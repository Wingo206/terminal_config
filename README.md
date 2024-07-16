# linux_pref

Repository containing my personal linux preferences and configuration files. Run Setup.sh to move the files into the correct locations and run initialization scripts. Moves existing files to the /old directory within this directory.

#Setup
- Clone repository into home directory
- Install stow
- In this directory, run ```stow .```

#Adding new files
- Move the file to this directory
- Run ```stow .```

Useful Tools:
- fzf ``https://askubuntu.com/questions/1515760/unknown-option-bash-when-opening-the-terminal``
- zoxide ``https://github.com/ajeetdsouza/zoxide``

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
