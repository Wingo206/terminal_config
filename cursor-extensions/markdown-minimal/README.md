# Markdown Minimal (`local.markdown-minimal`)

Zero-dependency Cursor / VS Code extension that adds lightweight inline Markdown styling directly inside the native text editor while keeping Vim motions, line numbers, the minimap, and the Outline sidebar intact.

## What it does

- **Typography & blocks:** Scales `H1`–`H6` headings using the active theme's Markdown colors, styles bold / italic / strikethrough, preserves a monospace font with subtle backgrounds on inline code and fenced code blocks, dims YAML frontmatter and HTML comments, and styles blockquotes and horizontal rules.
- **Honest link layout:** Highlights and underlines link labels while dimming `[...](...)` brackets and URL destinations (`markdownMinimal.linkSyntaxOpacity`, default `0.22`) instead of hiding them, keeping line wrapping, minimap proportions, and cursor positions predictable.
- **Vim Normal-mode stability:** Keeps short punctuation markers (`#`, `**`, `` ` ``, code fences) hidden while navigating in Vim Normal mode, revealing raw characters on the active construct only in Insert mode or inside a selection. Automatically disables decorations in diff views.
- **Workspace-relative code links:** Resolves leading-slash links (such as `[/components/foo.ts#L15-L35]` or `[/../mach9-keymap/src/bar.ts#L10]`) against the active window's workspace folder (falling back to the enclosing git root) and selects `#Lstart-Lend` line ranges on `Ctrl+Click`, even when the `.md` file lives outside the repo (e.g. `~/pr-reviews/` or `~/Research/`).
- **Quick toggle:** Click the eye icon in the editor title bar or run `Markdown Minimal: Toggle Inline Styling` (`markdownMinimal.toggle`) to switch decorations off or on.

## Build & install (WSL)

```bash
cd ~/terminal_config/cursor-extensions/markdown-minimal
npm install
npm run install-ext
```

Then run **Developer: Reload Window** in Cursor.

## Extension settings

| Setting | Default | Description |
|---|---|---|
| `markdownMinimal.enabled` | `true` | Enable minimal inline Markdown decorations. |
| `markdownMinimal.linkSyntaxOpacity` | `0.22` | Opacity (`0`–`1`) for dimmed Markdown link brackets and URL destinations. |

## Companion Cursor `settings.json` (`%APPDATA%\Cursor\User\settings.json`)

Add this `[markdown]` block to your Cursor user `settings.json` for proportional prose typography, smooth scrolling, and responsive wheel travel while keeping global line numbers and the minimap enabled:

```json
"[markdown]": {
    "editor.wordWrap": "on",
    "editor.fontFamily": "'Segoe UI', system-ui, -apple-system, sans-serif",
    "editor.fontSize": 15,
    "editor.lineHeight": 1.65,
    "editor.smoothScrolling": true,
    "editor.mouseWheelScrollSensitivity": 1.8,
    "editor.fastScrollSensitivity": 7,
    "editor.renderWhitespace": "none",
    "editor.guides.indentation": false,
    "editor.padding.top": 16,
    "editor.padding.bottom": 24,
    "editor.quickSuggestions": {
        "other": "off",
        "comments": "off",
        "strings": "off"
    }
}
```
