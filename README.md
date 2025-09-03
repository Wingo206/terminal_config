# Terminal Config for Ubuntu

Repository containing my personal linux preferences and configuration files. Run Setup.sh to move the files into the correct locations and run initialization scripts. Moves existing files to the /old directory within this directory.

# Setup
- ``sudo apt update``
- ``cd .ssh``
- ``ssh-keygen``
- Upload public key to github in settings --> ssh keys
- ``cd ~``
- ``git clone git@github.com:Wingo206/terminal_config.git``
- ``sudo apt install stow``
- ``stow .``

# nvim setup
```
curl -LO https://github.com/neovim/neovim/releases/latest/download/nvim-linux-x86_64.tar.gz
sudo rm -rf /opt/nvim
sudo tar -C /opt -xzf nvim-linux-x86_64.tar.gz

# add to bashrc
export PATH="$PATH:/opt/nvim-linux-x86_64/bin"

source ~/.bashrc

sudo apt install fd-find  # for telescope
sudo apt install ripgrep  # for telescope
sudo apt install build-essential
sudo apt install unzip  # for stylua lsp

# for mason
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install --lts
nvm use --lts

# for telescope
git clone --depth 1 https://github.com/junegunn/fzf.git ~/.fzf
~/.fzf/install

```

# use :MasonLog to see installation failures

tmux setup
```
git clone https://github.com/tmux-plugins/tpm ~/.tmux/plugins/tpm
tmux source ~/.tmux.conf
ctrl+b then capital I
```

# Adding new files
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
