local config_path = vim.fn.stdpath('config')
local init_vim_path = config_path .. '/init.vim.old'

if vim.fn.filereadable(init_vim_path) == 1 then
  local success, error_msg = pcall(vim.cmd.source, init_vim_path)
  if not success then
    vim.notify('Error loading init.vim: ' .. error_msg, vim.log.levels.ERROR)
  end
else
  vim.notify('init.vim not found at ' .. init_vim_path, vim.log.levels.WARN)
end

require("basic")
require("config.lazy")

require("appearance")
require("keybinds")

