"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { listContracts, ContractListItem } from "@/lib/api";

const STATUS_COLORS: Record<string, string> = {
  processed: "bg-green-100 text-green-800",
  processing: "bg-yellow-100 text-yellow-800",
  needs_review: "bg-red-100 text-red-800",
};

export default function ContractsPage() {
  const [contracts, setContracts] = useState<ContractListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [country, setCountry] = useState("");
  const [partyName, setPartyName] = useState("");
  const [expiringThisYear, setExpiringThisYear] = useState(false);
  const [missingSignature, setMissingSignature] = useState(false);
  const [missingStamp, setMissingStamp] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string | boolean> = {};
      if (country) params.country_code = country;
      if (partyName) params.party_name = partyName;
      if (expiringThisYear) params.expiring_this_year = true;
      if (missingSignature) params.missing_signature = true;
      if (missingStamp) params.missing_stamp = true;
      const data = await listContracts(params);
      setContracts(data);
    } catch (e) {
      setError("Failed to load contracts.");
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

  function resetFilters() {
    setCountry("");
    setPartyName("");
    setExpiringThisYear(false);
    setMissingSignature(false);
    setMissingStamp(false);
    setTimeout(load, 0);
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-semibold">Contracts</h1>
        <Link
          href="/upload"
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700"
        >
          Upload Contract
        </Link>
      </div>

      {/* Filters */}
      <form onSubmit={handleFilter} className="bg-white border border-gray-200 rounded p-4 mb-6">
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="block text-xs text-gray-500 mb-1">Country Code</label>
            <input
              type="text"
              value={country}
              onChange={(e) => setCountry(e.target.value.toUpperCase())}
              placeholder="e.g. US"
              maxLength={2}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-24"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">Party Name</label>
            <input
              type="text"
              value={partyName}
              onChange={(e) => setPartyName(e.target.value)}
              placeholder="Search party..."
              className="border border-gray-300 rounded px-3 py-1.5 text-sm w-48"
            />
          </div>
          <div className="flex flex-wrap gap-3 items-center">
            <button
              type="button"
              onClick={() => setExpiringThisYear(!expiringThisYear)}
              className={`px-3 py-1.5 rounded text-sm border ${
                expiringThisYear
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
              }`}
            >
              Expiring This Year
            </button>
            <button
              type="button"
              onClick={() => setMissingSignature(!missingSignature)}
              className={`px-3 py-1.5 rounded text-sm border ${
                missingSignature
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
              }`}
            >
              Missing Signature
            </button>
            <button
              type="button"
              onClick={() => setMissingStamp(!missingStamp)}
              className={`px-3 py-1.5 rounded text-sm border ${
                missingStamp
                  ? "bg-blue-600 text-white border-blue-600"
                  : "bg-white text-gray-700 border-gray-300 hover:bg-gray-50"
              }`}
            >
              Missing Stamp
            </button>
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
      ) : contracts.length === 0 ? (
        <p className="text-gray-500 text-sm">No contracts found.</p>
      ) : (
        <div className="overflow-x-auto bg-white border border-gray-200 rounded">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Ref No.</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">File</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Country</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Executed</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Expires</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {contracts.map((c) => (
                <tr key={c.contract_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3">
                    <Link
                      href={`/contracts/${c.contract_id}`}
                      className="text-blue-600 hover:underline font-medium"
                    >
                      {c.internal_ref_no ?? `#${c.contract_id}`}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-gray-700 max-w-xs truncate">{c.file_name}</td>
                  <td className="px-4 py-3 text-gray-600">{c.country_code ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{c.execution_date ?? "—"}</td>
                  <td className="px-4 py-3 text-gray-600">{c.expiry_date ?? "—"}</td>
                  <td className="px-4 py-3">
                    {c.status && (
                      <span
                        className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${
                          STATUS_COLORS[c.status] ?? "bg-gray-100 text-gray-700"
                        }`}
                      >
                        {c.status}
                      </span>
                    )}
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
