"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import {
  getContract,
  getSimilarContracts,
  ContractDetail,
  SimilarContract,
} from "@/lib/api";

type Tab = "metadata" | "parties" | "works" | "terms" | "ai";

export default function ContractDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [contract, setContract] = useState<ContractDetail | null>(null);
  const [similar, setSimilar] = useState<SimilarContract[] | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("metadata");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getContract(Number(id))
      .then(setContract)
      .catch(() => setError("Contract not found."))
      .finally(() => setLoading(false));
  }, [id]);

  function loadSimilar() {
    getSimilarContracts(Number(id))
      .then(setSimilar)
      .catch(() => setSimilar([]));
  }

  if (loading) return <p className="text-gray-500 text-sm">Loading...</p>;
  if (error || !contract) return <p className="text-red-600 text-sm">{error}</p>;

  const tabs: { key: Tab; label: string }[] = [
    { key: "metadata", label: "Metadata" },
    { key: "parties", label: `Parties (${contract.parties.length})` },
    { key: "works", label: `Musical Works (${contract.works.length})` },
    { key: "terms", label: "Terms" },
    { key: "ai", label: "AI" },
  ];

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link href="/contracts" className="text-sm text-blue-600 hover:underline">
            ← Back to contracts
          </Link>
          <h1 className="text-2xl font-semibold mt-1">
            {contract.internal_ref_no ?? `Contract #${contract.contract_id}`}
          </h1>
          <p className="text-gray-500 text-sm mt-0.5">{contract.file_name}</p>
        </div>
        <div className="flex gap-2">
          <a
            href={`http://localhost:8000/api/v1/contracts/${id}/download`}
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
          <h3 className="font-medium text-sm mb-2">Similar Contracts</h3>
          {similar.length === 0 ? (
            <p className="text-sm text-gray-500">No similar contracts found.</p>
          ) : (
            <ul className="space-y-1">
              {similar.map((s) => (
                <li key={s.contract_id} className="flex items-center justify-between text-sm">
                  <Link href={`/contracts/${s.contract_id}`} className="text-blue-700 hover:underline">
                    {s.internal_ref_no ?? `#${s.contract_id}`} — {s.file_name}
                  </Link>
                  <span className="text-gray-500">{s.similarity}% similar</span>
                </li>
              ))}
            </ul>
          )}
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
            <Field label="Internal Ref No." value={contract.internal_ref_no} />
            <Field label="Status" value={contract.status} />
            <Field label="Country" value={contract.country_code} />
            <Field label="Jurisdiction" value={contract.jurisdiction_state_city} />
            <Field label="Language" value={contract.language} />
            <Field label="Execution Date" value={contract.execution_date} />
            <Field label="Term (years)" value={contract.term_years} />
            <Field label="Expiry Date" value={contract.expiry_date} />
            <Field label="Exclusive" value={contract.is_exclusive === null ? null : contract.is_exclusive ? "Yes" : "No"} />
            <Field label="Uploaded" value={contract.upload_date ? new Date(contract.upload_date).toLocaleString() : null} />
          </dl>
        )}

        {activeTab === "parties" && (
          <div>
            {contract.parties.length === 0 ? (
              <p className="text-gray-500 text-sm">No parties extracted.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-gray-200">
                    <tr>
                      <th className="text-left py-2 pr-4 font-medium text-gray-600">Role</th>
                      <th className="text-left py-2 pr-4 font-medium text-gray-600">Legal Name</th>
                      <th className="text-left py-2 pr-4 font-medium text-gray-600">Representative</th>
                      <th className="text-left py-2 pr-4 font-medium text-gray-600">ID</th>
                      <th className="text-left py-2 pr-4 font-medium text-gray-600">Signing</th>
                      <th className="text-left py-2 font-medium text-gray-600">Address</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {contract.parties.map((p) => (
                      <tr key={p.party_id}>
                        <td className="py-2 pr-4">{p.role ?? "—"}</td>
                        <td className="py-2 pr-4">{p.legal_name ?? "—"}</td>
                        <td className="py-2 pr-4">{p.representative_name ?? "—"}</td>
                        <td className="py-2 pr-4">{p.id_type ? `${p.id_type}: ${p.id_value}` : "—"}</td>
                        <td className="py-2 pr-4"><SigningBadge status={p.signing_status} /></td>
                        <td className="py-2 text-gray-500">{p.address ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === "works" && (
          <div>
            {contract.works.length === 0 ? (
              <p className="text-gray-500 text-sm">No musical works extracted.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="border-b border-gray-200">
                    <tr>
                      <th className="text-left py-2 pr-4 font-medium text-gray-600">Title</th>
                      <th className="text-left py-2 pr-4 font-medium text-gray-600">Artist</th>
                      <th className="text-left py-2 pr-4 font-medium text-gray-600">Lyricist</th>
                      <th className="text-left py-2 pr-4 font-medium text-gray-600">ISRC</th>
                      <th className="text-left py-2 font-medium text-gray-600">Society</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {contract.works.map((w) => (
                      <tr key={w.work_id}>
                        <td className="py-2 pr-4 font-medium">{w.title ?? "—"}</td>
                        <td className="py-2 pr-4">{w.artist_performer ?? "—"}</td>
                        <td className="py-2 pr-4">{w.lyricist ?? "—"}</td>
                        <td className="py-2 pr-4 font-mono text-xs">{w.isrc_code ?? "—"}</td>
                        <td className="py-2">{w.collection_society ?? "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === "terms" && (
          <div>
            {!contract.terms ? (
              <p className="text-gray-500 text-sm">No terms extracted.</p>
            ) : (
              <dl className="grid grid-cols-2 gap-x-8 gap-y-4 text-sm">
                <Field
                  label="Remuneration"
                  value={
                    contract.terms.remuneration_amount !== null
                      ? `${contract.terms.remuneration_amount} ${contract.terms.currency ?? ""}`
                      : null
                  }
                />
                <Field label="Currency" value={contract.terms.currency} />
                <Field
                  label="Min. Penalty"
                  value={
                    contract.terms.min_penalty_liquidated_damages !== null
                      ? `${contract.terms.min_penalty_liquidated_damages} ${contract.terms.currency ?? ""}`
                      : null
                  }
                />
                <Field label="Delivery Deadline" value={contract.terms.delivery_deadline_days !== null ? `${contract.terms.delivery_deadline_days} days` : null} />
                <Field label="Registration Deadline" value={contract.terms.registration_deadline_days !== null ? `${contract.terms.registration_deadline_days} days` : null} />
                <Field label="Streaming Requirement" value={contract.terms.streaming_requirement_days !== null ? `${contract.terms.streaming_requirement_days} days` : null} />
              </dl>
            )}
          </div>
        )}

        {activeTab === "ai" && (
          <div className="space-y-6 text-sm">
            <div>
              <h3 className="font-medium mb-2">Summary</h3>
              <p className="text-gray-700 leading-relaxed">
                {contract.intelligence?.summary_short ?? "No summary available."}
              </p>
            </div>
            {contract.intelligence?.translated_text_en && (
              <div>
                <h3 className="font-medium mb-2">English Translation</h3>
                <pre className="whitespace-pre-wrap text-gray-700 leading-relaxed font-sans bg-gray-50 p-4 rounded border border-gray-200 max-h-96 overflow-y-auto">
                  {contract.intelligence.translated_text_en}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function Field({ label, value }: { label: string; value: string | number | boolean | null | undefined }) {
  return (
    <div>
      <dt className="text-gray-500 text-xs uppercase tracking-wide">{label}</dt>
      <dd className="mt-0.5 text-gray-900">{value !== null && value !== undefined ? String(value) : "—"}</dd>
    </div>
  );
}

const SIGNING_LABELS: Record<string, { label: string; className: string }> = {
  none:                 { label: "Nothing",            className: "bg-gray-100 text-gray-600" },
  signature_only:       { label: "Signature only",     className: "bg-blue-100 text-blue-700" },
  stamp_only:           { label: "Stamp only",          className: "bg-yellow-100 text-yellow-700" },
  signature_and_stamp:  { label: "Signature & Stamp",  className: "bg-green-100 text-green-700" },
};

function SigningBadge({ status }: { status: string | null | undefined }) {
  if (!status) return <span className="text-gray-400">—</span>;
  const s = SIGNING_LABELS[status] ?? { label: status, className: "bg-gray-100 text-gray-600" };
  return (
    <span className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${s.className}`}>
      {s.label}
    </span>
  );
}
