return {

	-- LSPConfig: Configurations for built-in LSP client
	{
		"neovim/nvim-lspconfig",
		event = { "BufReadPre", "BufNewFile" },
		dependencies = {
			-- "hrsh7th/cmp-nvim-lsp", -- LSP source for nvim-cmp
			"williamboman/mason-lspconfig.nvim",
		},
		config = function()
			-- Set up LSP keymaps when server attaches
			local lsp_cmds = vim.api.nvim_create_augroup("lsp_cmds", { clear = true })
			vim.api.nvim_create_autocmd("LspAttach", {
				group = lsp_cmds,
				desc = "LSP actions",
				callback = function()
					local bufmap = function(mode, lhs, rhs)
						vim.keymap.set(mode, lhs, rhs, { buffer = true })
					end

					-- Navigation
					bufmap("n", "K", "<cmd>lua vim.lsp.buf.hover()<cr>")
					bufmap("n", "gd", "<cmd>lua vim.lsp.buf.definition()<cr>")
					bufmap("n", "gD", "<cmd>lua vim.lsp.buf.declaration()<cr>")
					bufmap("n", "gi", "<cmd>lua vim.lsp.buf.implementation()<cr>")
					bufmap("n", "go", "<cmd>lua vim.lsp.buf.type_definition()<cr>")
					bufmap("n", "gr", "<cmd>lua vim.lsp.buf.references()<cr>")
					bufmap("n", "gs", "<cmd>lua vim.lsp.buf.signature_help()<cr>")

					-- Code actions
					-- bufmap('n', '<F2>', '<cmd>lua vim.lsp.buf.rename()<cr>')
					-- bufmap({ 'n', 'x' }, '<F3>', '<cmd>lua vim.lsp.buf.format({async = true})<cr>')
					-- bufmap('n', '<F4>', '<cmd>lua vim.lsp.buf.code_action()<cr>')

					-- Diagnostics
					bufmap("n", "gl", "<cmd>lua vim.diagnostic.open_float()<cr>")
					bufmap("n", "[d", "<cmd>lua vim.diagnostic.goto_prev()<cr>")
					bufmap("n", "]d", "<cmd>lua vim.diagnostic.goto_next()<cr>")
				end,
			})

			-- Configure diagnostic display
			vim.diagnostic.config({
				virtual_text = {
					prefix = "●",
					source = "if_many",
				},
				float = {
					source = "always",
					border = "rounded",
				},
				signs = true,
				underline = true,
				update_in_insert = false,
				severity_sort = true,
			})

			-- Customize diagnostic signs
			local signs = {
				{ name = "DiagnosticSignError", text = "" },
				{ name = "DiagnosticSignWarn", text = "" },
				{ name = "DiagnosticSignHint", text = "" },
				{ name = "DiagnosticSignInfo", text = "" },
			}

			for _, sign in ipairs(signs) do
				vim.fn.sign_define(sign.name, { texthl = sign.name, text = sign.text, numhl = "" })
			end
		end,
	},

	-- Mason: Package manager for LSP servers, DAP servers, linters, formatters
	{
		"williamboman/mason.nvim",
		config = function()
			require("mason").setup({
				ui = {
					icons = {
						package_installed = "✓",
						package_pending = "➜",
						package_uninstalled = "✗",
					},
				},
			})
		end,
	},

	-- Mason-LSPConfig: Bridge between mason and lspconfig
	-- Makes setting up lsps easier
	{
		"williamboman/mason-lspconfig.nvim",
		dependencies = { "williamboman/mason.nvim" },
		config = function()
			local lspconfig = require("lspconfig")
			local lsp_capabilities = require("blink.cmp").get_lsp_capabilities()

			require("mason-lspconfig").setup({
				-- Automatically install these language servers
				ensure_installed = {
					"lua_ls",
					"pyright",
					"ts_ls",
				},

				-- Automatically install language servers set up via lspconfig
				automatic_installation = true,

				-- Handlers: automatic setup for all servers
				handlers = {
					-- Default handler for all servers
					function(server)
						lspconfig[server].setup({
							capabilities = lsp_capabilities,
						})
					end,

					--
					-- -- Custom handler for lua_ls
					-- ["lua_ls"] = function()
					-- 	lspconfig.lua_ls.setup({
					-- 		capabilities = lsp_capabilities,
					-- 		settings = {
					-- 			Lua = {
					-- 				runtime = { version = "LuaJIT" },
					-- 				diagnostics = { globals = { "vim" } },
					-- 				workspace = {
					-- 					library = vim.api.nvim_get_runtime_file("", true),
					-- 					checkThirdParty = false,
					-- 				},
					-- 				telemetry = { enable = false },
					-- 			},
					-- 		},
					-- 	})
					-- end,
				},
			})
		end,
	},
	{
		"WhoIsSethDaniel/mason-tool-installer",
		dependencies = {
			"williamboman/mason.nvim",
			"williamboman/mason-lspconfig.nvim",
		},
		config = function()
			require("mason-tool-installer").setup({
				ensure_installed = {
					-- LSP servers (already handled by mason-lspconfig)
					-- "lua_ls", "pyright", "ts_ls",

					-- Formatters
					"stylua", -- Lua formatter
					-- "black", -- Python formatter
					-- "isort", -- Python import sorter
					"prettierd", -- Faster prettier

					-- Linters (optional)
					"eslint_d", -- JavaScript/TypeScript linter
					-- "flake8", -- Python linter

					-- Add more tools as needed
				},

				-- Auto-install missing tools on startup
				auto_update = false,
				run_on_start = true,
				start_delay = 3000,

				integrations = {
					["mason-lspconfig"] = true,
				},
			})
		end,
	},
}
