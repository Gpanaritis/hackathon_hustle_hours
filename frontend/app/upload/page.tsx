"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { uploadContract } from "@/lib/api";

type FileStatus = "pending" | "processing" | "done" | "error";

interface FileEntry {
  file: File;
  status: FileStatus;
  error?: string;
  contractId?: number;
}

export default function UploadPage() {
  const router = useRouter();
  const [files, setFiles] = useState<FileEntry[]>([]);
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);

  function addFiles(incoming: FileList | File[]) {
    const pdfs = Array.from(incoming).filter((f) =>
      f.name.toLowerCase().endsWith(".pdf")
    );
    setFiles((prev) => {
      const existing = new Set(prev.map((e) => e.file.name));
      const newEntries: FileEntry[] = pdfs
        .filter((f) => !existing.has(f.name))
        .map((f) => ({ file: f, status: "pending" }));
      return [...prev, ...newEntries];
    });
  }

  function removeFile(name: string) {
    setFiles((prev) => prev.filter((e) => e.file.name !== name));
  }

  function onFileInput(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files) addFiles(e.target.files);
    e.target.value = "";
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setDragging(false);
    if (e.dataTransfer.files) addFiles(e.dataTransfer.files);
  }

  async function submit() {
    const pending = files.filter((e) => e.status === "pending");
    if (!pending.length) return;
    setUploading(true);

    const BATCH_SIZE = 5;
    for (let i = 0; i < pending.length; i += BATCH_SIZE) {
      const batch = pending.slice(i, i + BATCH_SIZE);

      // Mark entire batch as processing
      setFiles((prev) =>
        prev.map((e) =>
          batch.some((b) => b.file.name === e.file.name)
            ? { ...e, status: "processing" }
            : e
        )
      );

      await Promise.all(
        batch.map(async (entry) => {
          try {
            const contract = await uploadContract(entry.file);
            setFiles((prev) =>
              prev.map((e) =>
                e.file.name === entry.file.name
                  ? { ...e, status: "done", contractId: contract.contract_id }
                  : e
              )
            );
          } catch (err: unknown) {
            setFiles((prev) =>
              prev.map((e) =>
                e.file.name === entry.file.name
                  ? {
                      ...e,
                      status: "error",
                      error: err instanceof Error ? err.message : "Upload failed.",
                    }
                  : e
              )
            );
          }
        })
      );
    }

    setUploading(false);
  }

  const pendingCount = files.filter((e) => e.status === "pending").length;
  const doneFiles = files.filter((e) => e.status === "done");

  return (
    <div className="max-w-2xl">
      <h1 className="text-2xl font-semibold mb-6">Upload Contracts</h1>

      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`border-2 border-dashed rounded-lg p-10 text-center transition-colors ${
          dragging ? "border-blue-400 bg-blue-50" : "border-gray-300 bg-white hover:border-gray-400"
        }`}
      >
        <p className="text-gray-500 mb-3">Drag and drop PDFs here, or</p>
        <label className="cursor-pointer bg-gray-900 text-white px-4 py-2 rounded text-sm hover:bg-gray-700">
          Browse
          <input
            type="file"
            accept=".pdf"
            multiple
            onChange={onFileInput}
            className="hidden"
          />
        </label>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <ul className="mt-4 space-y-2">
          {files.map((entry) => (
            <li
              key={entry.file.name}
              className="flex items-center justify-between bg-white border border-gray-200 rounded px-4 py-2.5 text-sm"
            >
              <div className="flex items-center gap-3 min-w-0">
                <StatusDot status={entry.status} />
                <span className="truncate text-gray-800">{entry.file.name}</span>
                <span className="text-gray-400 shrink-0">
                  {(entry.file.size / 1024).toFixed(0)} KB
                </span>
              </div>
              <div className="flex items-center gap-3 shrink-0 ml-4">
                {entry.status === "processing" && (
                  <span className="text-blue-600 text-xs">Processing...</span>
                )}
                {entry.status === "error" && (
                  <span className="text-red-600 text-xs">{entry.error}</span>
                )}
                {entry.status === "done" && entry.contractId && (
                  <a
                    href={`/contracts/${entry.contractId}`}
                    className="text-blue-600 text-xs hover:underline"
                  >
                    View →
                  </a>
                )}
                {entry.status === "pending" && (
                  <button
                    onClick={() => removeFile(entry.file.name)}
                    className="text-gray-400 hover:text-red-500 text-xs"
                  >
                    Remove
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}

      {/* Actions */}
      <div className="mt-4 flex items-center gap-4">
        <button
          onClick={submit}
          disabled={!pendingCount || uploading}
          className="bg-blue-600 text-white px-6 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {uploading
            ? "Processing..."
            : `Upload & Process${pendingCount ? ` (${pendingCount})` : ""}`}
        </button>

        {doneFiles.length > 0 && !uploading && (
          <button
            onClick={() => router.push("/contracts")}
            className="text-sm text-blue-600 hover:underline"
          >
            View all contracts →
          </button>
        )}
      </div>

      {uploading && (
        <p className="mt-3 text-sm text-gray-500">
          Processing one at a time — each contract takes 30–60 seconds for Claude to analyze.
        </p>
      )}
    </div>
  );
}

function StatusDot({ status }: { status: FileStatus }) {
  const classes: Record<FileStatus, string> = {
    pending: "bg-gray-300",
    processing: "bg-blue-500 animate-pulse",
    done: "bg-green-500",
    error: "bg-red-500",
  };
  return <span className={`w-2 h-2 rounded-full shrink-0 ${classes[status]}`} />;
}
