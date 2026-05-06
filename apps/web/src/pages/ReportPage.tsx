import React, { useState } from "react";
import { generateReport } from "../lib/api";
import type { SearchHit, ReportResponse } from "../lib/types";
import { FileText, Loader2, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const OPENROUTER_MODELS = [
  "google/gemma-4-26b-a4b-it:free",
  "google/gemma-3-4b-it:free",
  "google/gemini-2.5-flash",
  "openrouter/free",
];

const GEMINI_MODELS = [
  "gemini-2.5-flash",
  "gemini-2.5-pro",
];

export default function ReportPage() {
  const [query, setQuery] = useState("");
  const [llmProvider, setLlmProvider] = useState<"openrouter" | "gemini">("openrouter");
  const [llmModel, setLlmModel] = useState<string>(OPENROUTER_MODELS[0]);
  const [isLoading, setIsLoading] = useState(false);
  const [report, setReport] = useState<string | null>(null);
  const [sources, setSources] = useState<SearchHit[]>([]);
  const [modelUsed, setModelUsed] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isLoading) return;

    setIsLoading(true);
    setError(null);
    setReport(null);
    setSources([]);
    setModelUsed(null);

    try {
      const res: ReportResponse = await generateReport({
        query,
        top_k: 25,
        mode: "hybrid",
        llm_provider: llmProvider,
        llm_model: llmModel,
        max_tokens: 4096,
      });
      setReport(res.report);
      setSources(res.sources);
      setModelUsed(
        (res.provider_used ? `${res.provider_used} / ` : `${llmProvider} / `) + (res.model_used ?? llmModel)
      );
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed to generate report.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col gap-6 max-w-6xl mx-auto">
      <header className="mb-2">
        <h1 className="flex items-center gap-2 text-2xl font-black text-ink-900 border-b pb-4">
          <FileText className="text-primary-500" /> Legal Report Generation
        </h1>
        <p className="mt-2 text-ink-600">
          Enter a high-level research topic or legal query. The system will retrieve relevant chunks and compile an extensive Markdown document.
        </p>
      </header>
      
      <form onSubmit={handleGenerate} className="flex flex-col gap-4 bg-white/70 backdrop-blur-sm p-6 rounded-xl shadow-md ring-1 ring-black/5">
        <div className="flex flex-col gap-2">
          <label htmlFor="query" className="font-semibold text-ink-900">Research Topic</label>
          <textarea
            id="query"
            rows={3}
            className="w-full rounded-lg border-0 bg-paper py-3 px-4 text-ink-900 shadow-inner ring-1 ring-inset ring-black/5 placeholder:text-ink-400 focus:ring-2 focus:ring-inset focus:ring-ink-900 transition-all resize-y"
            placeholder="e.g. Generate a report detailing the termination clauses and notice periods standard within IT employment..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            disabled={isLoading}
          />
        </div>
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
          <div className="flex flex-col gap-2">
            <label className="font-semibold text-ink-900">LLM Provider</label>
            <select
              value={llmProvider}
              onChange={(e) => {
                const next = e.target.value as "openrouter" | "gemini";
                setLlmProvider(next);
                setLlmModel(next === "gemini" ? GEMINI_MODELS[0] : OPENROUTER_MODELS[0]);
              }}
              className="w-full rounded-lg border-0 bg-paper py-2 px-3 text-ink-900 shadow-inner ring-1 ring-inset ring-black/5"
            >
              <option value="openrouter">OpenRouter</option>
              <option value="gemini">Gemini API</option>
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <label className="font-semibold text-ink-900">LLM Model</label>
            <select
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
              className="w-full rounded-lg border-0 bg-paper py-2 px-3 text-ink-900 shadow-inner ring-1 ring-inset ring-black/5"
            >
              {(llmProvider === "gemini" ? GEMINI_MODELS : OPENROUTER_MODELS).map((m) => (
                <option key={m} value={m}>{m}</option>
              ))}
            </select>
          </div>
        </div>
        
        <button
          type="submit"
          disabled={isLoading || !query.trim()}
          className="self-start flex items-center justify-center gap-2 rounded-lg bg-ink-900 px-6 py-2.5 text-sm font-semibold text-white shadow-lg transition-transform active:scale-95 disabled:opacity-50 disabled:active:scale-100"
        >
          {isLoading ? <Loader2 size={18} className="animate-spin" /> : <Sparkles size={18} />}
          {isLoading ? "Generating Report..." : "Generate AI Report"}
        </button>
      </form>

      {error && (
        <div className="rounded-lg bg-red-50 p-4 text-red-800 ring-1 ring-red-200 shadow-sm border border-red-100">
          <span className="font-semibold">Error:</span> {error}
        </div>
      )}

      {report && (
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6 items-start mt-4">
          <article className="prose prose-ink prose-lg max-w-none bg-white p-8 sm:p-12 rounded-xl shadow-card ring-1 ring-black/5">
            {modelUsed && (
              <p className="not-prose mb-4 text-xs text-ink-500">
                Model used: <span className="font-mono">{modelUsed}</span>
              </p>
            )}
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report}
            </ReactMarkdown>
          </article>
          
          <aside className="sticky top-6 rounded-xl bg-paper p-5 ring-1 ring-black/5 shadow-sm">
            <h3 className="font-bold text-ink-900 mb-3 flex items-center gap-2 border-b pb-3">
               Sources ({sources.length})
            </h3>
            {sources.length === 0 ? (
              <p className="text-sm text-ink-500">No sources were retrieved.</p>
            ) : (
              <ul className="flex flex-col gap-3 max-h-[70vh] overflow-y-auto pr-2 pb-2">
                {sources.map((src, i) => (
                  <li key={i} className="flex flex-col gap-1.5 p-3 bg-white rounded-md shadow-sm text-xs border border-black/5">
                    <span className="font-semibold text-ink-900 leading-snug break-words" title={src.document_title || ""}>
                      {src.document_title || "Unknown Document"}
                    </span>
                    <span className="text-ink-500 font-mono text-[10px] bg-black/5 px-2 py-0.5 rounded-sm self-start">ID: {src.chunk_id.split("-")[0]}</span>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      )}
    </div>
  );
}
