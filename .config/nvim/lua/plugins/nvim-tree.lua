-- lua/plugins/nvim-tree.lua
return {
  "nvim-tree/nvim-tree.lua",
  version = "*",
  lazy = false, -- Load at startup since we're disabling netrw
  dependencies = {
    "nvim-tree/nvim-web-devicons",
  },
  keys = {
    { "<leader>nt", "<cmd>NvimTreeToggle<cr>", desc = "Toggle NvimTree" },
    { "<leader>nf", "<cmd>NvimTreeFindFile<cr>", desc = "Find file in NvimTree" },
  },
  init = function()
    -- Disable netrw at the very start (before nvim-tree loads)
    vim.g.loaded_netrw = 1
    vim.g.loaded_netrwPlugin = 1
    
    -- Set fillchars for better appearance
    vim.opt.fillchars = { eob = " " }
  end,
  config = function()
    local function my_on_attach(bufnr)
      local api = require('nvim-tree.api')
      
      local function opts(desc)
        return { 
          desc = 'nvim-tree: ' .. desc, 
          buffer = bufnr, 
          noremap = true, 
          silent = true, 
          nowait = true 
        }
      end
      
      -- Apply default mappings first
      api.config.mappings.default_on_attach(bufnr)
      
      -- Custom mappings
      local function go_to_next_tab()
        vim.cmd("tabnext")
      end
      
      -- Override Tab key to go to next tab instead of nvim-tree's default
      vim.keymap.set('n', '<Tab>', go_to_next_tab, opts('Go to next tab'))
    end

    require("nvim-tree").setup({
      view = {
        float = {
          enable = false
        },
      },
      tab = {
        sync = {
          open = true,
          close = true,
          ignore = {},
        },
      },
      on_attach = my_on_attach,
      
      -- Additional recommended settings
      sort_by = "case_sensitive",
      renderer = {
        group_empty = true,
      },
      filters = {
        dotfiles = false, -- Show dotfiles
      },
      git = {
        enable = true,
        ignore = false,
        timeout = 400,
      },
    })
  end,
}
