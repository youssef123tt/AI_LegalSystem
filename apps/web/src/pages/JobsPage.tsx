import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getJob } from "../lib/api";
import { Badge, Button, Card, Input, Label } from "../components/ui";

function statusTone(status: string) {
  if (status === "complete") return "ok";
  if (status === "processing") return "info";
  if (status === "queued") return "neutral";
  if (status === "needs_ocr") return "warn";
  if (status === "failed") return "bad";
  return "neutral";
}

export default function JobsPage() {
  const [jobId, setJobId] = useState("");

  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    enabled: jobId.trim().length > 0,
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      if (!status) return false;
      if (status === "complete" || status === "failed" || status === "needs_ocr") return false;
      return 1500;
    }
  });

  return (
    <Card className="p-6">
      <div className="font-display text-xl font-black text-ink-900">Job Status</div>
      <div className="mt-1 text-sm text-ink-700">Paste a job ID to poll ingestion progress.</div>

      <div className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-[1fr_auto]">
        <div>
          <Label>Job ID</Label>
          <Input value={jobId} onChange={(e) => setJobId(e.target.value)} placeholder="uuid..." />
        </div>
        <div className="flex items-end">
          <Button type="button" onClick={() => job.refetch()} disabled={!jobId.trim()}>
            Refresh
          </Button>
        </div>
      </div>

      {job.isError ? (
        <div className="mt-4 rounded-lg bg-rose-50 p-3 text-sm font-semibold text-rose-800 ring-1 ring-rose-200">
          {(job.error as Error).message}
        </div>
      ) : null}

      {job.data ? (
        <div className="mt-5 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-sm text-ink-700">
              Document: <span className="font-mono text-ink-900">{job.data.document_id}</span>
            </div>
            <Badge tone={statusTone(job.data.status)}>{job.data.status}</Badge>
          </div>

          {job.data.needs_review ? (
            <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200">
              This document was processed, but extraction quality looks suspicious. It may require OCR later.
            </div>
          ) : null}

          {(job.data.extraction_method || job.data.quality_score != null) ? (
            <div className="rounded-lg bg-paper p-3 text-xs text-ink-800 ring-1 ring-black/5">
              <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                <div>
                  <span className="font-bold">extraction_method</span>{" "}
                  <span className="font-mono">{job.data.extraction_method ?? "-"}</span>
                </div>
                <div>
                  <span className="font-bold">quality_score</span>{" "}
                  <span className="font-mono">{job.data.quality_score ?? "-"}</span>
                </div>
                <div>
                  <span className="font-bold">has_tounicode</span>{" "}
                  <span className="font-mono">
                    {job.data.has_tounicode === null || job.data.has_tounicode === undefined
                      ? "-"
                      : String(job.data.has_tounicode)}
                  </span>
                </div>
                <div>
                  <span className="font-bold">indexed</span>{" "}
                  <span className="font-mono">
                    {job.data.indexed === null || job.data.indexed === undefined ? "-" : String(job.data.indexed)}
                  </span>
                </div>
                <div>
                  <span className="font-bold">arabic_letters</span>{" "}
                  <span className="font-mono">{job.data.arabic_letter_count ?? "-"}</span>
                </div>
                <div>
                  <span className="font-bold">presentation_forms</span>{" "}
                  <span className="font-mono">{job.data.arabic_presentation_forms ?? "-"}</span>
                </div>
              </div>
            </div>
          ) : null}

          {job.data.error_message ? (
            <div className="rounded-lg bg-amber-50 p-3 text-sm text-amber-900 ring-1 ring-amber-200">
              <div className="text-xs font-bold uppercase tracking-wide text-amber-900/80">Message</div>
              <div className="mt-1 font-mono text-xs">{job.data.error_message}</div>
            </div>
          ) : null}

          {job.data.status === "needs_ocr" ? (
            <div className="rounded-lg bg-paper p-3 text-sm text-ink-800 ring-1 ring-black/5">
              This file is likely a scanned PDF. Milestone 3 does not OCR scans, so it stops here. OCR will be added in
              Milestone 4.
            </div>
          ) : null}
        </div>
      ) : (
        <div className="mt-5 text-sm text-ink-700">
          No job loaded yet. Upload a document first, then paste the returned job ID here.
        </div>
      )}
    </Card>
  );
}
