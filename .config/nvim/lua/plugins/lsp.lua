return {

	-- LSPConfig: Configurations for built-in LSP client
	{
		"neovim/nvim-lspconfig",
		event = { "BufReadPre", "BufNewFile" },
		dependencies = {
			"hrsh7th/cmp-nvim-lsp", -- LSP source for nvim-cmp
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

	-- Completion Engine
	{
		"hrsh7th/nvim-cmp",
		event = "InsertEnter",
		dependencies = {
			"hrsh7th/cmp-nvim-lsp",
			"L3MON4D3/LuaSnip",
		},
		config = function()
			local cmp = require("cmp")
			local luasnip = require("luasnip")

			cmp.setup({
				sources = {
					{ name = "nvim_lsp" },
				},
				mapping = cmp.mapping.preset.insert({
					["<C-Space>"] = cmp.mapping.complete(),
					["<C-u>"] = cmp.mapping.scroll_docs(-4),
					["<C-d>"] = cmp.mapping.scroll_docs(4),
					["<CR>"] = cmp.mapping.confirm({ select = true }),

					-- Tab completion like the minimal example
					-- ["<Tab>"] = cmp.mapping(function(fallback)
					-- 	if cmp.visible() then
					-- 		cmp.select_next_item()
					-- 	elseif luasnip.expand_or_jumpable() then
					-- 		luasnip.expand_or_jump()
					-- 	else
					-- 		fallback()
					-- 	end
					-- end, { "i", "s" }),

					["<S-Tab>"] = cmp.mapping(function(fallback)
						if cmp.visible() then
							cmp.select_prev_item()
						elseif luasnip.jumpable(-1) then
							luasnip.jump(-1)
						else
							fallback()
						end
					end, { "i", "s" }),
				}),
				snippet = {
					expand = function(args)
						luasnip.lsp_expand(args.body)
					end,
				},
			})
		end,
	},

	-- Snippet Engine
	{
		"L3MON4D3/LuaSnip",
		version = "2.*",
		build = "make install_jsregexp",
	},
}
