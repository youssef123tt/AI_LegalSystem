import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getOutline } from "../lib/api";
import { Badge, Button, Card, Input, Label } from "../components/ui";

export default function OutlinePage() {
  const [documentId, setDocumentId] = useState("");

  const q = useQuery({
    queryKey: ["outline", documentId],
    queryFn: () => getOutline(documentId),
    enabled: documentId.trim().length > 0
  });

  return (
    <Card className="p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="font-display text-xl font-black text-ink-900">Document Outline</div>
          <div className="mt-1 text-sm text-ink-700">
            Derived from chunk section paths (Milestone 6 section-aware chunking).
          </div>
        </div>
        {q.data ? <Badge tone="info">{q.data.length} sections</Badge> : null}
      </div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-[1fr_auto]">
        <div>
          <Label>Document ID</Label>
          <Input value={documentId} onChange={(e) => setDocumentId(e.target.value)} placeholder="uuid..." />
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

      {q.data && q.data.length ? (
        <div className="mt-5 space-y-2">
          {q.data.map((s) => (
            <div key={s.first_ordinal} className="rounded-lg bg-white/70 px-3 py-2 ring-1 ring-black/5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="text-sm font-semibold text-ink-900">
                  {s.path.length ? s.path.join(" > ") : "(No headings detected)"}
                </div>
                <div className="text-xs text-ink-700">
                  <span className="font-mono">{s.chunk_count}</span> chunks
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-5 text-sm text-ink-700">
          {q.isLoading ? "Loading..." : "No outline yet. Reprocess the document so chunks get section paths."}
        </div>
      )}
    </Card>
  );
}

