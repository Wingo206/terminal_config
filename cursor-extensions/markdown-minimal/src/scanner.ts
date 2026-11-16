export type DecorationKind =
  | 'hide'
  | 'transparent'
  | 'faint'
  | 'linkSyntaxFaint'
  | 'heading1'
  | 'heading2'
  | 'heading3'
  | 'heading4'
  | 'heading5'
  | 'heading6'
  | 'bold'
  | 'italic'
  | 'boldItalic'
  | 'strikethrough'
  | 'inlineCode'
  | 'link'
  | 'codeBlockLine'
  | 'frontmatterLine'
  | 'blockquoteLine'
  | 'horizontalRuleLine';

export interface TokenRange {
  kind: DecorationKind;
  from: number;
  to: number;
}

export interface RevealScope {
  from: number;
  to: number;
}

export interface ParsedLink {
  labelFrom: number;
  labelTo: number;
  urlFrom: number;
  urlTo: number;
  url: string;
}

export interface ScanResult {
  tokens: TokenRange[];
  scopes: RevealScope[];
  links: ParsedLink[];
}

const WHOLE_LINE_KINDS = new Set<DecorationKind>([
  'codeBlockLine',
  'frontmatterLine',
  'blockquoteLine',
  'horizontalRuleLine',
]);

interface PairedMarker {
  marker: string;
  kind: 'boldItalic' | 'bold' | 'italic' | 'strikethrough';
}

const PAIRED_MARKERS: readonly PairedMarker[] = [
  { marker: '***', kind: 'boldItalic' },
  { marker: '___', kind: 'boldItalic' },
  { marker: '**', kind: 'bold' },
  { marker: '__', kind: 'bold' },
  { marker: '~~', kind: 'strikethrough' },
  { marker: '*', kind: 'italic' },
  { marker: '_', kind: 'italic' },
];

export function isWholeLineKind(kind: DecorationKind): boolean {
  return WHOLE_LINE_KINDS.has(kind);
}

export function scanMarkdown(doc: string): ScanResult {
  const tokens: TokenRange[] = [];
  const scopes: RevealScope[] = [];
  const links: ParsedLink[] = [];

  if (!doc) {
    return { tokens, scopes, links };
  }

  const lines: { text: string; start: number; end: number }[] = [];
  let cursor = 0;
  while (cursor <= doc.length) {
    const nl = doc.indexOf('\n', cursor);
    if (nl === -1) {
      const end = doc.endsWith('\r') ? doc.length - 1 : doc.length;
      lines.push({ text: doc.slice(cursor, end), start: cursor, end });
      break;
    }
    const end = nl > cursor && doc[nl - 1] === '\r' ? nl - 1 : nl;
    lines.push({ text: doc.slice(cursor, end), start: cursor, end });
    cursor = nl + 1;
    if (cursor === doc.length && nl === doc.length - 1) {
      lines.push({ text: '', start: cursor, end: cursor });
      break;
    }
  }

  const pushToken = (kind: DecorationKind, from: number, to: number): void => {
    if (to > from || (to === from && WHOLE_LINE_KINDS.has(kind))) {
      tokens.push({ kind, from, to });
    }
  };

  let lineIdx = 0;

  // 1. YAML frontmatter at top of file
  if (lines.length >= 2 && lines[0].text.trim() === '---') {
    let fmEnd = -1;
    for (let j = 1; j < lines.length; j++) {
      if (lines[j].text.trim() === '---') {
        fmEnd = j;
        break;
      }
    }
    if (fmEnd !== -1) {
      scopes.push({ from: lines[0].start, to: lines[fmEnd].end });
      for (let j = 0; j <= fmEnd; j++) {
        pushToken('frontmatterLine', lines[j].start, lines[j].end);
      }
      pushToken('faint', lines[0].start, lines[0].end);
      pushToken('faint', lines[fmEnd].start, lines[fmEnd].end);
      lineIdx = fmEnd + 1;
    }
  }

  let inHtmlComment = false;

  while (lineIdx < lines.length) {
    const line = lines[lineIdx];
    const text = line.text;

    // Multi-line HTML comment continuation
    if (inHtmlComment) {
      const closeComment = text.indexOf('-->');
      if (closeComment === -1) {
        pushToken('faint', line.start, line.end);
        lineIdx++;
        continue;
      }
      const closeEnd = closeComment + 3;
      pushToken('faint', line.start, line.start + closeEnd);
      scopes.push({ from: line.start, to: line.start + closeEnd });
      inHtmlComment = false;
      if (closeEnd < text.length) {
        scanInline(text.slice(closeEnd), line.start + closeEnd, pushToken, scopes, links);
      }
      lineIdx++;
      continue;
    }

    // 2. Fenced code block (` ``` ` or `~~~`)
    const fenceMatch = /^( {0,3})(`{3,}|~{3,})(.*)$/.exec(text);
    if (fenceMatch && !(fenceMatch[2][0] === '`' && fenceMatch[3].includes('`'))) {
      const indentLen = fenceMatch[1].length;
      const fenceChars = fenceMatch[2];
      const fenceChar = fenceChars[0];
      const infoStr = fenceMatch[3];

      let closeLine = -1;
      const closeRe = new RegExp(`^ {0,3}${fenceChar}{${fenceChars.length},}[ \\t]*$`);
      for (let j = lineIdx + 1; j < lines.length; j++) {
        if (closeRe.test(lines[j].text)) {
          closeLine = j;
          break;
        }
      }

      const lastLine = closeLine !== -1 ? closeLine : lines.length - 1;
      scopes.push({ from: line.start, to: lines[lastLine].end });

      for (let j = lineIdx; j <= lastLine; j++) {
        pushToken('codeBlockLine', lines[j].start, lines[j].end);
      }

      const openFenceStart = line.start + indentLen;
      const openFenceEnd = openFenceStart + fenceChars.length;
      pushToken('hide', openFenceStart, openFenceEnd);
      if (infoStr.trim().length > 0) {
        pushToken('faint', openFenceEnd, line.end);
      }

      if (closeLine !== -1) {
        pushToken('hide', lines[closeLine].start, lines[closeLine].end);
      }

      lineIdx = lastLine + 1;
      continue;
    }

    // 3. Block-start HTML comment (`<!-- ...`)
    const trimmedStart = text.trimStart();
    if (trimmedStart.startsWith('<!--')) {
      const commentStartInLine = text.indexOf('<!--');
      const closeComment = text.indexOf('-->', commentStartInLine + 4);
      if (closeComment === -1) {
        pushToken('faint', line.start + commentStartInLine, line.end);
        scopes.push({ from: line.start + commentStartInLine, to: line.end });
        inHtmlComment = true;
        lineIdx++;
        continue;
      }
    }

    // 4. Horizontal rule (`---`, `***`, `___`)
    if (/^ {0,3}([-*_])(?:\s*\1){2,}\s*$/.test(text)) {
      pushToken('horizontalRuleLine', line.start, line.end);
      pushToken('hide', line.start, line.end);
      scopes.push({ from: line.start, to: line.end });
      lineIdx++;
      continue;
    }

    // 5. Optional blockquote prefix (`> `)
    let bodyOffset = line.start;
    let body = text;
    const quoteMatch = /^( {0,3}(?:>[ \t]?)+)/.exec(text);
    if (quoteMatch) {
      const prefixLen = quoteMatch[1].length;
      pushToken('blockquoteLine', line.start, line.end);
      pushToken('faint', line.start, line.start + prefixLen);
      scopes.push({ from: line.start, to: line.start + prefixLen });
      bodyOffset += prefixLen;
      body = text.slice(prefixLen);
    }

    // 6. ATX Heading (`#` .. `######`)
    const headingMatch = /^( {0,3})(#{1,6})([ \t]+)(.+?)[ \t]*$/.exec(body);
    if (headingMatch) {
      const indentLen = headingMatch[1].length;
      const level = headingMatch[2].length as 1 | 2 | 3 | 4 | 5 | 6;
      const spaceLen = headingMatch[3].length;
      const content = headingMatch[4];

      const markerStart = bodyOffset + indentLen;
      const contentStart = markerStart + level + spaceLen;
      const contentEnd = contentStart + content.length;

      pushToken('hide', markerStart, contentStart);
      pushToken(`heading${level}`, contentStart, contentEnd);
      scopes.push({ from: line.start, to: line.end });

      scanInline(content, contentStart, pushToken, scopes, links);
      lineIdx++;
      continue;
    }

    // 7. Standard line inline formatting
    if (body.length > 0) {
      scanInline(body, bodyOffset, pushToken, scopes, links);
    }
    lineIdx++;
  }

  return { tokens, scopes, links };
}

function scanInline(
  text: string,
  baseOffset: number,
  pushToken: (kind: DecorationKind, from: number, to: number) => void,
  scopes: RevealScope[],
  links: ParsedLink[],
): void {
  let i = 0;
  while (i < text.length) {
    const ch = text[i];

    // Escaped character
    if (ch === '\\' && i + 1 < text.length) {
      i += 2;
      continue;
    }

    // Inline code (`...` or ``...``)
    if (ch === '`') {
      const runLen = countRun(text, i, '`');
      const closeIdx = findClosingBackticks(text, i + runLen, runLen);
      if (closeIdx !== -1 && closeIdx > i + runLen) {
        const spanFrom = baseOffset + i;
        const spanTo = baseOffset + closeIdx + runLen;
        pushToken('inlineCode', spanFrom, spanTo);
        pushToken('transparent', spanFrom, spanFrom + runLen);
        pushToken('transparent', spanTo - runLen, spanTo);
        scopes.push({ from: spanFrom, to: spanTo });
        i = closeIdx + runLen;
        continue;
      }
      i += runLen;
      continue;
    }

    // Single-line HTML comment (`<!-- ... -->`)
    if (ch === '<' && text.startsWith('<!--', i)) {
      const closeIdx = text.indexOf('-->', i + 4);
      if (closeIdx !== -1) {
        const spanFrom = baseOffset + i;
        const spanTo = baseOffset + closeIdx + 3;
        pushToken('faint', spanFrom, spanTo);
        scopes.push({ from: spanFrom, to: spanTo });
        i = closeIdx + 3;
        continue;
      }
    }

    // Autolink (`<https://...>` or `<mailto:...>`)
    if (ch === '<') {
      const autoMatch = /^<(https?:\/\/[^\s<>]+|mailto:[^\s<>]+)>/i.exec(text.slice(i));
      if (autoMatch) {
        const fullLen = autoMatch[0].length;
        const innerUrl = autoMatch[1];
        const spanFrom = baseOffset + i;
        const spanTo = spanFrom + fullLen;
        pushToken('linkSyntaxFaint', spanFrom, spanFrom + 1);
        pushToken('link', spanFrom + 1, spanTo - 1);
        pushToken('linkSyntaxFaint', spanTo - 1, spanTo);
        scopes.push({ from: spanFrom, to: spanTo });
        links.push({
          labelFrom: spanFrom + 1,
          labelTo: spanTo - 1,
          urlFrom: spanFrom + 1,
          urlTo: spanTo - 1,
          url: innerUrl,
        });
        i += fullLen;
        continue;
      }
    }

    // Markdown link `[label](url)` or image `![alt](url)`
    if (ch === '[' || (ch === '!' && text[i + 1] === '[')) {
      const parsed = tryParseBracketLink(text, i);
      if (parsed) {
        const spanFrom = baseOffset + i;
        const labelFrom = baseOffset + parsed.openBracket + 1;
        const labelTo = baseOffset + parsed.closeBracket;
        const spanTo = baseOffset + parsed.closeParen + 1;

        pushToken('linkSyntaxFaint', spanFrom, labelFrom);
        if (labelTo > labelFrom) {
          pushToken('link', labelFrom, labelTo);
          scanInline(
            text.slice(parsed.openBracket + 1, parsed.closeBracket),
            labelFrom,
            pushToken,
            scopes,
            links,
          );
        }
        pushToken('linkSyntaxFaint', labelTo, spanTo);
        scopes.push({ from: spanFrom, to: spanTo });

        if (!parsed.isImage && parsed.url.length > 0 && labelTo > labelFrom) {
          links.push({
            labelFrom,
            labelTo,
            urlFrom: baseOffset + parsed.urlFrom,
            urlTo: baseOffset + parsed.urlTo,
            url: parsed.url,
          });
        }

        i = parsed.closeParen + 1;
        continue;
      }
    }

    // Paired emphasis / strikethrough markers (`***`, `**`, `*`, `___`, `__`, `_`, `~~`)
    const paired = matchOpeningPaired(text, i);
    if (paired) {
      const mLen = paired.marker.length;
      const contentStart = i + mLen;
      const closeIdx = findClosingPaired(text, contentStart, paired.marker);
      if (closeIdx !== -1 && closeIdx > contentStart) {
        const spanFrom = baseOffset + i;
        const innerFrom = baseOffset + contentStart;
        const innerTo = baseOffset + closeIdx;
        const spanTo = innerTo + mLen;

        pushToken('hide', spanFrom, innerFrom);
        pushToken(paired.kind, innerFrom, innerTo);
        pushToken('hide', innerTo, spanTo);
        scopes.push({ from: spanFrom, to: spanTo });

        scanInline(text.slice(contentStart, closeIdx), innerFrom, pushToken, scopes, links);
        i = closeIdx + mLen;
        continue;
      }
    }

    i++;
  }
}

function countRun(text: string, index: number, char: string): number {
  let end = index;
  while (end < text.length && text[end] === char) {
    end++;
  }
  return end - index;
}

function findClosingBackticks(text: string, from: number, targetLen: number): number {
  let j = from;
  while (j < text.length) {
    if (text[j] === '`') {
      const len = countRun(text, j, '`');
      if (len === targetLen) {
        return j;
      }
      j += len;
      continue;
    }
    j++;
  }
  return -1;
}

interface BracketLinkMatch {
  isImage: boolean;
  openBracket: number;
  closeBracket: number;
  closeParen: number;
  urlFrom: number;
  urlTo: number;
  url: string;
}

function tryParseBracketLink(text: string, start: number): BracketLinkMatch | null {
  const isImage = text[start] === '!';
  const openBracket = isImage ? start + 1 : start;

  // Leave Obsidian `[[wikilinks]]` and `[^footnotes]` untouched
  if (text[openBracket + 1] === '[' || text[openBracket + 1] === '^') {
    return null;
  }

  // Find matching `]`, skipping escapes, inline code spans, and nested `[...]`
  let depth = 1;
  let j = openBracket + 1;
  let closeBracket = -1;
  while (j < text.length) {
    const c = text[j];
    if (c === '\\' && j + 1 < text.length) {
      j += 2;
      continue;
    }
    if (c === '`') {
      const ticks = countRun(text, j, '`');
      const endTicks = findClosingBackticks(text, j + ticks, ticks);
      j = endTicks !== -1 ? endTicks + ticks : j + ticks;
      continue;
    }
    if (c === '[') {
      depth++;
    } else if (c === ']') {
      depth--;
      if (depth === 0) {
        closeBracket = j;
        break;
      }
    }
    j++;
  }

  if (closeBracket === -1 || text[closeBracket + 1] !== '(') {
    return null;
  }

  const openParen = closeBracket + 1;
  let p = openParen + 1;
  while (p < text.length && (text[p] === ' ' || text[p] === '\t')) {
    p++;
  }
  if (p >= text.length) {
    return null;
  }

  let urlFrom = p;
  let urlTo = p;
  let closeParen = -1;

  if (text[p] === '<') {
    const closeAngle = text.indexOf('>', p + 1);
    if (closeAngle === -1) {
      return null;
    }
    urlFrom = p + 1;
    urlTo = closeAngle;
    const restClose = findClosingParenAfterTitle(text, closeAngle + 1);
    if (restClose === -1) {
      return null;
    }
    closeParen = restClose;
  } else {
    let parenDepth = 0;
    let cursor = p;
    while (cursor < text.length) {
      const c = text[cursor];
      if (c === '\\' && cursor + 1 < text.length) {
        cursor += 2;
        continue;
      }
      if (c === '(') {
        parenDepth++;
        cursor++;
        continue;
      }
      if (c === ')') {
        if (parenDepth === 0) {
          urlTo = cursor;
          closeParen = cursor;
          break;
        }
        parenDepth--;
        cursor++;
        continue;
      }
      if ((c === ' ' || c === '\t') && parenDepth === 0) {
        urlTo = cursor;
        closeParen = findClosingParenAfterTitle(text, cursor);
        break;
      }
      cursor++;
    }
  }

  if (closeParen === -1) {
    return null;
  }

  return {
    isImage,
    openBracket,
    closeBracket,
    closeParen,
    urlFrom,
    urlTo,
    url: text.slice(urlFrom, urlTo).trim(),
  };
}

function findClosingParenAfterTitle(text: string, from: number): number {
  let p = from;
  while (p < text.length && (text[p] === ' ' || text[p] === '\t')) {
    p++;
  }
  if (p >= text.length) {
    return -1;
  }
  if (text[p] === ')') {
    return p;
  }
  const quote = text[p];
  if (quote !== '"' && quote !== "'") {
    return -1;
  }
  p++;
  while (p < text.length) {
    if (text[p] === '\\' && p + 1 < text.length) {
      p += 2;
      continue;
    }
    if (text[p] === quote) {
      p++;
      while (p < text.length && (text[p] === ' ' || text[p] === '\t')) {
        p++;
      }
      return text[p] === ')' ? p : -1;
    }
    p++;
  }
  return -1;
}

function isWordChar(ch: string | undefined): boolean {
  return ch !== undefined && /[\w]/.test(ch);
}

function isWhitespace(ch: string | undefined): boolean {
  return ch === undefined || /\s/.test(ch);
}

function matchOpeningPaired(text: string, index: number): PairedMarker | null {
  const ch = text[index];
  if (ch !== '*' && ch !== '_' && ch !== '~') {
    return null;
  }
  const runLen = countRun(text, index, ch);
  for (const candidate of PAIRED_MARKERS) {
    if (candidate.marker[0] !== ch || candidate.marker.length !== runLen) {
      continue;
    }
    const after = text[index + runLen];
    if (isWhitespace(after)) {
      return null;
    }
    if (ch === '_' && isWordChar(text[index - 1])) {
      return null;
    }
    return candidate;
  }
  return null;
}

function findClosingPaired(text: string, from: number, marker: string): number {
  const ch = marker[0];
  const mLen = marker.length;
  let j = from;

  while (j <= text.length - mLen) {
    const c = text[j];
    if (c === '\\' && j + 1 < text.length) {
      j += 2;
      continue;
    }
    // Skip inline code spans so markers inside backticks never close outer emphasis
    if (c === '`') {
      const ticks = countRun(text, j, '`');
      const endTicks = findClosingBackticks(text, j + ticks, ticks);
      j = endTicks !== -1 ? endTicks + ticks : j + ticks;
      continue;
    }
    // Skip complete `[label](url)` links so underscores or asterisks in URLs never split outer bold/italic
    if (c === '[' || (c === '!' && text[j + 1] === '[')) {
      const link = tryParseBracketLink(text, j);
      if (link) {
        j = link.closeParen + 1;
        continue;
      }
    }
    if (c === ch) {
      const runLen = countRun(text, j, ch);
      if (runLen === mLen) {
        const before = text[j - 1];
        const after = text[j + mLen];
        const validBoundary = !isWhitespace(before) && (ch !== '_' || !isWordChar(after));
        if (validBoundary) {
          return j;
        }
      }
      j += runLen;
      continue;
    }
    j++;
  }

  return -1;
}
