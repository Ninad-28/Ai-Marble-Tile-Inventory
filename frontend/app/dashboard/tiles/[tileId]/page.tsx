"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, Package } from "lucide-react";
import api from "@/lib/api";

type Category = { name: string };
type Tile = {
  id: number;
  sku: string;
  name: string;
  description?: string;
  width_cm?: number;
  height_cm?: number;
  thickness_cm?: number;
  price_per_sqm?: number;
  material?: Category;
  style?: Category;
  finish?: Category;
  size_format?: Category;
  application?: Category;
  color_family?: Category;
  inventory?: { quantity: number; unit: string; low_stock_threshold: number } | null;
  stock_quantity?: number | null;
  stock_status?: string;
  low_stock?: boolean;
  images?: { id: number; image_url: string; is_primary: boolean }[];
};

const statusStyles: Record<string, string> = {
  IN_STOCK: "bg-emerald-100 text-emerald-800",
  LOW_STOCK: "bg-amber-100 text-amber-800",
  OUT_OF_STOCK: "bg-red-100 text-red-800",
  INVENTORY_NOT_CONFIGURED: "bg-stone-100 text-stone-700",
};

export default function TileDetailsPage({ params }: { params: Promise<{ tileId: string }> }) {
  const [tile, setTile] = useState<Tile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    params.then(({ tileId }) => api.get(`/api/tiles/${tileId}`)
      .then((response) => setTile(response.data))
      .catch(() => setError("Product details could not be loaded."))
      .finally(() => setLoading(false)));
  }, [params]);

  if (loading) return <div className="flex min-h-[50vh] items-center justify-center text-stone-500"><Loader2 className="animate-spin mr-2" /> Loading product...</div>;
  if (error || !tile) return <div className="space-y-4"><Link href="/dashboard/tiles" className="inline-flex items-center gap-2 text-sm text-stone-600"><ArrowLeft size={16} /> Back to catalog</Link><p className="rounded-lg bg-red-50 p-4 text-red-700">{error || "Product not found."}</p></div>;

  const status = tile.stock_status || (tile.inventory ? (tile.inventory.quantity === 0 ? "OUT_OF_STOCK" : tile.low_stock ? "LOW_STOCK" : "IN_STOCK") : "INVENTORY_NOT_CONFIGURED");
  const images = tile.images || [];

  return (
    <div className="max-w-5xl space-y-6">
      <Link href="/dashboard/tiles" className="inline-flex items-center gap-2 text-sm text-stone-600 hover:text-stone-900"><ArrowLeft size={16} /> Back to catalog</Link>
      <div className="grid gap-8 lg:grid-cols-[1.05fr_1fr]">
        <section className="rounded-xl border border-stone-200 bg-white p-4 shadow-sm">
          <div className="aspect-square overflow-hidden rounded-lg bg-stone-100">
            {images[0] ? <img src={`http://localhost:8000${images[0].image_url}`} alt={tile.name} className="h-full w-full object-contain" /> : <div className="flex h-full items-center justify-center text-6xl text-stone-300">◆</div>}
          </div>
          {images.length > 1 && <div className="mt-3 grid grid-cols-5 gap-2">{images.slice(0, 5).map((image) => <img key={image.id} src={`http://localhost:8000${image.image_url}`} alt="" className="aspect-square rounded border border-stone-200 object-cover" />)}</div>}
        </section>
        <section className="space-y-6">
          <div><p className="font-mono text-sm text-stone-500">{tile.sku}</p><h1 className="mt-1 text-3xl font-bold text-stone-900">{tile.name}</h1><p className="mt-3 text-stone-600">{tile.description || "No description available."}</p></div>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {[['Material', tile.material?.name], ['Style', tile.style?.name], ['Finish', tile.finish?.name], ['Size', tile.size_format?.name], ['Application', tile.application?.name], ['Color', tile.color_family?.name]].map(([label, value]) => <div key={label} className="rounded-lg bg-stone-50 p-3"><p className="text-xs text-stone-500">{label}</p><p className="mt-1 font-medium text-stone-800">{value || "Not specified"}</p></div>)}
          </div>
          <div className="flex flex-wrap gap-3 text-sm text-stone-700"><span>Dimensions: {tile.width_cm || "?"} x {tile.height_cm || "?"} x {tile.thickness_cm || "?"} cm</span>{tile.price_per_sqm != null && <span className="font-semibold">₹{tile.price_per_sqm}/sqm</span>}</div>
          <div className="flex items-center gap-3 border-t border-stone-200 pt-5"><Package size={20} className="text-stone-500" /><span className={`rounded-full px-3 py-1 text-sm font-semibold ${statusStyles[status] || statusStyles.INVENTORY_NOT_CONFIGURED}`}>{status.replaceAll("_", " ")}</span><span className="text-sm text-stone-600">{tile.inventory ? `${tile.inventory.quantity} ${tile.inventory.unit}` : "Inventory information unavailable"}</span></div>
        </section>
      </div>
    </div>
  );
}
