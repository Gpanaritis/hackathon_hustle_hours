import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Contract Intelligence",
  description: "PDF contract management and AI analysis",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-gray-50 min-h-screen text-gray-900 antialiased">
        <nav className="bg-white border-b border-gray-200 px-6 py-3 flex items-center gap-6">
          <span className="font-semibold text-lg tracking-tight">Contract Intelligence</span>
          <Link href="/contracts" className="text-sm text-gray-600 hover:text-gray-900">
            Contracts
          </Link>
          <Link href="/upload" className="text-sm text-gray-600 hover:text-gray-900">
            Upload
          </Link>
          <Link href="/chat" className="text-sm text-gray-600 hover:text-gray-900">
            Chat
          </Link>
        </nav>
        <main className="max-w-7xl mx-auto px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
