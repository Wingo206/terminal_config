-- Add this to your plugins directory as lua/plugins/formatter.lua
return {
	"stevearc/conform.nvim",
	event = { "BufWritePre" },
	cmd = { "ConformInfo" },
	keys = {
		{
			"<leader>cf", -- Override the LSP format key
			function()
				require("conform").format({ async = true, lsp_fallback = true })
			end,
			mode = { "n", "v" },
			desc = "Format buffer",
		},
	},
	config = function()
		require("conform").setup({
			-- Map of filetype to formatters
			formatters_by_ft = {
				lua = { "stylua" },
				python = { "isort", "black" },
				javascript = { "prettierd", "prettier" },
				typescript = { "prettierd", "prettier" },
				javascriptreact = { "prettierd", "prettier" },
				typescriptreact = { "prettierd", "prettier" },
				json = { "prettierd", "prettier" },
				html = { "prettierd", "prettier" },
				css = { "prettierd", "prettier" },
				markdown = { "prettierd", "prettier" },
				yaml = { "prettierd", "prettier" },
			},

			-- Format on save (optional)
			format_on_save = {
				timeout_ms = 500,
				lsp_fallback = true,
			},

			-- Format after save (for slower formatters)
			-- format_after_save = {
			--   lsp_fallback = true,
			-- },

			-- Customize formatters (optional)
			formatters = {
				shfmt = {
					prepend_args = { "-i", "2" },
				},
			},
		})
	end,
}
