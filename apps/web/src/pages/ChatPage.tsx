import React, { useState, useRef, useEffect } from "react";
import { MessageCircle, Send, ChevronDown, FileText, X } from "lucide-react";
import { chatPublic, chatLawyer } from "../lib/api";
import type { ChatMessage, SearchHit, ChatResponse } from "../lib/types";
import clsx from "clsx";
import { renderHighlightedSnippet } from "../lib/snippet";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type EvidenceViewerState = {
  open: boolean;
  documentId: string | null;
  chunks: SearchHit[];
  phrases: string[];
  activeIndex: number;
  navSeq: number;
};

function plainSnippet(snippet: string): string {
  const withoutTags = snippet.replace(/<[^>]+>/g, " ");
  return withoutTags.replace(/\s+/g, " ").trim();
}

function emTerms(snippet: string): string[] {
  const out: string[] = [];
  const re = /<em>(.*?)<\/em>/gi;
  let m: RegExpExecArray | null;
  while ((m = re.exec(snippet)) !== null) {
    const t = (m[1] || "").replace(/\s+/g, " ").trim();
    if (t.length >= 2) out.push(t);
  }
  return Array.from(new Set(out));
}

function normForMatch(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^\p{L}\p{N}\s]/gu, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function sentenceParts(text: string): string[] {
  return text
    .split(/[.!?\n؟]/g)
    .map((s) => s.trim())
    .filter((s) => s.length >= 15);
}

function bestEvidencePhrase(answer: string, snippet: string): string {
  const cleanSnippet = plainSnippet(snippet);
  if (!answer.trim()) return cleanSnippet.slice(0, 140);

  const nSnippet = normForMatch(cleanSnippet);
  const candidates = sentenceParts(answer);

  let best: string | null = null;
  let bestScore = 0;
  for (const c of candidates) {
    const nC = normForMatch(c);
    if (!nC) continue;
    if (nSnippet.includes(nC)) {
      // Exact sentence hit in snippet gets top priority.
      return c.slice(0, 180);
    }
    const words = nC.split(" ").filter((w) => w.length >= 3);
    let overlap = 0;
    for (const w of words) {
      if (nSnippet.includes(w)) overlap += 1;
    }
    const score = overlap * 10 + Math.min(c.length, 120);
    if (overlap >= 3 && score > bestScore) {
      bestScore = score;
      best = c;
    }
  }
  return (best ?? cleanSnippet).slice(0, 180);
}

function buildPdfUrl(docId: string, page: number, searchText: string, seq: number): string {
  // Add a query cache-buster so the iframe always navigates when user switches chunks.
  const base = `/v1/documents/${docId}/file?nav=${seq}`;
  const fragments = [`page=${Math.max(1, page || 1)}`];
  if (searchText) {
    fragments.push(`search=${encodeURIComponent(searchText.slice(0, 120))}`);
  }
  return `${base}#${fragments.join("&")}`;
}

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

export default function ChatPage() {
  const [mode, setMode] = useState<"public" | "lawyer">("public");
  const [llmProvider, setLlmProvider] = useState<"openrouter" | "gemini">("openrouter");
  const [llmModel, setLlmModel] = useState<string>(OPENROUTER_MODELS[0]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [sourcesByMsgIndex, setSourcesByMsgIndex] = useState<Record<number, SearchHit[]>>({});
  const [modelByMsgIndex, setModelByMsgIndex] = useState<Record<number, string>>({});
  const [providerByMsgIndex, setProviderByMsgIndex] = useState<Record<number, string>>({});
  const [viewer, setViewer] = useState<EvidenceViewerState>({
    open: false,
    documentId: null,
    chunks: [],
    phrases: [],
    activeIndex: 0,
    navSeq: 0,
  });
  
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMsg: ChatMessage = { role: "user", content: input };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setIsLoading(true);

    try {
      const apiFn = mode === "public" ? chatPublic : chatLawyer;
      const res: ChatResponse = await apiFn({
        messages: newMessages,
        top_k: 15,
        mode: "hybrid",
        llm_provider: llmProvider,
        llm_model: llmModel,
        max_tokens: 4096,
      });
      
      const assistantMsg: ChatMessage = { role: "assistant", content: res.answer };
      const updatedMsgs = [...newMessages, assistantMsg];
      setMessages(updatedMsgs);
      
      setSourcesByMsgIndex((prev) => ({
        ...prev,
        [updatedMsgs.length - 1]: res.sources,
      }));
      if (res.model_used) {
        setModelByMsgIndex((prev) => ({
          ...prev,
          [updatedMsgs.length - 1]: res.model_used as string,
        }));
      }
      if (res.provider_used) {
        setProviderByMsgIndex((prev) => ({
          ...prev,
          [updatedMsgs.length - 1]: res.provider_used as string,
        }));
      }
    } catch (e) {
      console.error(e);
      setMessages((prev) => [...prev, { role: "assistant", content: "Error: " + (e as Error).message }]);
    } finally {
      setIsLoading(false);
    }
  };

  const openEvidenceViewer = (sources: SearchHit[], answerText: string) => {
    if (!sources.length) return;
    const docId = sources[0].document_id;
    const top2 = sources.filter((s) => s.document_id === docId).slice(0, 2);
    const chosen = top2.length ? top2 : sources.slice(0, 2);
    const phrases = chosen.map((s) => bestEvidencePhrase(answerText, s.snippet));
    setViewer({
      open: true,
      documentId: docId,
      chunks: chosen,
      phrases,
      activeIndex: 0,
      navSeq: 1,
    });
  };

  const openEvidenceViewerAtChunk = (sources: SearchHit[], answerText: string, chunkId: string) => {
    if (!sources.length) return;
    const selected = sources.find((s) => s.chunk_id === chunkId);
    if (!selected) {
      openEvidenceViewer(sources, answerText);
      return;
    }

    const sameDoc = sources.filter((s) => s.document_id === selected.document_id);
    const top2 = sameDoc.slice(0, 2);
    const chosen = top2.some((c) => c.chunk_id === selected.chunk_id)
      ? top2
      : [selected, ...top2].slice(0, 2);
    const phrases = chosen.map((s) => bestEvidencePhrase(answerText, s.snippet));
    const idx = Math.max(
      0,
      chosen.findIndex((c) => c.chunk_id === selected.chunk_id)
    );
    setViewer({
      open: true,
      documentId: selected.document_id,
      chunks: chosen,
      phrases,
      activeIndex: idx,
      navSeq: 1,
    });
  };

  const activeChunk = viewer.chunks[viewer.activeIndex];
  const activePhrase = viewer.phrases[viewer.activeIndex] ?? "";
  const activeEmTerms = activeChunk ? emTerms(activeChunk.snippet) : [];
  // Prefer exact highlighted terms from chunk text for better in-PDF search matching.
  const effectiveSearch =
    activeEmTerms.length >= 2
      ? activeEmTerms.slice(0, 4).join(" ")
      : (activePhrase || (activeChunk ? plainSnippet(activeChunk.snippet) : ""));
  const pdfSrc =
    viewer.open && viewer.documentId && activeChunk
      ? buildPdfUrl(viewer.documentId, activeChunk.page_start ?? 1, effectiveSearch, viewer.navSeq)
      : "";

  return (
    <>
    <div className="flex h-[calc(100vh-8rem)] flex-col rounded-xl bg-white/70 shadow-xl ring-1 ring-black/5 backdrop-blur-md">
      <div className="flex items-center justify-between border-b border-black/5 px-6 py-4">
        <div className="flex items-center gap-2 text-ink-900">
          <MessageCircle className="text-primary-500" />
          <h2 className="text-xl font-bold">RAG Chat</h2>
        </div>
        <div className="flex items-center gap-2 rounded-full bg-paper p-1 ring-1 ring-black/5">
          <button
            onClick={() => setMode("public")}
            className={clsx(
              "rounded-full px-4 py-1.5 text-sm font-semibold transition-all",
              mode === "public" ? "bg-ink-900 text-white shadow-md" : "text-ink-600 hover:text-ink-900 hover:bg-black/5"
            )}
          >
            Public Mode
          </button>
          <button
            onClick={() => setMode("lawyer")}
            className={clsx(
              "rounded-full px-4 py-1.5 text-sm font-semibold transition-all",
              mode === "lawyer" ? "bg-ink-900 text-white shadow-md" : "text-ink-600 hover:text-ink-900 hover:bg-black/5"
            )}
          >
            Lawyer Mode
          </button>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={llmProvider}
            onChange={(e) => {
              const next = e.target.value as "openrouter" | "gemini";
              setLlmProvider(next);
              setLlmModel(next === "gemini" ? GEMINI_MODELS[0] : OPENROUTER_MODELS[0]);
            }}
            className="rounded-lg border border-black/10 bg-white/90 px-2 py-1 text-xs text-ink-800"
          >
            <option value="openrouter">OpenRouter</option>
            <option value="gemini">Gemini API</option>
          </select>
          <select
            value={llmModel}
            onChange={(e) => setLlmModel(e.target.value)}
            className="max-w-[220px] rounded-lg border border-black/10 bg-white/90 px-2 py-1 text-xs text-ink-800"
          >
            {(llmProvider === "gemini" ? GEMINI_MODELS : OPENROUTER_MODELS).map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-6 scroll-smooth">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center text-center text-ink-500">
            <MessageCircle size={48} className="mb-4 text-ink-300 opacity-50" />
            <p className="text-lg">Ask a question about the uploaded legal documents.</p>
            <p className="text-sm">The AI will use hybrid retrieval to anchor its answers.</p>
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            {messages.map((msg, i) => (
              <div key={i} className={clsx("flex max-w-3xl flex-col", msg.role === "user" ? "self-end items-end" : "self-start items-start")}>
                <div
                  className={clsx(
                    "flex flex-col gap-2 rounded-2xl px-5 py-3 shadow-sm",
                    msg.role === "user" ? "bg-ink-900 text-white rounded-br-none" : "bg-white ring-1 ring-black/5 rounded-bl-none text-ink-900 shadow-md"
                  )}
                >
                  {msg.role === "assistant" ? (
                    <div className="leading-relaxed text-sm">
                      <ReactMarkdown
                        remarkPlugins={[remarkGfm]}
                        components={{
                          a: ({ href, children }) => {
                            if (href && href.startsWith("chunk://")) {
                              const cid = href.replace("chunk://", "");
                              return (
                                <button
                                  type="button"
                                  onClick={() =>
                                    openEvidenceViewerAtChunk(
                                      sourcesByMsgIndex[i] || [],
                                      msg.content,
                                      cid
                                    )
                                  }
                                  className="rounded bg-accent-100 px-1 py-0.5 font-mono text-xs text-ink-900 underline decoration-dotted"
                                >
                                  {children}
                                </button>
                              );
                            }
                            return (
                              <a href={href} target="_blank" rel="noreferrer" className="underline">
                                {children}
                              </a>
                            );
                          },
                        }}
                      >
                        {msg.content}
                      </ReactMarkdown>
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                  )}
                </div>
                {msg.role === "assistant" && sourcesByMsgIndex[i] && sourcesByMsgIndex[i].length > 0 && (
                  <div className="mt-2 w-full pl-2">
                    <button
                      type="button"
                      onClick={() => openEvidenceViewer(sourcesByMsgIndex[i], msg.content)}
                      className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-ink-900 px-3 py-1.5 text-xs font-semibold text-white shadow-sm hover:opacity-90"
                    >
                      <FileText size={14} />
                      Open PDF Evidence
                    </button>
                    <details className="group">
                      <summary className="flex cursor-pointer items-center gap-1 text-xs font-semibold text-ink-500 hover:text-ink-700">
                        <ChevronDown size={14} className="transition-transform group-open:-rotate-180" />
                        <span>{sourcesByMsgIndex[i].length} sources retrieved</span>
                      </summary>
                      <div className="mt-3 flex flex-col gap-3 border-l-2 border-ink-200 pl-4 py-1">
                        {sourcesByMsgIndex[i].map((src, j) => (
                          <div key={j} className="text-sm text-ink-700 bg-white/60 p-3 rounded-md ring-1 ring-black/5 shadow-sm">
                            <div className="flex justify-between items-center mb-1">
                              <span className="font-semibold text-ink-900">{src.document_title || "Unknown Document"}</span>
                              <span className="text-[10px] bg-black/5 px-2 py-0.5 rounded-full font-mono">{src.chunk_id.split("-")[0]}</span>
                            </div>
                            <p className="text-xs text-ink-600 italic leading-relaxed line-clamp-3">
                              {renderHighlightedSnippet(src.snippet)}
                            </p>
                          </div>
                        ))}
                      </div>
                    </details>
                  </div>
                )}
                {msg.role === "assistant" && modelByMsgIndex[i] && (
                  <div className="mt-1 text-xs text-ink-500">
                    Model used:{" "}
                    <span className="font-mono">
                      {(providerByMsgIndex[i] || llmProvider) + " / " + modelByMsgIndex[i]}
                    </span>
                  </div>
                )}
              </div>
            ))}
            {isLoading && (
              <div className="self-start">
                <div className="flex items-center gap-2 rounded-2xl rounded-bl-none bg-white px-5 py-4 text-ink-400 shadow-sm ring-1 ring-black/5">
                  <span className="flex gap-1.5">
                    <span className="h-2 w-2 animate-bounce rounded-full bg-ink-300 [animation-delay:-0.3s]"></span>
                    <span className="h-2 w-2 animate-bounce rounded-full bg-ink-300 [animation-delay:-0.15s]"></span>
                    <span className="h-2 w-2 animate-bounce rounded-full bg-ink-300"></span>
                  </span>
                </div>
              </div>
            )}
            <div ref={bottomRef} className="h-1" />
          </div>
        )}
      </div>

      <div className="border-t border-black/5 bg-white p-4 rounded-b-xl">
        <form onSubmit={handleSubmit} className="relative flex max-w-4xl mx-auto items-center">
          <input
            autoFocus
            type="text"
            className="w-full rounded-full border-0 bg-paper py-3.5 pl-6 pr-14 text-ink-900 shadow-inner ring-1 ring-inset ring-black/5 placeholder:text-ink-400 focus:ring-2 focus:ring-inset focus:ring-ink-900 focus:bg-white transition-all"
            placeholder={`Type your legal question (${mode} mode)...`}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="absolute right-1.5 flex h-10 w-10 items-center justify-center rounded-full bg-ink-900 text-white transition-transform active:scale-95 disabled:opacity-30 disabled:active:scale-100 flex-shrink-0"
          >
            <Send size={16} className="-ml-0.5" />
          </button>
        </form>
      </div>
    </div>
    {viewer.open && viewer.documentId && (
      <div className="fixed inset-0 z-50 bg-black/45 backdrop-blur-[2px]">
        <div className="absolute inset-4 grid grid-cols-1 gap-4 rounded-2xl bg-white p-4 shadow-2xl ring-1 ring-black/10 lg:grid-cols-[1fr_360px]">
          <div className="flex min-h-0 flex-col overflow-hidden rounded-xl ring-1 ring-black/10">
            <div className="flex items-center justify-between border-b border-black/10 bg-paper px-4 py-2">
              <p className="text-sm font-semibold text-ink-900">PDF Evidence Viewer</p>
              <button
                type="button"
                onClick={() => setViewer((v) => ({ ...v, open: false }))}
                className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-ink-600 hover:bg-black/5"
              >
                <X size={14} />
                Close
              </button>
            </div>
            {pdfSrc ? (
              <iframe
                title="pdf-evidence"
                key={pdfSrc}
                src={pdfSrc}
                className="h-full w-full bg-white"
              />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-ink-500">
                Unable to load PDF preview.
              </div>
            )}
          </div>

          <aside className="min-h-0 overflow-auto rounded-xl bg-paper p-3 ring-1 ring-black/10">
            <h3 className="mb-3 text-sm font-bold text-ink-900">Highlighted Chunks (Top 2)</h3>
            <div className="flex flex-col gap-2">
              {viewer.chunks.map((chunk, idx) => {
                const active = idx === viewer.activeIndex;
                return (
                  <button
                    type="button"
                    key={`${chunk.chunk_id}-${idx}`}
                    onClick={() =>
                      setViewer((v) => ({
                        ...v,
                        activeIndex: idx,
                        navSeq: v.navSeq + 1,
                      }))
                    }
                    className={clsx(
                      "w-full rounded-lg p-3 text-left shadow-sm ring-1 transition",
                      active
                        ? "bg-white ring-primary-400"
                        : "bg-white/70 ring-black/5 hover:bg-white hover:ring-black/10"
                    )}
                  >
                    <div className="mb-1 flex items-center justify-between">
                      <span className="text-xs font-semibold text-ink-900">
                        Chunk {idx + 1}
                      </span>
                      <span className="rounded-full bg-black/5 px-2 py-0.5 font-mono text-[10px] text-ink-600">
                        p.{chunk.page_start ?? "?"}
                        {chunk.page_end && chunk.page_end !== chunk.page_start ? `-${chunk.page_end}` : ""}
                      </span>
                    </div>
                    {chunk.section_path && chunk.section_path.length > 0 && (
                      <div className="mb-1 text-[11px] text-ink-600">
                        Section:{" "}
                        <span className="font-mono text-[10px]">
                          {chunk.section_path.join(" > ")}
                        </span>
                      </div>
                    )}
                    <div className="line-clamp-4 text-xs leading-relaxed text-ink-700">
                      {renderHighlightedSnippet(chunk.snippet)}
                    </div>
                    {viewer.phrases[idx] && (
                      <div className="mt-2 rounded bg-accent-100 px-2 py-1 text-[11px] text-ink-700">
                        Highlight phrase: "{viewer.phrases[idx]}"
                      </div>
                    )}
                  </button>
                );
              })}
            </div>
            <p className="mt-3 text-[11px] text-ink-500">
              The viewer jumps to the chunk page and uses PDF search to highlight matching text.
            </p>
          </aside>
        </div>
      </div>
    )}
    </>
  );
}
