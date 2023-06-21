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
        
    Plug 'preservim/nerdtree'
    Plug 'tpope/vim-commentary'
    Plug 'liuchengxu/vista.vim'

    Plug 'vim-airline/vim-airline'
    "Airline Settings --------------------- {{{
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
    
    "}}}
    
    " Plug 'jeetsukumaran/vim-pythonsense'
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
" }}}


" VIMSCRIPT -------------------------------------------------------------- {{{

" This will enable code folding.
" Use the marker method of folding.
augroup filetype_vim
    autocmd!
    autocmd FileType vim setlocal foldmethod=marker
    au BufNewFile,BufRead *.py silent 
        set foldmethod=indent
    autocmd BufWinEnter * silent! :%foldopen!

augroup END

" More Vimscripts code goes here.

" }}}


" STATUS LINE ------------------------------------------------------------ {{{

" Status bar code goes here.

" }}}
