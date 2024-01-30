"BASIC {{{
    set nocompatible
    filetype on
    filetype plugin on
    filetype indent on

    set number
    set relativenumber
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
    set nofoldenable
    set foldlevel=99

    " Fix 256 color mode for tmux
    if exists('+termguicolors')
      let &t_8f = "\<Esc>[38;2;%lu;%lu;%lum"
      let &t_8b = "\<Esc>[48;2;%lu;%lu;%lum"
      set termguicolors
    endif

" }}}

" PLUGINS {{{

    call plug#begin(has('nvim') ? stdpath('data') . '/plugged' : '~/.vim/plugged')
        Plug 'Rigellute/shades-of-purple.vim'
        Plug 'preservim/nerdtree' |
            \ Plug 'Xuyuanp/nerdtree-git-plugin'
        Plug 'airblade/vim-gitgutter'
        Plug 'tpope/vim-commentary'
        Plug 'nvim-lualine/lualine.nvim'
        Plug 'nvim-tree/nvim-web-devicons'
        Plug 'sheerun/vim-polyglot'
        Plug 'tmhedberg/SimpylFold'
        Plug 'nvim-lua/plenary.nvim'
        Plug 'nvim-telescope/telescope.nvim', { 'tag': '0.1.2' }
        Plug 'nvim-telescope/telescope-fzf-native.nvim', { 'do': 'make' }
        Plug 'neoclide/coc.nvim', {'branch': 'release'}
        Plug 'tribela/vim-transparent'
        Plug 'nvim-treesitter/nvim-treesitter', {'do': ':TSUpdate'}
        Plug 'kylechui/nvim-surround'
        Plug 'cohama/lexima.vim'
        "Plug 'notomo/gesture.nvim'
        Plug 'Shatur/neovim-session-manager'
        Plug 'stevearc/dressing.nvim'


    call plug#end()

    " coc extensions
    let g:coc_global_extensions = ['coc-pyright', 'coc-tsserver']

    " settings for coc completion
    set encoding=utf-8
    set nobackup
    set nowritebackup
    set updatetime=300
    set signcolumn=yes
    inoremap <silent><expr> <Tab> coc#pum#visible() ? coc#_select_confirm() : "\<C-g>u\<Tab>"
    function! CheckBackspace() abort
      let col = col('.') - 1
      return !col || getline('.')[col - 1]  =~# '\s'
    endfunction

" }}}

" MAPPINGS {{{
    let mapleader = "," " map leader to comma
    inoremap jj <esc>
    nnoremap <space> za
    nnoremap <Tab> gt
    nnoremap <S-Tab> gT

    " NERDTree
    let NERDTreeMapCustomOpen = '<space>'
    let NERDTreeCustomOpenArgs = {'file': {'reuse':'all', 'keepopen':1, 'where':'t', 'stay':0}}
    let NERDTreeShowHidden=1
    nnoremap <leader>nt :NERDTreeToggle <Cr>

    " CoC
    nmap <leader>cf <Plug>(coc-format)

    " Telescope
    nnoremap <leader>tf <cmd>Telescope find_files hidden=true<cr>
    nnoremap <leader>tg <cmd>Telescope live_grep<cr>
    nnoremap <leader>th <cmd>Telescope help_tags<cr>

    " new tab
    nnoremap <leader><tab> <cmd>tabnew<cr><cmd>Telescope find_files<cr>


    " Delete Buffers
    command! BufOnly silent! execute "%bd|e#|bd#"
    nnoremap <leader>bd <cmd>BufOnly<cr>

" }}}

" VIMSCRIPT {{{

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

    " NERDTree autocommands
    augroup NERDTreeCmds
        autocmd!

        " Start NERDTree. If a file is specified, move the cursor to its window.
        " autocmd StdinReadPre * let s:std_in=1
        " autocmd VimEnter * NERDTree | if argc() > 0 || exists("s:std_in") | wincmd p | endif

        " Start NERDTree when Vim starts with a directory argument.
        " autocmd StdinReadPre * let s:std_in=1
        " autocmd VimEnter * if argc() == 1 && isdirectory(argv()[0]) && !exists('s:std_in') |
        "     \ execute 'NERDTree' argv()[0] | wincmd p | enew | execute 'cd '.argv()[0] | call NERDTreeFocus() | endif

        " Open the existing NERDTree on each new tab.
        " autocmd BufWinEnter * if getcmdwintype() == '' | silent NERDTreeMirror | endif

        " Exit Vim if NERDTree is the only window remaining in the only tab.
        " autocmd BufEnter * if tabpagenr('$') == 1 && winnr('$') == 1 && exists('b:NERDTree') && b:NERDTree.isTabTree() | quit | endif

        " Close the tab if NERDTree is the only window remaining in it.
        " autocmd BufEnter * if winnr('$') == 1 && exists('b:NERDTree') && b:NERDTree.isTabTree() | quit | endif

        " autocmd! WinEnter * call CloseVimOnLastWindow()

        " function! CloseVimOnLastWindow()
        "     " If we are on the last tab, if it contains only one window
        "     " and this window doesn't contains a buffer representing a file
        "     if (tabpagenr('$') == 1 && winnr() == 1 && len(expand('%'))==0)
        "         q!
        "     endif
        " endfunction

        "If another buffer tries to replace NERDTree, put it in the other window,
        " and bring back NERDTree.
        " autocmd BufEnter * if bufname('#') =~ 'NERD_tree_\d\+' && bufname('%') !~ 'NERD_tree_\d\+' && winnr('$') > 1 |
        "     \ let buf=bufnr() | buffer# | execute "normal! \<C-W>w" | execute 'buffer'.buf | endif

        " autocmd TabEnter * NERDTreeFocus |  wincmd w
        " autocmd TabLeave * if bufname('#') =~ 'NERD_tree_\d\+' | wincmd w
    augroup END

    function! SynStack()
      if !exists("*synstack")
        return
      endif
      echo map(synstack(line('.'), col('.')), 'synIDattr(v:val, "name")')
    endfunc

" }}}

" APPEARANCE {{{
    
    " enable 24bit true color
    if (has("termguicolors"))
     set termguicolors
    endif

    " enable the theme
    syntax enable
    colorscheme shades_of_purple
    hi CocInlayHint guibg=NONE guifg=WebGray
    hi CocUnusedHighlight guibg=NONE gui=underline
    hi Function guibg=NONE guifg=#ff8aff
    hi Identifier guibg=None guifg=#ffffff
    hi Conditional guibg=NONE guifg=#ffb03b
    hi Operator guibg=NONE guifg=#ffb03b
    hi StorageClass guibg=NONE guifg=#ffb03b
    hi String guibg=NONE guifg=#b9ffa8
    hi Comment guibg=NONE guifg=#cc96fa
    hi TelescopeBorder guibg=NONE guifg=#a599e9

    hi Directory guibg=NONE guifg=#ff8aff


    let g:transparent_groups = ['Normal', 'Comment', 'Constant', 'Special', 'Identifier',
                            \ 'Statement', 'PreProc', 'Type', 'Underlined', 'Todo', 'String',
                            \ 'Function', 'Conditional', 'Repeat', 'Operator', 'Structure',
                            \ 'LineNr', 'NonText', 'SignColumn', 'CursorLineNr', 'EndOfBuffer']

    " coc transparency
    let g:transparent_groups += ['Pmenu', 'NormalFloat', 'CocFloating']

    " gitgutter transparency
    let g:transparent_groups += ['GitGutterAdd', 'GitGutterChange', 'GitGutterDelete', 'GitGutterDelete']

    let g:transparent_groups += ['VertSplit']

    " gesture transparency
    hi GestureBackground guibg=#000000
    let g:transparent_groups += ['GestureBackground']

    " hi PmenuThumb guibg = #b362ff
    " hi PmenuSBar guibg = #a599e9

    " STATUS LINE {{{
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
            let g:airline_left_sep = ''
            let g:airline_left_alt_sep = ''
            let g:airline_right_sep = ''
            let g:airline_right_alt_sep = ''
            let g:airline_symbols.branch = ''
            let g:airline_symbols.readonly = ''
            let g:airline_symbols.linenr = ''
    " }}}
" }}}

" Add Lua configuration
lua require('conf')
