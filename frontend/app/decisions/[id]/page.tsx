"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getDecision,
  getSimilarDecisions,
  DecisionDetail,
  SimilarDecision,
} from "@/lib/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

type Tab = "metadata" | "arguments" | "legal_refs" | "summary" | "full_text";

export default function DecisionDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [decision, setDecision] = useState<DecisionDetail | null>(null);
  const [similar, setSimilar] = useState<SimilarDecision[] | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("metadata");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDecision(id)
      .then(setDecision)
      .catch(() => setError("Decision not found."))
      .finally(() => setLoading(false));
  }, [id]);

  function loadSimilar() {
    getSimilarDecisions(id)
      .then(setSimilar)
      .catch(() => setSimilar([]));
  }

  if (loading) return <p className="text-gray-500 text-sm">Loading...</p>;
  if (error || !decision) return <p className="text-red-600 text-sm">{error}</p>;

  const tabs: { key: Tab; label: string }[] = [
    { key: "metadata", label: "Metadata" },
    { key: "arguments", label: `Arguments (${decision.arguments.length})` + (decision.arguments.length ? ` · ${decision.arguments.filter(a => a.side === "plaintiff").length}P / ${decision.arguments.filter(a => a.side === "defendant").length}D` : "") },
    { key: "legal_refs", label: `Legal Refs (${decision.legal_refs.length})` },
    { key: "summary", label: "Summary" },
    { key: "full_text", label: "Full Text" },
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link href="/decisions" className="text-sm text-blue-600 hover:underline">
            ← Back to decisions
          </Link>
          <h1 className="text-2xl font-semibold mt-1">
            {decision.case_number ?? `Decision ${decision.id.slice(0, 8)}`}
          </h1>
          <p className="text-gray-500 text-sm mt-0.5">{decision.source_filename}</p>
        </div>
        <div className="flex gap-2">
          <a
            href={`${API_BASE}/decisions/${id}/download`}
            target="_blank"
            rel="noopener noreferrer"
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded text-sm hover:bg-gray-50"
          >
            Download PDF
          </a>
          <button
            onClick={loadSimilar}
            className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
          >
            Find Similar
          </button>
        </div>
      </div>

      {/* Similarity results */}
      {similar !== null && (
        <div className="bg-blue-50 border border-blue-200 rounded p-4 mb-6">
          <h3 className="font-medium text-sm mb-2">Similar Decisions</h3>
          {similar.length === 0 ? (
            <p className="text-sm text-gray-500">No similar decisions found.</p>
          ) : (
            <ul className="space-y-1">
              {similar.map((s) => (
                <li key={s.id} className="flex items-center justify-between text-sm">
                  <Link href={`/decisions/${s.id}`} className="text-blue-700 hover:underline">
                    {s.case_number ?? s.id.slice(0, 8)} — {s.court ?? s.source_filename}
                  </Link>
                  <span className="text-gray-500">{s.similarity}% similar</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Processing error banner */}
      {decision.processing_status === "failed" && decision.extraction_error && (
        <div className="bg-red-50 border border-red-200 rounded p-4 mb-6 text-sm text-red-700">
          <strong>Extraction failed:</strong> {decision.extraction_error}
        </div>
      )}

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="flex gap-0">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                activeTab === t.key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-600 hover:text-gray-900"
              }`}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab content */}
      <div className="bg-white border border-gray-200 rounded p-6">
        {activeTab === "metadata" && (
          <dl className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm">
            <Field label="Case Number" value={decision.case_number} />
            <Field label="Case Type" value={decision.case_type} />
            <Field label="Court" value={decision.court} />
            <Field label="Judge" value={decision.judge} />
            <Field label="Plaintiff" value={decision.plaintiff} />
            <Field label="Defendant" value={decision.defendant} />
            <Field label="Decision Date" value={decision.decision_date} />
            <Field
              label="Monetary Award"
              value={decision.monetary_award !== null ? String(decision.monetary_award) : null}
            />
            <Field label="Appeal Of" value={decision.appeal_of} />
            <Field label="Outcome" value={decision.outcome} />
            <Field label="OCR" value={decision.is_ocr ? "Yes (image PDF)" : "No (text PDF)"} />
            <Field label="Status" value={decision.processing_status} />
            <Field
              label="Uploaded"
              value={decision.created_at ? new Date(decision.created_at).toLocaleString() : null}
            />
          </dl>
        )}

        {activeTab === "arguments" && (
          <div className="space-y-6">
            {decision.arguments.length === 0 ? (
              <p className="text-gray-500 text-sm">No arguments extracted.</p>
            ) : (
              <>
                <ArgumentSection
                  title="Plaintiff Arguments"
                  args={decision.arguments.filter((a) => a.side === "plaintiff")}
                  color="blue"
                />
                <ArgumentSection
                  title="Defendant Arguments"
                  args={decision.arguments.filter((a) => a.side === "defendant")}
                  color="red"
                />
              </>
            )}
          </div>
        )}

        {activeTab === "legal_refs" && (
          <div>
            {decision.legal_refs.length === 0 ? (
              <p className="text-gray-500 text-sm">No legal references extracted.</p>
            ) : (
              <ul className="space-y-2 text-sm">
                {decision.legal_refs.map((ref) => (
                  <li key={ref.id} className="flex items-start gap-2 text-gray-800">
                    <span className="text-gray-400 shrink-0 mt-0.5">•</span>
                    {ref.reference}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        {activeTab === "summary" && (
          <div className="text-sm">
            {decision.summary ? (
              <p className="text-gray-700 leading-relaxed">{decision.summary}</p>
            ) : (
              <p className="text-gray-500">No summary available.</p>
            )}
          </div>
        )}

        {activeTab === "full_text" && (
          <div className="text-sm">
            {decision.full_text ? (
              <pre className="whitespace-pre-wrap text-gray-700 leading-relaxed font-sans bg-gray-50 p-4 rounded border border-gray-200 max-h-[60vh] overflow-y-auto">
                {decision.full_text}
              </pre>
            ) : (
              <p className="text-gray-500">Full text not available.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function ArgumentSection({
  title,
  args,
  color,
}: {
  title: string;
  args: { id: string; argument: string; position: number }[];
  color: "blue" | "red";
}) {
  const border = color === "blue" ? "border-blue-200" : "border-red-200";
  const heading = color === "blue" ? "text-blue-700" : "text-red-700";
  const dot = color === "blue" ? "bg-blue-400" : "bg-red-400";

  return (
    <div className={`border-l-4 ${border} pl-4`}>
      <h4 className={`font-medium text-sm mb-2 ${heading}`}>{title}</h4>
      {args.length === 0 ? (
        <p className="text-gray-400 text-sm">None extracted.</p>
      ) : (
        <ol className="space-y-2 text-sm">
          {args
            .sort((a, b) => a.position - b.position)
            .map((arg) => (
              <li key={arg.id} className="flex gap-2 text-gray-800 leading-relaxed">
                <span className={`w-1.5 h-1.5 rounded-full ${dot} shrink-0 mt-1.5`} />
                {arg.argument}
              </li>
            ))}
        </ol>
      )}
    </div>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value: string | number | boolean | null | undefined;
}) {
  return (
    <div>
      <dt className="text-gray-500 text-xs uppercase tracking-wide">{label}</dt>
      <dd className="mt-0.5 text-gray-900">
        {value !== null && value !== undefined ? String(value) : "—"}
      </dd>
    </div>
  );
}
