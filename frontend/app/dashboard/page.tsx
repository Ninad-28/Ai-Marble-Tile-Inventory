"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import StatCard from "@/components/StatCard";

export default function DashboardPage() {
  const [stats, setStats] = useState({
    total_tiles: 0,
    low_stock: 0,
    total_searches: 0,
  });

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const [tilesRes, lowStockRes, historyRes] = await Promise.all([
          api.get("/api/tiles/?limit=500"),
          api.get("/api/inventory/alerts/low-stock"),
          api.get("/api/search/history?limit=100"),
        ]);
        setStats({
          total_tiles:    tilesRes.data.length   || 0,
          low_stock:      lowStockRes.data.count || 0,
          total_searches: historyRes.data.length || 0,
        });
      } catch {}
    };
    fetchStats();
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold text-stone-800 mb-6">Dashboard</h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <StatCard label="Total Tiles"    value={stats.total_tiles}    icon="🪨" />
        <StatCard label="Low Stock"      value={stats.low_stock}      icon="⚠️" />
        <StatCard label="Total Searches" value={stats.total_searches} icon="🔍" />
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-stone-200">
        <h2 className="font-semibold text-stone-700 mb-2">Quick Actions</h2>
        <div className="flex gap-4 mt-4">
          <a href="/dashboard/search"
             className="bg-stone-800 text-white px-5 py-2.5 rounded-lg
                        text-sm font-medium hover:bg-stone-700 transition">
            🔍 Search a Tile
          </a>
          <a href="/dashboard/tiles"
             className="border border-stone-300 text-stone-700 px-5 py-2.5
                        rounded-lg text-sm font-medium hover:bg-stone-100 transition">
            ➕ Add New Tile
          </a>
        </div>
      </div>
    </div>
  );
}