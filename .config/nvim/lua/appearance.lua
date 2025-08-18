-- Appearance configuration
local opt = vim.opt
local g = vim.g
local cmd = vim.cmd

-- Enable syntax highlighting
cmd("syntax enable")

-- Set colorscheme (with error handling)
local status_ok, _ = pcall(cmd, "colorscheme shades_of_purple")
if not status_ok then
	cmd("colorscheme default")
	print("Warning: shades_of_purple colorscheme not found, using default")
end

-- Custom highlight groups
local function set_highlights()
	local highlights = {
		-- CocInlayHint = { guibg = 'NONE', guifg = 'WebGray' },
		-- CocUnusedHighlight = { guibg = 'NONE', gui = 'underline' },
		Function = { guibg = "NONE", guifg = "#ff8aff" },
		Identifier = { guibg = "NONE", guifg = "#ffffff" },
		Conditional = { guibg = "NONE", guifg = "#ffb03b" },
		Operator = { guibg = "NONE", guifg = "#ffb03b" },
		StorageClass = { guibg = "NONE", guifg = "#ffb03b" },
		String = { guibg = "NONE", guifg = "#b9ffa8" },
		Comment = { guibg = "NONE", guifg = "#cc96fa" },
		TelescopeBorder = { guibg = "NONE", guifg = "#a599e9" },
		Visual = { guibg = "#655BA1", guifg = "NONE" },
		Search = { guibg = "#655BA1", guifg = "NONE" },
		ScrollView = { guibg = "#7367B7", guifg = "NONE" },
		Directory = { guibg = "NONE", guifg = "#ff8aff" },
		GestureBackground = { guibg = "#000000" },
	}

	for group, settings in pairs(highlights) do
		local hl_cmd = "hi " .. group
		for key, value in pairs(settings) do
			hl_cmd = hl_cmd .. " " .. key .. "=" .. value
		end
		cmd(hl_cmd)
	end
end

-- Apply highlights after colorscheme loads
vim.api.nvim_create_autocmd("ColorScheme", {
	pattern = "*",
	callback = set_highlights,
})

-- Apply highlights immediately
set_highlights()

-- Transparency groups configuration
-- g.transparent_groups = {
--   'Normal', 'Comment', 'Constant', 'Special', 'Identifier',
--   'Statement', 'PreProc', 'Type', 'Underlined', 'Todo', 'String',
--   'Function', 'Conditional', 'Repeat', 'Operator', 'Structure',
--   'LineNr', 'NonText', 'SignColumn', 'CursorLineNr', 'EndOfBuffer',
--   -- CoC transparency
--   'Pmenu', 'NormalFloat', --'CocFloating',
--   -- GitGutter transparency
--   'GitGutterAdd', 'GitGutterChange', 'GitGutterDelete',
--   -- Vertical split
--   'VertSplit',
--   -- Gesture transparency
--   'GestureBackground'
-- }

-- -- Airline configuration
-- g.shades_of_purple_airline = 1
-- g.airline_theme = 'shades_of_purple'
-- g.airline_powerline_fonts = 1
--
-- -- Airline symbols
-- g.airline_symbols = g.airline_symbols or {}
-- g.airline_left_sep = ''
-- g.airline_left_alt_sep = ''
-- g.airline_right_sep = ''
-- g.airline_right_alt_sep = ''
-- g.airline_symbols.branch = ''
-- g.airline_symbols.readonly = ''
-- g.airline_symbols.linenr = ''
