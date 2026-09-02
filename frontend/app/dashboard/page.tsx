"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import StatCard from "@/components/StatCard";
import Link from "next/link";

type InventoryRow = { quantity: number };
type SearchRow = { id: number; status?: string; confidence?: number | null };

export default function DashboardPage() {
  const [stats, setStats] = useState({
    total_tiles: 0,
    low_stock: 0,
    out_of_stock: 0,
    total_searches: 0,
  });
  const [recent, setRecent] = useState<SearchRow[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [tilesRes, lowStockRes, inventoryRes, historyRes] = await Promise.all([
          api.get("/api/tiles/?limit=500"),
          api.get("/api/inventory/alerts/low-stock"),
          api.get("/api/inventory/"),
          api.get("/api/search/history?limit=100"),
        ]);
        const inventory: InventoryRow[] = inventoryRes.data || [];
        setStats({
          total_tiles:    tilesRes.data.length   || 0,
          low_stock:      lowStockRes.data.count || 0,
          out_of_stock:   inventory.filter((item) => item.quantity === 0).length,
          total_searches: historyRes.data.length || 0,
        });
        setRecent(historyRes.data.slice(0, 5));
      } catch { setError("Dashboard data could not be loaded."); }
    };
    fetchStats();
  }, []);

  return (
    <div>
      <div className="mb-6"><h1 className="text-2xl font-bold text-stone-800">Dashboard</h1><p className="mt-1 text-sm text-stone-500">Live catalog and search activity</p></div>
      {error && <p className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Tiles"    value={stats.total_tiles}    icon="🪨" />
        <StatCard label="Low Stock"      value={stats.low_stock}      icon="⚠️" />
        <StatCard label="Out of Stock"   value={stats.out_of_stock}   icon="○" />
        <StatCard label="Total Searches" value={stats.total_searches} icon="🔍" />
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-stone-200">
        <h2 className="font-semibold text-stone-700 mb-2">Quick Actions</h2>
        <div className="flex gap-4 mt-4">
          <Link href="/dashboard/search"
             className="bg-stone-800 text-white px-5 py-2.5 rounded-lg
                        text-sm font-medium hover:bg-stone-700 transition">
            🔍 Search Tile
          </Link>
          <Link href="/dashboard/tiles"
             className="border border-stone-300 text-stone-700 px-5 py-2.5
                        rounded-lg text-sm font-medium hover:bg-stone-100 transition">
            Browse Catalog
          </Link>
        </div>
      </div>
      <div className="mt-6 bg-white rounded-xl p-6 shadow-sm border border-stone-200">
        <div className="flex items-center justify-between"><h2 className="font-semibold text-stone-700">Recent searches</h2><Link href="/dashboard/history" className="text-sm text-cyan-700">View all</Link></div>
        {recent.length === 0 ? <p className="mt-5 text-sm text-stone-400">No searches recorded yet.</p> : <div className="mt-4 divide-y divide-stone-100">{recent.map((item) => <div key={item.id} className="flex items-center justify-between py-3 text-sm"><span className="text-stone-600">{item.status || "Search"}</span><span className="font-mono text-xs text-stone-500">{item.confidence != null ? `${(item.confidence * 100).toFixed(1)} similarity` : "No match"}</span></div>)}</div>}
      </div>
    </div>
  );
}