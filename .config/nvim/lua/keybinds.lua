-- Keymappings configuration
local keymap = vim.keymap.set
local opts = { noremap = true, silent = true }

-- Basic mappings
keymap("i", "jj", "<Esc>", opts)
keymap("n", "<Tab>", "gt", opts)
keymap("n", "<S-Tab>", "gT", opts)

-- New tab with file finder
keymap("n", "<leader><tab>", "<cmd>NvimTreeClose<cr><cmd>tabnew<cr><cmd>Telescope find_files hidden=true<cr>", opts)

-- Delete all buffers except current
vim.api.nvim_create_user_command("BufOnly", function()
	vim.cmd('silent! execute "%bd|e#|bd#"')
end, {})

keymap("n", "<leader>bd", "<cmd>BufOnly<cr>", opts)

local function smart_navigate(direction)
	local win_before = vim.api.nvim_get_current_win()

	-- Try vim navigation first
	if direction == "left" then
		vim.cmd("wincmd h")
	elseif direction == "right" then
		vim.cmd("wincmd l")
	elseif direction == "up" then
		vim.cmd("wincmd k")
	elseif direction == "down" then
		vim.cmd("wincmd j")
	end

	local win_after = vim.api.nvim_get_current_win()

	-- If we didn't move in vim, try tmux (but only if not at tmux edge)
	if win_before == win_after then
		-- Use tmux navigation with edge checking
		local tmux_cmd
		if direction == "left" then
			tmux_cmd = 'if-shell "[ #{pane_at_left} -eq 0 ]" "select-pane -L"'
		elseif direction == "right" then
			tmux_cmd = 'if-shell "[ #{pane_at_right} -eq 0 ]" "select-pane -R"'
		elseif direction == "up" then
			tmux_cmd = 'if-shell "[ #{pane_at_top} -eq 0 ]" "select-pane -U"'
		elseif direction == "down" then
			tmux_cmd = 'if-shell "[ #{pane_at_bottom} -eq 0 ]" "select-pane -D"'
		end

		if tmux_cmd then
			vim.fn.system("tmux " .. tmux_cmd)
		end
	end
end

-- Map to your custom functions
vim.keymap.set("n", "<C-h>", function()
	smart_navigate("left")
end)
vim.keymap.set("n", "<C-j>", function()
	smart_navigate("down")
end)
vim.keymap.set("n", "<C-k>", function()
	smart_navigate("up")
end)
vim.keymap.set("n", "<C-l>", function()
	smart_navigate("right")
end)

-- Better indenting (stay in visual mode)
keymap("v", "<", "<gv", opts)
keymap("v", ">", ">gv", opts)
