import React, { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { search } from "../lib/api";
import type { SearchFilters } from "../lib/types";
import { renderHighlightedSnippet } from "../lib/snippet";
import { Badge, Button, Card, Input, Label } from "../components/ui";

export default function SearchPage() {
  const [query, setQuery] = useState("Regulation");
  const [mode, setMode] = useState<"hybrid" | "keyword" | "vector">("hybrid");
  const [jurisdiction, setJurisdiction] = useState("");
  const [lawType, setLawType] = useState("");
  const [yearMin, setYearMin] = useState<string>("");
  const [yearMax, setYearMax] = useState<string>("");
  const [keywordWeight, setKeywordWeight] = useState<string>("1");
  const [vectorWeight, setVectorWeight] = useState<string>("1");

  const m = useMutation({
    mutationFn: async () => {
      const filters: SearchFilters = {};
      if (jurisdiction.trim()) filters.jurisdiction = jurisdiction.trim();
      if (lawType.trim()) filters.law_type = lawType.trim();
      if (yearMin.trim()) filters.year_min = Number(yearMin);
      if (yearMax.trim()) filters.year_max = Number(yearMax);

      return search({
        query: query.trim() || "*",
        filters: Object.keys(filters).length ? filters : null,
        top_k: 10,
        mode,
        keyword_weight: mode === "hybrid" ? Number(keywordWeight || "1") : undefined,
        vector_weight: mode === "hybrid" ? Number(vectorWeight || "1") : undefined
      });
    }
  });

  const err = useMemo(() => (m.error as Error | null)?.message ?? null, [m.error]);

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="font-display text-xl font-black text-ink-900">Keyword Search</div>
          <div className="mt-1 text-sm text-ink-700">
            Milestone 3 uses BM25 keyword search (no vectors yet). Use filters only if you set real metadata on upload.
          </div>
        </div>
        {m.data ? <Badge tone="info">{m.data.hits.length} hits</Badge> : null}
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2">
        <div className="md:col-span-2">
          <Label>Query</Label>
          <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search text..." />
        </div>
        <div>
          <Label>Mode</Label>
          <select
            className="w-full rounded-lg border border-black/10 bg-white/80 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-accent-300/70"
            value={mode}
            onChange={(e) => setMode(e.target.value as any)}
          >
            <option value="hybrid">hybrid</option>
            <option value="keyword">keyword</option>
            <option value="vector">vector</option>
          </select>
        </div>
        <div>
          <Label>Jurisdiction (optional)</Label>
          <Input value={jurisdiction} onChange={(e) => setJurisdiction(e.target.value)} placeholder="US" />
        </div>
        <div>
          <Label>Law Type (optional)</Label>
          <Input value={lawType} onChange={(e) => setLawType(e.target.value)} placeholder="contract" />
        </div>
        <div>
          <Label>Year Min (optional)</Label>
          <Input value={yearMin} onChange={(e) => setYearMin(e.target.value)} placeholder="2010" />
        </div>
        <div>
          <Label>Year Max (optional)</Label>
          <Input value={yearMax} onChange={(e) => setYearMax(e.target.value)} placeholder="2030" />
        </div>

        {mode === "hybrid" ? (
          <>
            <div>
              <Label>Keyword Weight</Label>
              <Input value={keywordWeight} onChange={(e) => setKeywordWeight(e.target.value)} placeholder="1.0" />
            </div>
            <div>
              <Label>Vector Weight</Label>
              <Input value={vectorWeight} onChange={(e) => setVectorWeight(e.target.value)} placeholder="1.0" />
            </div>
          </>
        ) : null}

        <div className="md:col-span-2 flex items-center gap-2">
          <Button type="button" onClick={() => m.mutate()} disabled={m.isPending}>
            {m.isPending ? "Searching..." : "Search"}
          </Button>
          {err ? <div className="text-sm font-semibold text-rose-700">{err}</div> : null}
        </div>
      </div>

      {m.data ? (
        <div className="mt-6 space-y-3">
          {m.data.hits.map((h) => (
            <div key={h.chunk_id} className="rounded-xl bg-white/70 p-4 ring-1 ring-black/5">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="font-display text-lg font-black text-ink-900">{h.document_title ?? "Untitled document"}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-700">
                    {h.jurisdiction ? <Badge>{h.jurisdiction}</Badge> : null}
                    {typeof h.year === "number" ? <Badge>{h.year}</Badge> : null}
                    {h.law_type ? <Badge>{h.law_type}</Badge> : null}
                    {typeof h.score === "number" ? <span className="font-mono">score={h.score.toFixed(3)}</span> : null}
                  </div>
                </div>
                <div className="text-right text-xs text-ink-600">
                  <div className="font-mono">{h.chunk_id}</div>
                  {typeof h.ordinal === "number" ? <div>ordinal {h.ordinal}</div> : null}
                </div>
              </div>
              <div className="mt-3 text-sm leading-relaxed text-ink-900">{renderHighlightedSnippet(h.snippet)}</div>
              {h.section_path && h.section_path.length ? (
                <div className="mt-2 text-xs text-ink-700">
                  <span className="font-bold">Section:</span>{" "}
                  <span className="font-mono">{h.section_path.join(" > ")}</span>
                </div>
              ) : null}
              {h.citations && h.citations.length ? (
                <div className="mt-3 flex flex-wrap gap-2 text-xs">
                  <span className="font-bold text-ink-700">Citations:</span>
                  {h.citations.slice(0, 6).map((c) => (
                    <span key={c} className="rounded-full bg-black/5 px-2 py-0.5 font-mono text-ink-800 ring-1 ring-black/10">
                      {c}
                    </span>
                  ))}
                  {h.citations.length > 6 ? (
                    <span className="text-ink-600">+{h.citations.length - 6} more</span>
                  ) : null}
                </div>
              ) : null}
            </div>
          ))}

          {m.data.hits.length === 0 ? (
            <div className="rounded-lg bg-paper p-3 text-sm text-ink-800 ring-1 ring-black/5">
              No hits. If you used filters, confirm you set the same metadata values during upload (exact match).
            </div>
          ) : null}
        </div>
      ) : (
        <div className="mt-6 text-sm text-ink-700">
          Run a search to see results. If you already have chunks in Postgres but no search hits, ensure the worker job
          completed and indexed into OpenSearch.
        </div>
      )}
    </Card>
  );
}
