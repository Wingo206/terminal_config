
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}"  )" &> /dev/null && pwd  )

echo "Copying nvim config and .tmux.conf"
cp ~/.config/nvim/ . -r
cp ~/.tmux.conf .
#cp $HOME/.vimrc $SCRIPT_DIR/.vimrc
#git add $SCRIPT_DIR/.vimrc
