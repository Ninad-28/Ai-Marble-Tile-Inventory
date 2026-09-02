"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { History, Loader2 } from "lucide-react";
import api from "@/lib/api";

type SearchLog = { id: number; matched_tile_id?: number; confidence?: number; response_time_ms?: number; status?: string; searched_at?: string };

export default function HistoryPage() {
  const [logs, setLogs] = useState<SearchLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/api/search/history?limit=100")
      .then((response) => setLogs(response.data || []))
      .catch(() => setError("Search history could not be loaded."))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-4xl">
      <div className="mb-6 flex items-center gap-3"><History className="text-cyan-700" /><div><h1 className="text-2xl font-bold text-stone-800">Search History</h1><p className="text-sm text-stone-500">Recent visual searches from SearchLog</p></div></div>
      {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}
      <div className="overflow-hidden rounded-xl border border-stone-200 bg-white shadow-sm">
        {loading ? <div className="flex items-center justify-center gap-2 py-16 text-stone-500"><Loader2 className="animate-spin" /> Loading history...</div> : logs.length === 0 ? <p className="py-16 text-center text-stone-400">No searches recorded yet.</p> : <div className="divide-y divide-stone-100">{logs.map((log) => <div key={log.id} className="flex flex-wrap items-center justify-between gap-3 p-4"><div><p className="font-medium capitalize text-stone-800">{(log.status || "search").replaceAll("_", " ")}</p><p className="text-xs text-stone-500">{log.searched_at ? new Date(log.searched_at).toLocaleString() : "Timestamp unavailable"}</p></div><div className="flex items-center gap-4 text-sm text-stone-600">{log.matched_tile_id ? <Link href={`/dashboard/tiles/${log.matched_tile_id}`} className="text-cyan-700 hover:underline">Product #{log.matched_tile_id}</Link> : <span>No match</span>}{log.confidence != null && <span>{(log.confidence * 100).toFixed(1)} similarity</span>}{log.response_time_ms != null && <span>{log.response_time_ms} ms</span>}</div></div>)}</div>}
      </div>
    </div>
  );
}
