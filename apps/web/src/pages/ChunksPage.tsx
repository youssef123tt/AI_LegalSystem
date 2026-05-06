import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { listChunks } from "../lib/api";
import { Badge, Button, Card, Input, Label } from "../components/ui";

export default function ChunksPage() {
  const [documentId, setDocumentId] = useState("");
  const [find, setFind] = useState("");

  const q = useQuery({
    queryKey: ["chunks", documentId],
    queryFn: () => listChunks(documentId, 200, 0),
    enabled: documentId.trim().length > 0
  });

  const filtered = useMemo(() => {
    if (!q.data) return [];
    const f = find.trim().toLowerCase();
    if (!f) return q.data;
    return q.data.filter((c) => c.text.toLowerCase().includes(f));
  }, [q.data, find]);

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="font-display text-xl font-black text-ink-900">Document Chunks</div>
          <div className="mt-1 text-sm text-ink-700">Loads chunks from Postgres (source of truth).</div>
        </div>
        {q.data ? <Badge tone="info">{filtered.length} chunks</Badge> : null}
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-[1fr_260px_auto]">
        <div>
          <Label>Document ID</Label>
          <Input value={documentId} onChange={(e) => setDocumentId(e.target.value)} placeholder="uuid..." />
        </div>
        <div>
          <Label>Find (client-side)</Label>
          <Input value={find} onChange={(e) => setFind(e.target.value)} placeholder="search inside chunk text..." />
        </div>
        <div className="flex items-end">
          <Button type="button" onClick={() => q.refetch()} disabled={!documentId.trim()}>
            Refresh
          </Button>
        </div>
      </div>

      {q.isError ? (
        <div className="mt-4 rounded-lg bg-rose-50 p-3 text-sm font-semibold text-rose-800 ring-1 ring-rose-200">
          {(q.error as Error).message}
        </div>
      ) : null}

      {filtered.length ? (
        <div className="mt-5 space-y-3">
          {filtered.slice(0, 60).map((c) => (
            <div key={c.id} className="rounded-xl bg-white/70 p-4 ring-1 ring-black/5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-xs text-ink-700">
                  <span className="font-bold">ordinal</span> {c.ordinal}
                </div>
                <div className="font-mono text-xs text-ink-700">{c.id}</div>
              </div>
              {c.section_path && c.section_path.length ? (
                <div className="mt-2 text-xs text-ink-700">
                  <span className="font-bold">section</span>{" "}
                  <span className="font-mono">{c.section_path.join(" > ")}</span>
                </div>
              ) : null}
              <div className="mt-3 whitespace-pre-wrap text-sm leading-relaxed text-ink-900">{c.text}</div>
            </div>
          ))}
          {filtered.length > 60 ? <div className="text-xs text-ink-600">Showing first 60 chunks. Narrow using Find.</div> : null}
        </div>
      ) : (
        <div className="mt-5 text-sm text-ink-700">
          {q.isLoading ? "Loading..." : "No chunks found. Make sure the job status is complete."}
        </div>
      )}
    </Card>
  );
}
