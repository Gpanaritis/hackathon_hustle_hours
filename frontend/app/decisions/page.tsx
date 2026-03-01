"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listDecisions, deleteDecision, DecisionListItem } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  extracted: "bg-green-100 text-green-800",
  pending: "bg-yellow-100 text-yellow-800",
  failed: "bg-red-100 text-red-800",
};

export default function DecisionsPage() {
  const [decisions, setDecisions] = useState<DecisionListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [court, setCourt] = useState("");
  const [judge, setJudge] = useState("");
  const [caseType, setCaseType] = useState("");
  const [outcome, setOutcome] = useState("");
  const [plaintiff, setPlaintiff] = useState("");
  const [defendant, setDefendant] = useState("");

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (court) params.court = court;
      if (judge) params.judge = judge;
      if (caseType) params.case_type = caseType;
      if (outcome) params.outcome = outcome;
      if (plaintiff) params.plaintiff = plaintiff;
      if (defendant) params.defendant = defendant;
      const data = await listDecisions(params);
      setDecisions(data);
    } catch {
      setError("Failed to load decisions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  function handleFilter(e: React.FormEvent) {
    e.preventDefault();
    load();
  }

  async function handleDelete(id: string, label: string) {
    if (!confirm(`Delete "${label}"? This cannot be undone.`)) return;
    try {
      await deleteDecision(id);
      setDecisions((prev) => prev.filter((d) => d.id !== id));
    } catch {
      alert("Failed to delete decision.");
    }
  }

  function resetFilters() {
    setCourt("");
    setJudge("");
    setCaseType("");
    setOutcome("");
    setPlaintiff("");
    setDefendant("");
    setTimeout(load, 0);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Court Decisions</h1>
        <Link
          href="/decisions/upload"
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
        >
          Upload Decision
        </Link>
      </div>

      {/* Filters */}
      <form onSubmit={handleFilter} className="bg-white border border-gray-200 rounded p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Court</label>
            <input
              type="text"
              value={court}
              onChange={(e) => setCourt(e.target.value)}
              placeholder="Search court..."
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-44"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Judge</label>
            <input
              type="text"
              value={judge}
              onChange={(e) => setJudge(e.target.value)}
              placeholder="Search judge..."
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-44"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Case Type</label>
            <input
              type="text"
              value={caseType}
              onChange={(e) => setCaseType(e.target.value)}
              placeholder="e.g. copyright"
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-36"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Outcome</label>
            <input
              type="text"
              value={outcome}
              onChange={(e) => setOutcome(e.target.value)}
              placeholder="e.g. granted"
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-36"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Plaintiff</label>
            <input
              type="text"
              value={plaintiff}
              onChange={(e) => setPlaintiff(e.target.value)}
              placeholder="Search plaintiff..."
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-44"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Defendant</label>
            <input
              type="text"
              value={defendant}
              onChange={(e) => setDefendant(e.target.value)}
              placeholder="Search defendant..."
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-44"
            />
          </div>
          <div className="flex gap-2">
            <button
              type="submit"
              className="bg-gray-900 text-white px-4 py-1.5 rounded text-sm hover:bg-gray-700"
            >
              Apply
            </button>
            <button
              type="button"
              onClick={resetFilters}
              className="bg-white text-gray-600 px-4 py-1.5 rounded text-sm border border-gray-300 hover:bg-gray-50"
            >
              Reset
            </button>
          </div>
        </div>
      </form>

      {/* Table */}
      {loading ? (
        <p className="text-gray-500 text-sm">Loading...</p>
      ) : error ? (
        <p className="text-red-600 text-sm">{error}</p>
      ) : decisions.length === 0 ? (
        <p className="text-gray-500 text-sm">No decisions found.</p>
      ) : (
        <div className="overflow-x-auto bg-white border border-gray-200 rounded">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Case No.</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Court</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Judge</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Plaintiff</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Defendant</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Date</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Outcome</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {decisions.map((d) => (
                <tr key={d.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/decisions/${d.id}`}
                      className="text-blue-600 hover:underline font-medium"
                    >
                      {d.case_number ?? d.source_filename ?? d.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-700 max-w-xs truncate">{d.court ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{d.judge ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{d.plaintiff ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600 max-w-xs truncate">{d.defendant ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{d.decision_date ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{d.outcome ?? "—"}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                        STATUS_COLORS[d.processing_status] ?? "bg-gray-100 text-gray-700"
                      }`}
                    >
                      {d.processing_status}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => handleDelete(d.id, d.case_number ?? d.source_filename ?? d.id.slice(0, 8))}
                      className="text-gray-400 hover:text-red-600 text-xs"
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
