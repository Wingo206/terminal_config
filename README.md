# linux_pref

Repository containing my personal linux preferences and configuration files. Run Setup.sh to move the files into the correct locations and run initialization scripts. Moves existing files to the /old directory within this directory.

Useful keybinds:
- h j k l for movement in normal mode
- ZZ to do :wq (exit and save)
- ZQ to do :q! (exit without saving)
- i to enter insert mode
- I to enter insert mode at beginning of line
- a to enter insert mode 1 char further (useful for end of the line)
- A to enter insert mode at end of line
- o to "open new line" and enter insert mode
- / to search
- :%s/old/new to replace all instance of "old" with "new"

Mappings specific to my config:
- jj to <esc> in insert mode
- gcc to comment line (gc + motion)
- bd: delete other buffers, keep only current
- <Tab> <S-Tab> to navigate to next and previous tab

CoC:
- ,cf: format with CoC

Telescope:
- ,tf: Telescope find files
- ,tg: Telescope grep
- ,th: Telescope help (search help docs for nvim symbols/functions)
- ,<tab>: new tab and open telescope

Folding tips:
- Set to automatically save and load folds
- zR to open all folds
- zM to close all folds

NERDTree tips:
- Opens automatically when opening vim
- TT set to toggle NERDTree
- Use J and K to move down and up
- Use / to find text within vim. Can be used within NERDTree
- <space> set to unfold directories and open files in new tab
- gt: next tab, gT: previous tab
- Closes when it is the last remaining window
- use <Ctrl> ww to toggle between active windows. Can be used to focus on NERDTree

nvim-tree:
- ,nt: toggle nvim-tree
- ,nf: open nvim-tree, find and focus on current file
- <C-t>: open in new tab
- o: open
- for other bindings, use g? while in nvim-tree to open bindings tab

Tmux hotkeys:
- Ctrl+b prefixes all hotkeys
- \ to open picker menu
- w to pick between windows/sessions
- % to split horizontally
- " to split vertically
- hjkl to switch panes

# Todo:
- keybinds and config for nvimtree
- keybinds for nvim session manager

