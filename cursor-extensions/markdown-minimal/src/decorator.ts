import * as vscode from 'vscode';
import {
  isWholeLineKind,
  scanMarkdown,
  type DecorationKind,
  type ParsedLink,
  type RevealScope,
  type ScanResult,
} from './scanner.ts';

const MONOSPACE_CSS =
  "font-family: Consolas, 'Cascadia Mono', 'Courier New', monospace; font-size: 0.92em;";

const SUPPRESSED_ON_EDIT = new Set<DecorationKind>([
  'hide',
  'transparent',
  'faint',
  'linkSyntaxFaint',
  'heading1',
  'heading2',
  'heading3',
  'heading4',
  'heading5',
  'heading6',
  'horizontalRuleLine',
]);

interface CachedScan {
  version: number;
  result: ScanResult;
}

export class MinimalMarkdownDecorator implements vscode.Disposable {
  private readonly cache = new Map<string, CachedScan>();
  private types = new Map<DecorationKind, vscode.TextEditorDecorationType>();
  private selectionOverlayType!: vscode.TextEditorDecorationType;
  private enabled: boolean;
  private debounceTimer: NodeJS.Timeout | undefined;

  constructor() {
    this.enabled = vscode.workspace
      .getConfiguration('markdownMinimal')
      .get<boolean>('enabled', true);
    this.rebuildDecorationTypes();
  }

  isEnabled(): boolean {
    return this.enabled;
  }

  toggle(): boolean {
    this.enabled = !this.enabled;
    this.refreshVisibleEditors();
    return this.enabled;
  }

  reloadConfig(): void {
    this.enabled = vscode.workspace
      .getConfiguration('markdownMinimal')
      .get<boolean>('enabled', true);
    this.disposeDecorationTypes();
    this.rebuildDecorationTypes();
    this.refreshVisibleEditors();
  }

  getLinksForDocument(document: vscode.TextDocument): readonly ParsedLink[] {
    return this.getScan(document).links;
  }

  invalidateDocument(document: vscode.TextDocument): void {
    this.cache.delete(document.uri.toString());
  }

  scheduleDocumentRefresh(document: vscode.TextDocument): void {
    this.invalidateDocument(document);
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    this.debounceTimer = setTimeout(() => {
      this.debounceTimer = undefined;
      for (const editor of vscode.window.visibleTextEditors) {
        if (editor.document.uri.toString() === document.uri.toString()) {
          this.applyToEditor(editor);
        }
      }
    }, 60);
  }

  refreshVisibleEditors(): void {
    for (const editor of vscode.window.visibleTextEditors) {
      if (isMarkdownEditor(editor)) {
        this.applyToEditor(editor);
      }
    }
  }

  applyToEditor(editor: vscode.TextEditor | undefined): void {
    if (!editor || !isMarkdownEditor(editor)) {
      return;
    }

    if (!this.enabled || isDiffEditor(editor)) {
      this.clearEditor(editor);
      return;
    }

    const { tokens, scopes } = this.getScan(editor.document);
    const activeScopes = computeActiveScopes(editor, scopes);
    const grouped = new Map<DecorationKind, vscode.Range[]>();

    for (const token of tokens) {
      if (
        activeScopes.length > 0 &&
        SUPPRESSED_ON_EDIT.has(token.kind) &&
        intersectsAnyScope(token.from, token.to, activeScopes)
      ) {
        continue;
      }

      const range = new vscode.Range(
        editor.document.positionAt(token.from),
        editor.document.positionAt(token.to),
      );
      let list = grouped.get(token.kind);
      if (!list) {
        list = [];
        grouped.set(token.kind, list);
      }
      list.push(range);
    }

    for (const [kind, decoType] of this.types.entries()) {
      editor.setDecorations(decoType, grouped.get(kind) ?? []);
    }

    // Keep text selection readable atop whole-line code block / frontmatter backgrounds
    const overlayRanges: vscode.Range[] = [];
    const blockRanges = [
      ...(grouped.get('codeBlockLine') ?? []),
      ...(grouped.get('frontmatterLine') ?? []),
    ];
    if (blockRanges.length > 0) {
      for (const selection of editor.selections) {
        if (selection.isEmpty) {
          continue;
        }
        for (const blockRange of blockRanges) {
          if (
            blockRange.start.line >= selection.start.line &&
            blockRange.start.line <= selection.end.line
          ) {
            const lineRange = editor.document.lineAt(blockRange.start.line).range;
            const hit = lineRange.intersection(selection);
            if (hit && !hit.isEmpty) {
              overlayRanges.push(hit);
            }
          }
        }
      }
    }
    editor.setDecorations(this.selectionOverlayType, overlayRanges);
  }

  dispose(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }
    this.disposeDecorationTypes();
    this.cache.clear();
  }

  private getScan(document: vscode.TextDocument): ScanResult {
    const key = document.uri.toString();
    const cached = this.cache.get(key);
    if (cached && cached.version === document.version) {
      return cached.result;
    }
    const result = scanMarkdown(document.getText());
    this.cache.set(key, { version: document.version, result });
    return result;
  }

  private clearEditor(editor: vscode.TextEditor): void {
    for (const decoType of this.types.values()) {
      editor.setDecorations(decoType, []);
    }
    editor.setDecorations(this.selectionOverlayType, []);
  }

  private disposeDecorationTypes(): void {
    for (const decoType of this.types.values()) {
      decoType.dispose();
    }
    this.types.clear();
    this.selectionOverlayType?.dispose();
  }

  private rebuildDecorationTypes(): void {
    const linkOpacity = Math.max(
      0,
      Math.min(
        1,
        vscode.workspace.getConfiguration('markdownMinimal').get<number>('linkSyntaxOpacity', 0.22),
      ),
    );
    const isDark =
      vscode.window.activeColorTheme.kind === vscode.ColorThemeKind.Dark ||
      vscode.window.activeColorTheme.kind === vscode.ColorThemeKind.HighContrast;
    const inlineCodeBg = isDark ? 'rgba(255, 255, 255, 0.09)' : 'rgba(0, 0, 0, 0.07)';

    this.types = new Map<DecorationKind, vscode.TextEditorDecorationType>([
      [
        'hide',
        vscode.window.createTextEditorDecorationType({
          textDecoration: 'none; display: none;',
          after: { contentText: '' },
        }),
      ],
      [
        'transparent',
        vscode.window.createTextEditorDecorationType({
          color: 'transparent',
        }),
      ],
      [
        'faint',
        vscode.window.createTextEditorDecorationType({
          opacity: '0.38',
        }),
      ],
      [
        'linkSyntaxFaint',
        vscode.window.createTextEditorDecorationType({
          opacity: linkOpacity.toString(),
        }),
      ],
      ['heading1', headingDecoration('1.6em', '700')],
      ['heading2', headingDecoration('1.36em', '700')],
      ['heading3', headingDecoration('1.18em', '700')],
      ['heading4', headingDecoration('1.08em', '700')],
      ['heading5', headingDecoration('1.0em', '600')],
      ['heading6', headingDecoration('0.95em', '600', '0.85')],
      [
        'bold',
        vscode.window.createTextEditorDecorationType({
          fontWeight: 'bold',
        }),
      ],
      [
        'italic',
        vscode.window.createTextEditorDecorationType({
          fontStyle: 'italic',
        }),
      ],
      [
        'boldItalic',
        vscode.window.createTextEditorDecorationType({
          fontWeight: 'bold',
          fontStyle: 'italic',
        }),
      ],
      [
        'strikethrough',
        vscode.window.createTextEditorDecorationType({
          textDecoration: 'line-through',
        }),
      ],
      [
        'inlineCode',
        vscode.window.createTextEditorDecorationType({
          backgroundColor: inlineCodeBg,
          borderRadius: '3px',
          textDecoration: `none; ${MONOSPACE_CSS}`,
        }),
      ],
      [
        'link',
        vscode.window.createTextEditorDecorationType({
          color: new vscode.ThemeColor('textLink.foreground'),
          textDecoration: 'underline',
          cursor: 'pointer',
        }),
      ],
      [
        'codeBlockLine',
        vscode.window.createTextEditorDecorationType({
          backgroundColor: new vscode.ThemeColor('textCodeBlock.background'),
          isWholeLine: isWholeLineKind('codeBlockLine'),
          textDecoration: `none; ${MONOSPACE_CSS}`,
        }),
      ],
      [
        'frontmatterLine',
        vscode.window.createTextEditorDecorationType({
          backgroundColor: new vscode.ThemeColor('textCodeBlock.background'),
          isWholeLine: isWholeLineKind('frontmatterLine'),
          textDecoration: `none; ${MONOSPACE_CSS}`,
        }),
      ],
      [
        'blockquoteLine',
        vscode.window.createTextEditorDecorationType({
          borderWidth: '0 0 0 3px',
          borderStyle: 'solid',
          borderColor: new vscode.ThemeColor('textBlockQuote.border'),
          backgroundColor: new vscode.ThemeColor('textBlockQuote.background'),
          isWholeLine: isWholeLineKind('blockquoteLine'),
        }),
      ],
      [
        'horizontalRuleLine',
        vscode.window.createTextEditorDecorationType({
          borderWidth: '0 0 1px 0',
          borderStyle: 'solid',
          borderColor: new vscode.ThemeColor('editorWidget.border'),
          isWholeLine: isWholeLineKind('horizontalRuleLine'),
        }),
      ],
    ]);

    this.selectionOverlayType = vscode.window.createTextEditorDecorationType({
      backgroundColor: new vscode.ThemeColor('editor.selectionBackground'),
    });
  }
}

function headingDecoration(
  size: string,
  weight: string,
  opacity?: string,
): vscode.TextEditorDecorationType {
  return vscode.window.createTextEditorDecorationType({
    fontWeight: weight,
    ...(opacity ? { opacity } : {}),
    textDecoration: `none; font-size: ${size};`,
  });
}

export function isMarkdownEditor(editor: vscode.TextEditor): boolean {
  const lang = editor.document.languageId;
  return lang === 'markdown' || lang === 'mdx';
}

function isDiffEditor(editor: vscode.TextEditor): boolean {
  const scheme = editor.document.uri.scheme;
  if (scheme === 'git' || scheme === 'vscode-scm') {
    return true;
  }
  for (const group of vscode.window.tabGroups.all) {
    const active = group.activeTab;
    if (active?.input instanceof vscode.TabInputTextDiff) {
      const { original, modified } = active.input;
      const target = editor.document.uri.toString();
      if (original.toString() === target || modified.toString() === target) {
        return true;
      }
    }
  }
  return false;
}

function computeActiveScopes(
  editor: vscode.TextEditor,
  scopes: readonly RevealScope[],
): RevealScope[] {
  if (scopes.length === 0) {
    return [];
  }

  const cursorStyle = editor.options.cursorStyle;
  // VSCodeVim sets Block / Underline cursors in Normal, Visual, and Operator-Pending modes,
  // and switches to Line / LineThin in Insert mode. Keep Markdown stably styled while moving
  // around or Ctrl+Clicking links in Normal mode.
  const isInsertCursor =
    cursorStyle === undefined ||
    cursorStyle === vscode.TextEditorCursorStyle.Line ||
    cursorStyle === vscode.TextEditorCursorStyle.LineThin;

  const active: RevealScope[] = [];

  for (const selection of editor.selections) {
    if (!selection.isEmpty) {
      const selFrom = editor.document.offsetAt(selection.start);
      const selTo = editor.document.offsetAt(selection.end);
      for (const scope of scopes) {
        if (selFrom <= scope.to && selTo >= scope.from) {
          active.push(scope);
        }
      }
    } else if (isInsertCursor) {
      const offset = editor.document.offsetAt(selection.active);
      // Reveal the tightest scope containing the Insert-mode cursor
      let tightest: RevealScope | undefined;
      for (const scope of scopes) {
        if (offset >= scope.from && offset <= scope.to) {
          if (!tightest || scope.to - scope.from < tightest.to - tightest.from) {
            tightest = scope;
          }
        }
      }
      if (tightest) {
        active.push(tightest);
      }
    }
  }

  return active;
}

function intersectsAnyScope(
  from: number,
  to: number,
  scopes: readonly RevealScope[],
): boolean {
  for (const scope of scopes) {
    if (from < scope.to && to > scope.from) {
      return true;
    }
  }
  return false;
}
