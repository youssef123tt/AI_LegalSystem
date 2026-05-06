import React from "react";
import { Card } from "../components/ui";

export default function AboutPage() {
  return (
    <Card className="p-6">
      <div className="font-display text-xl font-black text-ink-900">What This UI Does (Now)</div>
      <div className="mt-2 text-sm text-ink-700">
        This dashboard is wired to the current backend features (Milestone 3): upload, job status, list chunks, and
        keyword search over OpenSearch.
      </div>
      <div className="mt-4 text-sm text-ink-800">
        If you upload a scanned PDF, the worker will likely mark the job as <code>needs_ocr</code>. OCR comes in
        Milestone 4.
      </div>
    </Card>
  );
}

