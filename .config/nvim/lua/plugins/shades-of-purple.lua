return {
  "Rigellute/shades-of-purple.vim",
  priority = 1000, -- Load colorschemes first
  config = function()
    vim.cmd.colorscheme("shades_of_purple")
    --
    -- -- Your custom highlights from before
    -- local highlights = {
    --   CocInlayHint = { guibg = 'NONE', guifg = 'WebGray' },
    --   Function = { guibg = 'NONE', guifg = '#ff8aff' },
    --   -- ... rest of your highlights
    -- }
    --
    -- for group, settings in pairs(highlights) do
    --   vim.api.nvim_set_hl(0, group, settings)
    -- end
  end,
}
