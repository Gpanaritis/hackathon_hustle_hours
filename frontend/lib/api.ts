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
  signing_status: "none" | "signature_only" | "stamp_only" | "signature_and_stamp" | null;
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

// ── Decisions ────────────────────────────────────────────────────────────────

export interface DecisionListItem {
  id: string;
  source_filename: string | null;
  court: string | null;
  judge: string | null;
  case_number: string | null;
  case_type: string | null;
  plaintiff: string | null;
  defendant: string | null;
  outcome: string | null;
  decision_date: string | null;
  monetary_award: number | null;
  processing_status: string;
  created_at: string | null;
}

export interface DecisionCategory {
  id: string;
  category: string;
  subcategory: string;
}

export interface DecisionArgument {
  id: string;
  side: "plaintiff" | "defendant";
  argument: string;
  position: number;
}

export interface DecisionLegalRef {
  id: string;
  reference: string;
}

export interface DecisionDetail extends DecisionListItem {
  full_text: string | null;
  summary: string | null;
  appeal_of: string | null;
  is_ocr: boolean;
  ocr_confidence: number | null;
  extraction_error: string | null;
  categories: DecisionCategory[];
  arguments: DecisionArgument[];
  legal_refs: DecisionLegalRef[];
}

export interface SimilarDecision {
  id: string;
  source_filename: string | null;
  court: string | null;
  case_number: string | null;
  similarity: number;
}

export async function listDecisions(params: Record<string, string>) {
  const query = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v) query.set(k, v);
  }
  const res = await fetch(`${API_BASE}/decisions?${query}`);
  if (!res.ok) throw new Error("Failed to fetch decisions");
  return res.json() as Promise<DecisionListItem[]>;
}

export async function getDecision(id: string) {
  const res = await fetch(`${API_BASE}/decisions/${id}`);
  if (!res.ok) throw new Error("Decision not found");
  return res.json() as Promise<DecisionDetail>;
}

export async function getSimilarDecisions(id: string) {
  const res = await fetch(`${API_BASE}/decisions/${id}/similar`);
  if (!res.ok) throw new Error("Could not fetch similar decisions");
  return res.json() as Promise<SimilarDecision[]>;
}

export async function deleteDecision(id: string) {
  const res = await fetch(`${API_BASE}/decisions/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Failed to delete decision");
}

export async function uploadDecision(file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API_BASE}/decisions/upload`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json() as Promise<DecisionDetail>;
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export async function chat(message: string, history: { role: string; content: string }[]) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, history }),
  });
  if (!res.ok) throw new Error("Chat request failed");
  return res.json() as Promise<ChatResponse>;
}

export interface SummaryMatchResult {
  id: string;
  source_filename: string | null;
  court: string | null;
  case_number: string | null;
  case_type: string | null;
  plaintiff: string | null;
  defendant: string | null;
  outcome: string | null;
  similarity: number | null;
  matched_categories: string[] | null;
}

export async function findByCategories(summary: string) {
  const res = await fetch(`${API_BASE}/chat/find-by-categories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ summary }),
  });
  if (!res.ok) throw new Error("Category search failed");
  return res.json() as Promise<SummaryMatchResult[]>;
}

export async function findBySimilarity(summary: string) {
  const res = await fetch(`${API_BASE}/chat/find-by-similarity`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ summary }),
  });
  if (!res.ok) throw new Error("Similarity search failed");
  return res.json() as Promise<SummaryMatchResult[]>;
}
