-- Basic Neovim configuration in Lua
local opt = vim.opt

-- File type detection and plugins
vim.cmd('filetype on')
vim.cmd('filetype plugin on')
vim.cmd('filetype indent on')

-- Line numbers
opt.number = true
opt.relativenumber = true

-- Visual guides
opt.cursorline = true
opt.cursorcolumn = true

-- Indentation
opt.shiftwidth = 4
opt.tabstop = 4
opt.softtabstop = 4
opt.autoindent = true
opt.expandtab = true

-- File handling
opt.backup = false
opt.autoread = true

-- Text wrapping
opt.wrap = false

-- Search settings
opt.incsearch = true
opt.ignorecase = true
opt.smartcase = true  -- Override ignorecase if search contains uppercase
opt.hlsearch = true

-- UI settings
opt.showcmd = true
opt.showmode = true
opt.showmatch = true

-- History and undo
opt.history = 1000
opt.undofile = true  -- Persistent undo across sessions

-- Scrolling
opt.scrolloff = 5
opt.sidescroll = 1
opt.sidescrolloff = 5

-- Command line completion
opt.wildmenu = true
opt.wildmode = { 'list:longest' }
opt.wildignore = {
    '*.docx', '*.jpg', '*.png', '*.gif', '*.pdf', '*.pyc', '*.exe',
    '*.flv', '*.img', '*.xlsx', '*.o', '*.obj', '*.class'
}

-- Mouse support
opt.mouse = 'a'

-- Enable 24-bit RGB colors
opt.termguicolors = true

-- Folding configuration
opt.foldenable = false

-- Set leader key
vim.g.mapleader = ","

-- Additional modern improvements
opt.signcolumn = 'yes'        -- Always show sign column (for LSP, git signs, etc.)
opt.updatetime = 300          -- Faster completion (default is 4000ms)
opt.timeoutlen = 500          -- Faster key sequence completion
opt.splitbelow = true         -- Horizontal splits go below
opt.splitright = true         -- Vertical splits go right
opt.clipboard = 'unnamedplus' -- Use system clipboard
opt.conceallevel = 0          -- Don't hide quotes in JSON files
opt.pumheight = 10            -- Popup menu height
opt.cmdheight = 1             -- Command line height
opt.completeopt = { 'menu', 'menuone', 'noselect' } -- Better completion experience
