import React from "react";

function decodeEntities(s: string): string {
  return s
    .replaceAll("&nbsp;", " ")
    .replaceAll("&amp;", "&")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&#39;", "'")
    .replaceAll("&#039;", "'");
}

function normalizeSnippetText(s: string): string {
  return s
    .replace(/\u00A0/g, " ")
    .replace(/\s*\n+\s*/g, " ")
    .replace(/\s{2,}/g, " ")
    .trim();
}

function escapeHtml(s: string): string {
  return s
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

/**
 * OpenSearch highlight returns HTML tags (typically <em>).
 * We render only <em> safely by escaping everything, then rehydrating em spans.
 */
export function renderHighlightedSnippet(snippet: string): React.ReactNode {
  // Preserve <em> tags while decoding other HTML entities and normalizing whitespace.
  const withTokens = snippet
    .replaceAll("<em>", "__EM_OPEN__")
    .replaceAll("</em>", "__EM_CLOSE__");
  const decoded = normalizeSnippetText(decodeEntities(withTokens))
    .replaceAll("__EM_OPEN__", "<em>")
    .replaceAll("__EM_CLOSE__", "</em>");

  const safe = escapeHtml(decoded);
  const parts = safe.split("&lt;em&gt;").flatMap((p) => p.split("&lt;/em&gt;"));
  const nodes: React.ReactNode[] = [];
  for (let i = 0; i < parts.length; i++) {
    const text = parts[i] ?? "";
    const isEm = i % 2 === 1;
    if (!text) continue;
    nodes.push(
      isEm ? (
        <mark
          key={i}
          className="rounded bg-accent-200/70 px-1 py-0.5 font-medium text-ink-900"
        >
          {text}
        </mark>
      ) : (
        <span key={i}>{text}</span>
      )
    );
  }
  return nodes.length ? nodes : snippet;
}
