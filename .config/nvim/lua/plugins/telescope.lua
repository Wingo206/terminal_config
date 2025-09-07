return {
	"nvim-telescope/telescope.nvim",
	tag = "0.1.8",
	dependencies = {
		"nvim-lua/plenary.nvim",
		{
			"nvim-telescope/telescope-fzf-native.nvim",
			build = "make",
		},
	},
	cmd = "Telescope",
	keys = {
		{ "<leader>tf", "<cmd>Telescope find_files hidden=true<cr>", desc = "Find files" },
		{ "<leader>tg", "<cmd>Telescope live_grep<cr>", desc = "Live grep" },
		{ "<leader>th", "<cmd>Telescope help_tags<cr>", desc = "Help tags" },
		{ "<leader>tb", "<cmd>Telescope buffers<cr>", desc = "Search Buffers" },
	},
	config = function()
		local telescope = require("telescope")
		telescope.setup({

			pickers = {
				find_files = {
					hidden = true,
				},
				live_grep = {
					additional_args = function()
						return { "--hidden" }
					end,
				},
			},
			extensions = {
				fzf = {
					fuzzy = true,
					override_generic_sorter = true,
					override_file_sorter = true,
					case_mode = "smart_case",
				},
			},
		})
		require("telescope").load_extension("fzf")
		-- require('telescope').load_extension('remote-sshfs')
	end,
}
