"BASIC -------------------------{{{
    set nocompatible
    filetype on
    filetype plugin on
    filetype indent on

    set number
    " set relativenumber
    set cursorline
    set cursorcolumn

    set shiftwidth=4
    set tabstop=4
    set softtabstop=4
    set autoindent
    set expandtab
    set nobackup
    set nowrap
    set incsearch
    set ignorecase
    set showcmd
    set showmode
    set showmatch
    set hlsearch
    set history=1000

    set wildmenu
    set wildmode=list:longest
    set wildignore=*.docx,*.jpg,*.png,*.gif,*.pdf,*.pyc,*.exe,*.flv,*.img,*.xlsx

    set mouse=a

    " Fix 256 color mode for tmux
    if exists('+termguicolors')
      let &t_8f = "\<Esc>[38;2;%lu;%lu;%lum"
      let &t_8b = "\<Esc>[48;2;%lu;%lu;%lum"
      set termguicolors
    endif
" }}}

" PLUGINS ----------------------------------{{{

" Plugin code goes here.
call plug#begin('~/.vim/plugged')
    " Setup the theme
    Plug 'Rigellute/shades-of-purple.vim'
    " Plug 'joshdick/onedark.vim'
        
    Plug 'preservim/nerdtree' |
        \ Plug 'Xuyuanp/nerdtree-git-plugin'
    Plug 'tpope/vim-commentary'
    " Plug 'liuchengxu/vista.vim'
    Plug 'vim-airline/vim-airline'
    Plug 'jiangmiao/auto-pairs'
    Plug 'sheerun/vim-polyglot'
    Plug 'dense-analysis/ale'
    " ALE Settings -----------------{{{
    let g:ale_linters = {
                \'python': ['flake8']
                \}
    let g:ale_fixers = {
                \'python': ['black']
                \}
    let g:ale_python_black_options = '--line-length=79'
    " }}}
    
    Plug 'ycm-core/YouCompleteMe', { 'do': './install.py'  }
    Plug 'tmhedberg/SimpylFold'

    call plug#end()

"""" enable 24bit true color
" If you have vim >=8.0 or Neovim >= 0.1.5
if (has("termguicolors"))
 set termguicolors
endif

"""" enable the theme
syntax enable
colorscheme shades_of_purple

" }}}


" MAPPINGS ---------------------------------------------------------------{{{

" Mappings code goes here.
inoremap jj <esc>
nnoremap <space> za
nnoremap FF :ALEFix <CR>
let NERDTreeMapCustomOpen = '<space>'
let NERDTreeCustomOpenArgs = {'file': {'reuse':'currenttab', 'keepopen':1, 'where':'t', 'stay':0}}
let NERDTreeShowHidden=1


" TT for Tree Toggle, open NERDTree
nnoremap TT :NERDTreeToggle <Cr>

" }}}


" VIMSCRIPT -------------------------------------------------------------- {{{

" This will enable code folding.
" Use the marker method of folding.
augroup filetype_vim
    autocmd!
    autocmd FileType vim setlocal foldmethod=marker
augroup END

" Python autocomands
augroup filetype_py
    autocmd!
    au BufNewFile,BufRead *.py silent 
        set foldmethod=syntax
augroup END

" Readme autocommands
augroup filetype_md
    autocmd!
    au BufNewFile,BufRead *.md set wrap
    set linebreak
augroup END

" Remember folds
augroup remember_folds
    autocmd!
    autocmd BufWinLeave * mkview
    autocmd BufWinEnter * silent! loadview
augroup END 

" NERDTree autocommands
augroup NERDTreeCmds
    autocmd!

    " Start NERDTree. If a file is specified, move the cursor to its window.
    autocmd StdinReadPre * let s:std_in=1
    autocmd VimEnter * NERDTree | if argc() > 0 || exists("s:std_in") | wincmd p | endif

    " Start NERDTree when Vim starts with a directory argument.
    autocmd StdinReadPre * let s:std_in=1
    autocmd VimEnter * if argc() == 1 && isdirectory(argv()[0]) && !exists('s:std_in') |
        \ execute 'NERDTree' argv()[0] | wincmd p | enew | execute 'cd '.argv()[0] | call NERDTreeFocus() | endif

    " Open the existing NERDTree on each new tab.
    autocmd BufWinEnter * if getcmdwintype() == '' | silent NERDTreeMirror | endif

    " Exit Vim if NERDTree is the only window remaining in the only tab.
    autocmd BufEnter * if tabpagenr('$') == 1 && winnr('$') == 1 && exists('b:NERDTree') && b:NERDTree.isTabTree() | quit | endif

    " Close the tab if NERDTree is the only window remaining in it.
    autocmd BufEnter * if winnr('$') == 1 && exists('b:NERDTree') && b:NERDTree.isTabTree() | quit | endif

    autocmd! WinEnter * call CloseVimOnLastWindow()

    function! CloseVimOnLastWindow()
        " If we are on the last tab, if it contains only one window
        " and this window doesn't contains a buffer representing a file
        if (tabpagenr('$') == 1 && winnr() == 1 && len(expand('%'))==0)
            q!
        endif
    endfunction

    "If another buffer tries to replace NERDTree, put it in the other window,
    " and bring back NERDTree.
    autocmd BufEnter * if bufname('#') =~ 'NERD_tree_\d\+' && bufname('%') !~ 'NERD_tree_\d\+' && winnr('$') > 1 |
        \ let buf=bufnr() | buffer# | execute "normal! \<C-W>w" | execute 'buffer'.buf | endif
augroup END

" More Vimscripts code goes here.

" }}}


" STATUS LINE ------------------------------------------------------------ {{{

" Status bar code goes here.

" enable shades of purple airline theme
let g:shades_of_purple_airline = 1
let g:airline_theme='shades_of_purple'
" airline symbols
    " air-line
    let g:airline_powerline_fonts = 1

    if !exists('g:airline_symbols')
        let g:airline_symbols = {}
    endif

    " unicode symbols
    let g:airline_left_sep = ' '
    let g:airline_right_sep = ' '
    let g:airline_symbols.linenr = '␊'
    let g:airline_symbols.branch = '⎇'
    let g:airline_symbols.paste = 'ρ'
    let g:airline_symbols.whitespace = 'Ξ'
    
" }}}
" test
