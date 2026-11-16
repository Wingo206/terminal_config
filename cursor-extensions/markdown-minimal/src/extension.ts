import * as vscode from 'vscode';
import { isMarkdownEditor, MinimalMarkdownDecorator } from './decorator.ts';
import {
  MinimalDocumentLinkProvider,
  OPEN_LINK_COMMAND,
  openMarkdownLink,
} from './links.ts';

const DOCUMENT_SELECTOR: vscode.DocumentSelector = [
  { language: 'markdown' },
  { language: 'mdx' },
];

export function activate(context: vscode.ExtensionContext): void {
  const decorator = new MinimalMarkdownDecorator();
  const linkProvider = new MinimalDocumentLinkProvider((doc) =>
    decorator.getLinksForDocument(doc),
  );

  decorator.refreshVisibleEditors();

  context.subscriptions.push(
    decorator,
    vscode.languages.registerDocumentLinkProvider(DOCUMENT_SELECTOR, linkProvider),
    vscode.commands.registerCommand(OPEN_LINK_COMMAND, openMarkdownLink),
    vscode.commands.registerCommand('markdownMinimal.toggle', () => {
      const enabled = decorator.toggle();
      vscode.window.setStatusBarMessage(
        `Markdown Minimal: inline styling ${enabled ? 'enabled' : 'disabled'}`,
        2000,
      );
    }),
    vscode.window.onDidChangeActiveTextEditor((editor) => {
      decorator.applyToEditor(editor);
    }),
    vscode.window.onDidChangeVisibleTextEditors(() => {
      decorator.refreshVisibleEditors();
    }),
    vscode.window.onDidChangeTextEditorSelection((event) => {
      if (isMarkdownEditor(event.textEditor)) {
        decorator.applyToEditor(event.textEditor);
      }
    }),
    vscode.window.onDidChangeTextEditorOptions((event) => {
      if (isMarkdownEditor(event.textEditor)) {
        decorator.applyToEditor(event.textEditor);
      }
    }),
    vscode.workspace.onDidChangeTextDocument((event) => {
      if (event.document.languageId === 'markdown' || event.document.languageId === 'mdx') {
        decorator.scheduleDocumentRefresh(event.document);
      }
    }),
    vscode.workspace.onDidCloseTextDocument((document) => {
      decorator.invalidateDocument(document);
    }),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (event.affectsConfiguration('markdownMinimal')) {
        decorator.reloadConfig();
      }
    }),
    vscode.window.onDidChangeActiveColorTheme(() => {
      decorator.reloadConfig();
    }),
  );
}

export function deactivate(): void {}
