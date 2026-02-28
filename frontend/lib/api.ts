const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface ContractListItem {
  contract_id: number;
  internal_ref_no: string | null;
  file_name: string;
  country_code: string | null;
  language: string | null;
  execution_date: string | null;
  expiry_date: string | null;
  status: string | null;
  signature_present: boolean | null;
  stamp_present: boolean | null;
  upload_date: string | null;
}

export interface ContractParty {
  party_id: number;
  role: string | null;
  legal_name: string | null;
  representative_name: string | null;
  id_type: string | null;
  id_value: string | null;
  address: string | null;
}

export interface MusicalWork {
  work_id: number;
  title: string | null;
  artist_performer: string | null;
  lyricist: string | null;
  isrc_code: string | null;
  collection_society: string | null;
}

export interface ContractTerms {
  term_id: number;
  remuneration_amount: number | null;
  currency: string | null;
  min_penalty_liquidated_damages: number | null;
  delivery_deadline_days: number | null;
  registration_deadline_days: number | null;
  streaming_requirement_days: number | null;
}

export interface ContractIntelligence {
  intel_id: number;
  summary_short: string | null;
  translated_text_en: string | null;
}

export interface ContractDetail extends ContractListItem {
  jurisdiction_state_city: string | null;
  term_years: number | null;
  is_exclusive: boolean | null;
  parties: ContractParty[];
  works: MusicalWork[];
  terms: ContractTerms | null;
  intelligence: ContractIntelligence | null;
}

export interface SimilarContract {
  contract_id: number;
  internal_ref_no: string | null;
  file_name: string;
  similarity: number;
}

export interface ChatResponse {
  answer: string;
  sql: string | null;
  results: Record<string, unknown>[] | null;
}

export async function listContracts(params: Record<string, string | boolean>) {
  const query = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") {
      query.set(k, String(v));
    }
  }
  const res = await fetch(`${API_BASE}/contracts?${query}`);
  if (!res.ok) throw new Error("Failed to fetch contracts");
  return res.json() as Promise<ContractListItem[]>;
}

export async function getContract(id: number) {
  const res = await fetch(`${API_BASE}/contracts/${id}`);
  if (!res.ok) throw new Error("Contract not found");
  return res.json() as Promise<ContractDetail>;
}

export async function getSimilarContracts(id: number) {
  const res = await fetch(`${API_BASE}/contracts/${id}/similar`);
  if (!res.ok) throw new Error("Could not fetch similar contracts");
  return res.json() as Promise<SimilarContract[]>;
}

export async function uploadContract(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/contracts/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json() as Promise<ContractDetail>;
}

export async function chat(message: string, history: { role: string; content: string }[]) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json() as Promise<ChatResponse>;
}
