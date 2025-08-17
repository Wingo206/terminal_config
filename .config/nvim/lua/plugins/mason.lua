return {
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
	{
		"williamboman/mason-lspconfig.nvim",
		dependencies = { "williamboman/mason.nvim" },
		config = function()
			local lspconfig = require("lspconfig")
			local lsp_capabilities = require("cmp_nvim_lsp").default_capabilities()

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
					--
					-- -- Custom handler for TypeScript/JavaScript
					-- ["ts_ls"] = function()
					-- 	lspconfig.ts_ls.setup({
					-- 		capabilities = lsp_capabilities,
					-- 		settings = {
					-- 			completions = {
					-- 				completeFunctionCalls = true,
					-- 			},
					-- 		},
					-- 	})
					-- end,
					--
					-- -- Custom handler for Python
					-- ["pyright"] = function()
					-- 	lspconfig.pyright.setup({
					-- 		capabilities = lsp_capabilities,
					-- 		settings = {
					-- 			python = {
					-- 				analysis = {
					-- 					typeCheckingMode = "basic",
					-- 					autoSearchPaths = true,
					-- 					useLibraryCodeForTypes = true,
					-- 				},
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
