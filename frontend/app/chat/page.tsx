"use client";

import { useState, useRef, useEffect } from "react";
import { chat } from "@/lib/api";

interface Message {
  role: "user" | "assistant";
  content: string;
  sql?: string | null;
  results?: Record<string, unknown>[] | null;
}

const SUGGESTIONS = [
  "Show contracts expiring this year",
  "List contracts with missing signatures",
  "Show all contracts from Bulgaria",
  "Which contracts have a penalty above 10000?",
  "List all musical works across all contracts",
];

export default function ChatPage() {
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
        {
          role: "assistant",
          content: res.answer,
          sql: res.sql,
          results: res.results,
        },
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
    <div className="max-w-3xl flex flex-col h-[calc(100vh-10rem)]">
      <h1 className="text-2xl font-semibold mb-4">Chat with Contracts</h1>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 mb-4">
        {messages.length === 0 && (
          <div>
            <p className="text-gray-500 text-sm mb-4">
              Ask anything about your contracts. Try one of these:
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

      {/* Input */}
      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask about your contracts... (Enter to send)"
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
  );
}
