import React, { useMemo, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";

import { initOpenSearch, uploadDocument } from "../lib/api";
import type { UploadResponse } from "../lib/types";
import { Badge, Button, Card, Input, Label } from "../components/ui";

const schema = z.object({
  file: z.instanceof(File),
  title: z.string().min(1, "Title is required"),
  jurisdiction: z.string().optional(),
  year: z.preprocess((v) => (v === "" || v == null ? undefined : Number(v)), z.number().int().min(0).max(3000).optional()),
  law_type: z.string().optional()
});

type FormValues = z.infer<typeof schema>;

function statusTone(status: string) {
  if (status === "complete") return "ok";
  if (status === "processing") return "info";
  if (status === "queued") return "neutral";
  if (status === "needs_ocr") return "warn";
  if (status === "failed") return "bad";
  return "neutral";
}

export default function UploadPage() {
  const [last, setLast] = useState<UploadResponse | null>(null);

  const form = useForm<FormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      title: "",
      jurisdiction: "US",
      year: new Date().getFullYear(),
      law_type: "contract"
    }
  });

  const upload = useMutation({
    mutationFn: async (v: FormValues) => {
      const parsed = schema.parse(v);
      return uploadDocument({
        file: parsed.file,
        title: parsed.title,
        jurisdiction: parsed.jurisdiction?.trim() || undefined,
        year: parsed.year,
        law_type: parsed.law_type?.trim() || undefined
      });
    },
    onSuccess: (r) => setLast(r)
  });

  const init = useMutation({
    mutationFn: initOpenSearch
  });

  const err = useMemo(() => {
    const e = upload.error as Error | null;
    return e?.message ?? null;
  }, [upload.error]);

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="font-display text-xl font-black text-ink-900">Upload Document</div>
            <div className="mt-1 text-sm text-ink-700">Upload PDF/DOCX/TXT and provide metadata for filters.</div>
          </div>
          <Button
            type="button"
            variant="ghost"
            onClick={() => init.mutate()}
            disabled={init.isPending}
            title="Creates the OpenSearch chunks index if missing"
          >
            Init OpenSearch
          </Button>
        </div>

        <form
          className="mt-5 grid grid-cols-1 gap-4 md:grid-cols-2"
          onSubmit={form.handleSubmit((v) => upload.mutate(v))}
        >
          <div className="md:col-span-2">
            <Label>File</Label>
            <Input
              type="file"
              accept=".pdf,.docx,.txt,.md"
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) form.setValue("file", f, { shouldValidate: true });
              }}
            />
            <div className="mt-1 text-xs text-ink-600">Tip: use a text-based PDF (scanned PDFs need OCR in M4).</div>
          </div>

          <div className="md:col-span-2">
            <Label>Title</Label>
            <Input placeholder="AIMMUNE 8-K Agreement" {...form.register("title")} />
            {form.formState.errors.title?.message ? (
              <div className="mt-1 text-xs font-semibold text-rose-700">{form.formState.errors.title.message}</div>
            ) : null}
          </div>

          <div>
            <Label>Jurisdiction</Label>
            <Input placeholder="US" {...form.register("jurisdiction")} />
          </div>

          <div>
            <Label>Year</Label>
            <Input type="number" placeholder="2020" {...form.register("year")} />
          </div>

          <div className="md:col-span-2">
            <Label>Law Type</Label>
            <Input placeholder="contract | regulation | case_decision" {...form.register("law_type")} />
            <div className="mt-1 text-xs text-ink-600">
              This value is used for filtering. It must match exactly when you filter later.
            </div>
          </div>

          <div className="md:col-span-2 flex items-center gap-2">
            <Button type="submit" disabled={upload.isPending}>
              {upload.isPending ? "Uploading..." : "Upload + Start Ingestion"}
            </Button>
            {err ? <div className="text-sm font-semibold text-rose-700">{err}</div> : null}
          </div>
        </form>
      </Card>

      {last ? (
        <Card className="p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="font-display text-lg font-black text-ink-900">Last Upload</div>
            <Badge tone={statusTone(last.job.status)}>{last.job.status}</Badge>
          </div>
          <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="rounded-lg bg-paper p-3 ring-1 ring-black/5">
              <div className="text-xs font-bold uppercase tracking-wide text-ink-700">Document ID</div>
              <div className="mt-1 font-mono text-sm text-ink-900">{last.document.id}</div>
            </div>
            <div className="rounded-lg bg-paper p-3 ring-1 ring-black/5">
              <div className="text-xs font-bold uppercase tracking-wide text-ink-700">Job ID</div>
              <div className="mt-1 font-mono text-sm text-ink-900">{last.job.id}</div>
            </div>
          </div>
          <div className="mt-4 text-sm text-ink-700">
            Next: go to <span className="font-semibold">Jobs</span> to poll status, then{" "}
            <span className="font-semibold">Search</span>.
          </div>
        </Card>
      ) : null}
    </div>
  );
}

