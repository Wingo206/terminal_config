#!/bin/bash
# Setup script for Wingo206/linux_pref.

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}"  )" &> /dev/null && pwd  )

#install things
sudo apt install vim
sudo apt install tmux

# copy all configuration files and directories
echo "Copying configuration files."
paths=(
   .vimrc
   .tmux.conf
    )

for path in "${paths[@]}"
do
    if [ -f "$HOME/$path" ]; then
        # Create /old directory if it doens't exist
        if [ ! -d "$SCRIPT_DIR/old" ]; then
            mkdir $SCRIPT_DIR/old
        fi
        # Move old file to /old directory
        echo "Moving $HOME/$path to $SCRIPT_DIR/old/ ."
        mv $HOME/$path $SCRIPT_DIR/old/$path
    fi
    # Copy new file into home directory
    echo "Copying $path to home directory"
    cp $path $HOME/$path 
done

# Setup vim-plug
if [ -d "$HOME/.vim" ]; then
    # Move old directory into /old
    mv $HOME/.vim $SCRIPT_DIR/old/.vim
fi
curl -fLo $HOME/.vim/autoload/plug.vim --create-dirs \
        https://raw.githubusercontent.com/junegunn/vim-plug/master/plug.vim

# Add to .bashrc
if  grep -q /opt/ros/noetic/lib/python3/dist-packages "$HOME/.bashrc"; then
    echo "$HOME/.bashrc already has pythonpath set up for ros python support in vim."
else
    echo "Adding to \$PYTHONPATH in .bashrc"
    if [ -f "$HOME/.bashrc" ]; then
        cp $HOME/.bashrc $SCRIPT_DIR/old/.bashrc
    fi
    echo "" >> $HOME/.bashrc
    echo "# python path for ros python modules. For use with vim plugins." >> $HOME/.bashrc
    echo "export PYTHONPATH=\"\${PYTHONPATH}:/opt/ros/noetic/lib/python3/dist-packages\"" >> $HOME/.bashrc
fi
# Install plugins
echo "Installing vim plugins..."
vim -E -s -u "$HOME/.vimrc" +PlugInstall +qall
echo "Done installing!"
