# Setup fzf
# ---------
if [[ ! "$PATH" == */home/brandon/.fzf/bin* ]]; then
  PATH="${PATH:+${PATH}:}/home/brandon/.fzf/bin"
fi

eval "$(fzf --bash)"
