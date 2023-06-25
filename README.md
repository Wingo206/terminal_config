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

My Mappings:
- jj to <esc> in insert mode
- gcc to comment line (gc + motion)

Folding tips:
- Set to automatically save and load folds
- <space> to toggle current fold
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
