import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import * as vscode from 'vscode';
import type { ParsedLink } from './scanner.ts';

export const OPEN_LINK_COMMAND = 'markdownMinimal.openLink';

export interface LineSpan {
  startLine: number;
  startCol?: number;
  endLine?: number;
  endCol?: number;
}

export function parseLineFragment(fragment: string): LineSpan | null {
  const match =
    /^L?(?<startLine>\d+)(?:,(?<startCol>\d+))?(?:-L?(?<endLine>\d+)(?:,(?<endCol>\d+))?)?$/i.exec(
      fragment.trim(),
    );
  if (!match?.groups) {
    return null;
  }
  const startLine = Number.parseInt(match.groups.startLine, 10);
  if (!Number.isFinite(startLine) || startLine < 1) {
    return null;
  }
  const startCol = match.groups.startCol
    ? Math.max(1, Number.parseInt(match.groups.startCol, 10))
    : undefined;
  const endLine = match.groups.endLine
    ? Math.max(1, Number.parseInt(match.groups.endLine, 10))
    : undefined;
  const endCol = match.groups.endCol
    ? Math.max(1, Number.parseInt(match.groups.endCol, 10))
    : undefined;
  return { startLine, startCol, endLine, endCol };
}

export function splitHref(rawUrl: string): { pathPart: string; fragment: string; colonSpan: LineSpan | null } {
  const trimmed = rawUrl.trim();
  const hashIdx = trimmed.indexOf('#');
  let pathPart = hashIdx === -1 ? trimmed : trimmed.slice(0, hashIdx);
  const fragment = hashIdx === -1 ? '' : trimmed.slice(hashIdx + 1);

  let colonSpan: LineSpan | null = null;
  if (!fragment) {
    const colonMatch = /^(.*\.[A-Za-z0-9_]+):(\d+)(?:-(\d+))?$/.exec(pathPart);
    if (colonMatch) {
      pathPart = colonMatch[1];
      colonSpan = {
        startLine: Number.parseInt(colonMatch[2], 10),
        endLine: colonMatch[3] ? Number.parseInt(colonMatch[3], 10) : undefined,
      };
    }
  }

  return { pathPart, fragment, colonSpan };
}

export function slugifyHeading(raw: string): string {
  return raw
    .trim()
    .toLowerCase()
    .replace(/[`*_~[\]()]/g, '')
    .replace(/[^\p{L}\p{N}\s-]/gu, '')
    .trim()
    .replace(/\s+/g, '-');
}

function decodePath(raw: string): string {
  try {
    return decodeURIComponent(raw);
  } catch {
    return raw;
  }
}

function findEnclosingGitRoot(fsPath: string): string | null {
  let current = fsPath;
  for (let depth = 0; depth < 5; depth++) {
    if (existsSync(join(current, '.git'))) {
      return current;
    }
    const parent = dirname(current);
    if (parent === current) {
      break;
    }
    current = parent;
  }
  return null;
}

async function uriExists(uri: vscode.Uri): Promise<boolean> {
  try {
    await vscode.workspace.fs.stat(uri);
    return true;
  } catch {
    return false;
  }
}

async function resolveTargetFileUri(decodedPath: string, sourceDocUri: vscode.Uri): Promise<vscode.Uri> {
  const wsFolder =
    vscode.workspace.getWorkspaceFolder(sourceDocUri)?.uri ??
    vscode.workspace.workspaceFolders?.[0]?.uri;
  const gitRootPath = wsFolder?.scheme === 'file' ? findEnclosingGitRoot(wsFolder.fsPath) : null;
  const gitRootUri =
    gitRootPath && gitRootPath !== wsFolder?.fsPath ? vscode.Uri.file(gitRootPath) : null;

  const candidates: vscode.Uri[] = [];
  if (decodedPath.startsWith('/')) {
    if (wsFolder) {
      candidates.push(vscode.Uri.joinPath(wsFolder, decodedPath));
    }
    if (gitRootUri) {
      candidates.push(vscode.Uri.joinPath(gitRootUri, decodedPath));
    }
    candidates.push(vscode.Uri.file(decodedPath));
  } else {
    candidates.push(vscode.Uri.joinPath(sourceDocUri, '..', decodedPath));
    if (wsFolder) {
      candidates.push(vscode.Uri.joinPath(wsFolder, decodedPath));
    }
    if (gitRootUri) {
      candidates.push(vscode.Uri.joinPath(gitRootUri, decodedPath));
    }
  }

  for (const candidate of candidates) {
    if (await uriExists(candidate)) {
      return candidate;
    }
  }
  return candidates[0];
}

export async function openMarkdownLink(
  rawArg: string | unknown[],
  maybeDocUri?: string,
): Promise<void> {
  let rawUrl = '';
  let docUriStr = maybeDocUri;
  if (Array.isArray(rawArg)) {
    rawUrl = String(rawArg[0] ?? '');
    docUriStr = typeof rawArg[1] === 'string' ? rawArg[1] : docUriStr;
  } else {
    rawUrl = String(rawArg ?? '');
  }

  if (!rawUrl || !docUriStr) {
    return;
  }

  const sourceDocUri = vscode.Uri.parse(docUriStr);
  const { pathPart, fragment, colonSpan } = splitHref(rawUrl);

  const targetUri = pathPart
    ? await resolveTargetFileUri(decodePath(pathPart), sourceDocUri)
    : sourceDocUri;

  const lineSpan = (fragment ? parseLineFragment(fragment) : null) ?? colonSpan;
  const document = await vscode.workspace.openTextDocument(targetUri);

  if (lineSpan) {
    const maxLine = Math.max(0, document.lineCount - 1);
    const startLine = Math.min(Math.max(0, lineSpan.startLine - 1), maxLine);
    const startCol = lineSpan.startCol ? Math.max(0, lineSpan.startCol - 1) : 0;
    const startPos = new vscode.Position(startLine, startCol);

    let endPos = startPos;
    if (lineSpan.endLine !== undefined) {
      const endLine = Math.min(Math.max(0, lineSpan.endLine - 1), maxLine);
      const endCol = lineSpan.endCol
        ? Math.max(0, lineSpan.endCol - 1)
        : document.lineAt(endLine).text.length;
      endPos = new vscode.Position(endLine, endCol);
    }

    const selection = new vscode.Range(startPos, endPos);
    const editor = await vscode.window.showTextDocument(document, {
      selection,
      preserveFocus: false,
    });
    editor.revealRange(selection, vscode.TextEditorRevealType.InCenterIfOutsideViewport);
    return;
  }

  const editor = await vscode.window.showTextDocument(document, { preserveFocus: false });

  if (fragment) {
    const wanted = slugifyHeading(decodePath(fragment));
    const lines = document.getText().split(/\r?\n/);
    for (let i = 0; i < lines.length; i++) {
      const m = /^ {0,3}#{1,6}[ \t]+(.+?)[ \t]*$/.exec(lines[i]);
      if (m && (slugifyHeading(m[1]) === wanted || m[1].trim().toLowerCase() === wanted)) {
        const pos = new vscode.Position(i, 0);
        editor.selection = new vscode.Selection(pos, pos);
        editor.revealRange(new vscode.Range(pos, pos), vscode.TextEditorRevealType.InCenter);
        return;
      }
    }
  }
}

function toCommandUri(args: unknown[]): vscode.Uri {
  return vscode.Uri.parse(
    `command:${OPEN_LINK_COMMAND}?${encodeURIComponent(JSON.stringify(args))}`,
  );
}

export class MinimalDocumentLinkProvider implements vscode.DocumentLinkProvider {
  constructor(private readonly getLinks: (doc: vscode.TextDocument) => readonly ParsedLink[]) {}

  provideDocumentLinks(document: vscode.TextDocument): vscode.DocumentLink[] {
    const parsedLinks = this.getLinks(document);
    const out: vscode.DocumentLink[] = [];

    for (const item of parsedLinks) {
      if (item.labelTo <= item.labelFrom) {
        continue;
      }
      const range = new vscode.Range(
        document.positionAt(item.labelFrom),
        document.positionAt(item.labelTo),
      );
      const trimmed = item.url.trim();

      let target: vscode.Uri | undefined;
      if (/^(?:https?:|mailto:)/i.test(trimmed)) {
        try {
          target = vscode.Uri.parse(trimmed);
        } catch {
          continue;
        }
      } else {
        target = toCommandUri([trimmed, document.uri.toString()]);
      }

      const docLink = new vscode.DocumentLink(range, target);
      docLink.tooltip = trimmed;
      out.push(docLink);
    }

    return out;
  }
}
