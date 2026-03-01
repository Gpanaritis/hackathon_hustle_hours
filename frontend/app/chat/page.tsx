"use client";

import { useState, useRef, useEffect } from "react";
import { chat, findByCategories, findBySimilarity, SummaryMatchResult } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Message {
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  results?: Record<string, unknown>[] | null;
}

type Tab = "query" | "categories" | "similarity";

// ── Constants ─────────────────────────────────────────────────────────────────

const SUGGESTIONS = [
  "Show all decisions from this year",
  "List decisions where the plaintiff won",
  "Which cases had a monetary award above 10000?",
  "Show decisions by judge",
  "List all legal references used across decisions",
];

const TABS: { id: Tab; label: string; description: string }[] = [
  { id: "query", label: "Query", description: "Ask anything in natural language — get SQL results" },
  { id: "categories", label: "Find by Categories", description: "Describe your case and find decisions with the same legal taxonomy" },
  { id: "similarity", label: "Find by Similarity", description: "Describe your case and find semantically similar decisions" },
];

// ── Sub-components ────────────────────────────────────────────────────────────

function MatchCard({ match, mode }: { match: SummaryMatchResult; mode: "categories" | "similarity" }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 text-sm space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div className="font-medium text-gray-900 truncate">
          {match.source_filename ?? match.case_number ?? match.id}
        </div>
        {mode === "similarity" && match.similarity != null && (
          <span
            className={`shrink-0 text-xs font-semibold px-2 py-0.5 rounded-full ${
              match.similarity >= 80
                ? "bg-green-100 text-green-700"
                : match.similarity >= 50
                ? "bg-yellow-100 text-yellow-700"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {match.similarity}%
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-gray-600">
        {match.court && <span><span className="text-gray-400">Court:</span> {match.court}</span>}
        {match.case_number && <span><span className="text-gray-400">Case:</span> {match.case_number}</span>}
        {match.case_type && <span><span className="text-gray-400">Type:</span> {match.case_type}</span>}
        {match.outcome && <span><span className="text-gray-400">Outcome:</span> {match.outcome}</span>}
        {match.plaintiff && <span><span className="text-gray-400">Plaintiff:</span> {match.plaintiff}</span>}
        {match.defendant && <span><span className="text-gray-400">Defendant:</span> {match.defendant}</span>}
      </div>

      {mode === "categories" && match.matched_categories && match.matched_categories.length > 0 && (
        <div className="flex flex-wrap gap-1 pt-1">
          {match.matched_categories.map((cat) => (
            <span key={cat} className="bg-blue-50 border border-blue-200 text-blue-700 text-xs px-2 py-0.5 rounded-full">
              {cat}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function SummarySearchPanel({ mode }: { mode: "categories" | "similarity" }) {
  const [summary, setSummary] = useState("");
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<SummaryMatchResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function search() {
    if (!summary.trim() || loading) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data =
        mode === "categories"
          ? await findByCategories(summary)
          : await findBySimilarity(summary);
      if (mode === "categories") {
        data.sort((a, b) => (b.matched_categories?.length ?? 0) - (a.matched_categories?.length ?? 0));
      }
      setResults(data);
    } catch {
      setError("Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      search();
    }
  }

  const placeholder =
    mode === "categories"
      ? "Describe the legal situation of your case — the AI will classify it and find decisions with matching legal categories..."
      : "Describe the facts and context of your case — the AI will embed it and find the most semantically similar decisions...";

  return (
    <div className="space-y-4">
      <div className="space-y-2">
        <textarea
          value={summary}
          onChange={(e) => setSummary(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={placeholder}
          rows={5}
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <div className="flex items-center justify-between">
          <p className="text-xs text-gray-400">Ctrl+Enter to search</p>
          <button
            onClick={search}
            disabled={!summary.trim() || loading}
            className="bg-blue-600 text-white px-5 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      {results !== null && (
        <div className="space-y-2">
          {results.length === 0 ? (
            <p className="text-sm text-gray-500">No matching decisions found.</p>
          ) : (
            <>
              <p className="text-xs text-gray-500">{results.length} result{results.length !== 1 ? "s" : ""} found</p>
              <div className="space-y-2">
                {results.map((r) => (
                  <MatchCard key={r.id} match={r} mode={mode} />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function ChatPage() {
  const [activeTab, setActiveTab] = useState<Tab>("query");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    if (!text.trim() || loading) return;
    const userMsg: Message = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const history = messages.map((m) => ({ role: m.role, content: m.content }));
      const res = await chat(text, history);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: res.answer, sql: res.sql, results: res.results },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Something went wrong. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send(input);
    }
  }

  return (
    <div className="max-w-3xl flex flex-col" style={{ minHeight: "calc(100vh - 10rem)" }}>
      <h1 className="text-2xl font-semibold mb-4">Chat with Decisions</h1>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 p-1 rounded-lg">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-3 py-2 rounded-md text-sm font-medium transition-colors ${
              activeTab === tab.id
                ? "bg-white text-gray-900 shadow-sm"
                : "text-gray-600 hover:text-gray-900"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab description */}
      <p className="text-xs text-gray-500 mb-4">
        {TABS.find((t) => t.id === activeTab)?.description}
      </p>

      {/* Query tab */}
      {activeTab === "query" && (
        <div className="flex flex-col flex-1">
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {messages.length === 0 && (
              <div>
                <p className="text-gray-500 text-sm mb-4">
                  Ask anything about your court decisions. Try one of these:
                </p>
                <div className="flex flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => send(s)}
                      className="bg-white border border-gray-200 text-gray-700 px-3 py-1.5 rounded text-sm hover:bg-gray-50"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((m, i) => (
              <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-xl rounded-lg px-4 py-3 text-sm ${
                    m.role === "user"
                      ? "bg-blue-600 text-white"
                      : "bg-white border border-gray-200 text-gray-900"
                  }`}
                >
                  <p className="leading-relaxed whitespace-pre-wrap">{m.content}</p>

                  {m.sql && (
                    <details className="mt-2">
                      <summary className="text-xs text-gray-500 cursor-pointer">View SQL</summary>
                      <pre className="mt-1 text-xs bg-gray-50 border border-gray-200 rounded p-2 overflow-x-auto whitespace-pre-wrap font-mono">
                        {m.sql}
                      </pre>
                    </details>
                  )}

                  {m.results && m.results.length > 0 && (
                    <div className="mt-3 overflow-x-auto">
                      <table className="text-xs border-collapse w-full">
                        <thead>
                          <tr className="bg-gray-50">
                            {Object.keys(m.results[0]).map((col) => (
                              <th key={col} className="border border-gray-200 px-2 py-1 text-left font-medium text-gray-600">
                                {col}
                              </th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {m.results.slice(0, 50).map((row, ri) => (
                            <tr key={ri} className="even:bg-gray-50">
                              {Object.values(row).map((val, vi) => (
                                <td key={vi} className="border border-gray-200 px-2 py-1 text-gray-700">
                                  {val === null ? "—" : String(val)}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {m.results.length > 50 && (
                        <p className="text-xs text-gray-500 mt-1">Showing 50 of {m.results.length} rows.</p>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 text-sm text-gray-500">
                  Thinking...
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          <div className="flex gap-2">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Ask about your court decisions... (Enter to send)"
              rows={2}
              className="flex-1 border border-gray-300 rounded px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <button
              onClick={() => send(input)}
              disabled={!input.trim() || loading}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed self-end"
            >
              Send
            </button>
          </div>
        </div>
      )}

      {/* Find by categories tab */}
      {activeTab === "categories" && <SummarySearchPanel mode="categories" />}

      {/* Find by similarity tab */}
      {activeTab === "similarity" && <SummarySearchPanel mode="similarity" />}
    </div>
  );
}
