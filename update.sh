
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}"  )" &> /dev/null && pwd  )

echo "Copying .vimrc and adding to git"
cp $HOME/.vimrc $SCRIPT_DIR/.vimrc
git add $SCRIPT_DIR/.vimrc
