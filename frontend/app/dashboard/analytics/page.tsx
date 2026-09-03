"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { BarChart3, Clock, AlertTriangle, TrendingUp, Filter, Users, ChevronDown, ChevronUp, Package } from "lucide-react";

export default function AnalyticsPage() {
  const [data, setData] = useState<any>(null);
  const [funnelData, setFunnelData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selectedBracket, setSelectedBracket] = useState<"fresh" | "medium" | "aged" | null>("aged");

  useEffect(() => {
    Promise.all([
      api.get("/api/analytics/summary"),
      api.get("/api/analytics/funnel-and-clients")
    ])
      .then(([res1, res2]) => {
        setData(res1.data);
        setFunnelData(res2.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="text-center py-20 text-stone-400">Loading factory analytics suite...</div>;
  }

  const aging = data?.stock_aging || { fresh_under_90: 0, medium_90_180: 0, aged_over_180: 0, samples: { fresh: [], medium: [], aged: [] } };
  const samples = aging.samples || { fresh: [], medium: [], aged: [] };
  const prodSales = data?.production_vs_sales || { total_produced_sqm: 4500, total_sold_sqm: 3820, efficiency_ratio: "84.9%" };
  const topSellers = data?.top_selling_materials || [];
  const funnel = funnelData?.sales_funnel || { total_visual_searches: 371, quotations_generated: 0, orders_closed: 0, search_to_quote_conversion: "0.0%", quote_to_sale_conversion: "100%", overall_conversion: "0.0%" };
  const topClients = funnelData?.top_corporate_clients || [];

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <BarChart3 className="w-8 h-8 text-stone-700" />
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Factory Operations & Analytics</h1>
          <p className="text-xs text-stone-500">Real-time inventory aging, production metrics, search conversion, and client revenue intelligence</p>
        </div>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-sm">
          <div className="flex items-center justify-between text-stone-500 text-xs font-medium uppercase mb-2">
            <span>Production vs Sales</span>
            <TrendingUp size={16} className="text-green-600" />
          </div>
          <p className="text-2xl font-bold text-stone-800">{prodSales.efficiency_ratio}</p>
          <p className="text-xs text-stone-500 mt-1">
            {prodSales.total_sold_sqm} m² sold out of {prodSales.total_produced_sqm} m² produced
          </p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-sm">
          <div className="flex items-center justify-between text-stone-500 text-xs font-medium uppercase mb-2">
            <span>Aged Dead Stock (180+ Days)</span>
            <AlertTriangle size={16} className="text-amber-600" />
          </div>
          <p className="text-2xl font-bold text-amber-700">{aging.aged_over_180} pcs</p>
          <p className="text-xs text-stone-500 mt-1">Tying up warehouse yard space & capital</p>
        </div>

        <div className="bg-white p-5 rounded-xl border border-stone-200 shadow-sm">
          <div className="flex items-center justify-between text-stone-500 text-xs font-medium uppercase mb-2">
            <span>Search Conversion Rate</span>
            <Filter size={16} className="text-stone-700" />
          </div>
          <p className="text-2xl font-bold text-stone-800">{funnel.overall_conversion}</p>
          <p className="text-xs text-stone-500 mt-1">Visual Search to Closed B2B Order</p>
        </div>
      </div>

      {/* Stock Aging Breakdown Section with Interactive Card Selection */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-5 h-5 text-stone-700" />
            <h2 className="font-semibold text-stone-800 text-lg">Warehouse Stock Aging Report</h2>
          </div>
          <span className="text-xs text-stone-400">Click any card to inspect sample batches</span>
        </div>
        <p className="text-xs text-stone-500">
          Tracking duration of polished marble and stone slabs sitting in storage yards to prevent capital stagnation.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          {/* Fresh Stock Card */}
          <div 
            onClick={() => setSelectedBracket(selectedBracket === "fresh" ? null : "fresh")}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              selectedBracket === "fresh" 
                ? "bg-green-50/90 border-green-400 ring-2 ring-green-200 shadow-xs" 
                : "bg-green-50/40 border-green-200 hover:border-green-300"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-green-800 uppercase">Fresh Stock (&lt; 90 Days)</span>
              {selectedBracket === "fresh" ? <ChevronUp size={16} className="text-green-800"/> : <ChevronDown size={16} className="text-green-800"/>}
            </div>
            <p className="text-2xl font-bold text-green-900 mt-2">{aging.fresh_under_90} pieces</p>
            <p className="text-xs text-green-700 mt-1">Optimal turnover window</p>
          </div>

          {/* Medium Aging Card */}
          <div 
            onClick={() => setSelectedBracket(selectedBracket === "medium" ? null : "medium")}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              selectedBracket === "medium" 
                ? "bg-amber-50/90 border-amber-400 ring-2 ring-amber-200 shadow-xs" 
                : "bg-yellow-50/40 border-yellow-200 hover:border-yellow-300"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-yellow-800 uppercase">Medium Aging (90 - 180 Days)</span>
              {selectedBracket === "medium" ? <ChevronUp size={16} className="text-yellow-800"/> : <ChevronDown size={16} className="text-yellow-800"/>}
            </div>
            <p className="text-2xl font-bold text-yellow-900 mt-2">{aging.medium_90_180} pieces</p>
            <p className="text-xs text-yellow-700 mt-1">Requires active marketing push</p>
          </div>

          {/* Critical Aged Stock Card */}
          <div 
            onClick={() => setSelectedBracket(selectedBracket === "aged" ? null : "aged")}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              selectedBracket === "aged" 
                ? "bg-red-50/90 border-red-400 ring-2 ring-red-200 shadow-xs" 
                : "bg-red-50/40 border-red-200 hover:border-red-300"
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-red-800 uppercase">Critical Aged Stock (180+ Days)</span>
              {selectedBracket === "aged" ? <ChevronUp size={16} className="text-red-800"/> : <ChevronDown size={16} className="text-red-800"/>}
            </div>
            <p className="text-2xl font-bold text-red-900 mt-2">{aging.aged_over_180} pieces</p>
            <p className="text-xs text-red-700 mt-1">Recommended for clearance discount</p>
          </div>
        </div>

        {/* Dynamic Slab Cards Preview Drawer */}
        {selectedBracket && (
          <div className="mt-4 p-4 rounded-xl bg-stone-50 border border-stone-200 transition-all">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-stone-600 flex items-center gap-1.5">
                <Package size={14} />
                Sample Slabs: {selectedBracket === "fresh" ? "Fresh Stock (<90 Days)" : selectedBracket === "medium" ? "Medium Aging (90-180 Days)" : "Critical Aged Inventory (180+ Days)"}
              </h3>
              <span className="text-[11px] text-stone-400">Warehouse sample batches</span>
            </div>

            {samples[selectedBracket]?.length > 0 ? (
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {samples[selectedBracket].map((tile: any) => (
                  <div key={tile.id} className="bg-white rounded-lg border border-stone-200 p-2.5 shadow-xs flex flex-col justify-between">
                    <div>
                      <div className="w-full h-24 rounded bg-stone-100 mb-2 overflow-hidden flex items-center justify-center">
                        {tile.image_url ? (
                          <img src={tile.image_url} alt={tile.name} className="w-full h-full object-cover" />
                        ) : (
                          <div className="text-[11px] text-stone-400 uppercase font-mono">{tile.sku}</div>
                        )}
                      </div>
                      <p className="text-xs font-semibold text-stone-800 truncate">{tile.name}</p>
                      <p className="text-[10px] text-stone-400 font-mono">{tile.sku}</p>
                    </div>
                    <div className="mt-2 pt-2 border-t border-stone-100 flex items-center justify-between text-[11px]">
                      <span className="text-stone-600 font-medium">{tile.quantity} pcs</span>
                      <span className="text-[10px] text-stone-400 font-mono">{tile.date}</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-stone-400 py-3 text-center">No inventory slabs currently recorded in this category.</p>
            )}
          </div>
        )}
      </div>

      {/* Search-to-Sale Funnel Efficiency */}
      <div className="bg-white rounded-xl border border-stone-200 p-6 shadow-sm space-y-4">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-stone-700" />
          <h2 className="font-semibold text-stone-800 text-lg">Search-to-Sale Conversion Funnel</h2>
        </div>
        <p className="text-xs text-stone-500">
          Measures sales team efficiency and AI visual search engagement from query to closed B2B wholesale order.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
          <div className="bg-stone-50 border border-stone-200 p-4 rounded-lg text-center">
            <span className="text-xs font-semibold text-stone-500 uppercase">1. Visual Searches</span>
            <p className="text-2xl font-bold text-stone-900 mt-1">{funnel.total_visual_searches}</p>
            <p className="text-xs text-stone-500 mt-1">DINOv2 matching queries</p>
          </div>

          <div className="bg-stone-50 border border-stone-200 p-4 rounded-lg text-center">
            <span className="text-xs font-semibold text-stone-500 uppercase">2. Quotations Generated</span>
            <p className="text-2xl font-bold text-stone-900 mt-1">{funnel.quotations_generated}</p>
            <p className="text-xs text-stone-500 mt-1">{funnel.search_to_quote_conversion} conversion rate</p>
          </div>

          <div className="bg-stone-50 border border-stone-200 p-4 rounded-lg text-center">
            <span className="text-xs font-semibold text-stone-500 uppercase">3. Closed B2B Orders</span>
            <p className="text-2xl font-bold text-green-700 mt-1">{funnel.orders_closed}</p>
            <p className="text-xs text-stone-500 mt-1">{funnel.quote_to_sale_conversion} quote conversion</p>
          </div>
        </div>
      </div>

      {/* Top Sellers & Top Corporate Buyers Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-stone-200 p-6 shadow-sm space-y-4">
          <h2 className="font-semibold text-stone-800 text-lg">Top-Selling Materials</h2>
          <table className="w-full text-sm">
            <thead className="bg-stone-50 text-stone-500 text-xs uppercase tracking-wider border-b border-stone-200">
              <tr>
                <th className="text-left px-3 py-2">Material</th>
                <th className="text-right px-3 py-2">Volume</th>
                <th className="text-right px-3 py-2">Revenue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {topSellers.map((item: any, idx: number) => (
                <tr key={idx} className="hover:bg-stone-50">
                  <td className="px-3 py-2.5 font-medium text-stone-800">{item.material}</td>
                  <td className="px-3 py-2.5 text-right text-stone-600 font-mono">{item.volume_sqm} m²</td>
                  <td className="px-3 py-2.5 text-right font-semibold text-stone-900 font-mono">₹{item.revenue.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="bg-white rounded-xl border border-stone-200 p-6 shadow-sm space-y-4">
          <div className="flex items-center gap-2">
            <Users size={18} className="text-stone-700" />
            <h2 className="font-semibold text-stone-800 text-lg">Top Corporate Buyers</h2>
          </div>
          <table className="w-full text-sm">
            <thead className="bg-stone-50 text-stone-500 text-xs uppercase tracking-wider border-b border-stone-200">
              <tr>
                <th className="text-left px-3 py-2">Company / Buyer</th>
                <th className="text-right px-3 py-2">Orders</th>
                <th className="text-right px-3 py-2">Revenue</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {topClients.map((client: any, idx: number) => (
                <tr key={idx} className="hover:bg-stone-50">
                  <td className="px-3 py-2.5">
                    <p className="font-medium text-stone-800">{client.company}</p>
                    <p className="text-[10px] text-stone-400">{client.contact}</p>
                  </td>
                  <td className="px-3 py-2.5 text-right text-stone-600 font-mono">{client.total_orders}</td>
                  <td className="px-3 py-2.5 text-right font-semibold text-stone-900 font-mono">₹{client.revenue.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}