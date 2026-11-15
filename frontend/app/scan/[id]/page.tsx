import { MapPin, Package, Layers, Ruler, Tag, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";

type ScannedTile = {
  id: number;
  sku: string;
  name: string;
  description?: string;
  width_cm?: number;
  height_cm?: number;
  thickness_cm?: number;
  price_per_sqm?: number;
  stock_quantity?: number | null;
  stock_status?: string;
  stock_unit: string;
  material?: { name: string };
  finish?: { name: string };
  style?: { name: string };
  color_family?: { name: string };
  origin?: { name: string };
  location?: { warehouse?: string; aisle?: string; rack?: string; bin?: string } | null;
  images: { image_url: string }[];
};

export const dynamic = "force-dynamic";

export default async function MobileScanPage({
  params,
}: {
  params: Promise<{ id: string }> | { id: string };
}) {
  const resolvedParams = await Promise.resolve(params);
  const id = resolvedParams.id;

  let tile: ScannedTile | null = null;
  let error = "";

  try {
    const res = await fetch(`http://127.0.0.1:8000/tiles/${id}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!res.ok) {
      error = `Tile #${id} not found (HTTP ${res.status})`;
    } else {
      tile = await res.json();
    }
  } catch (err: unknown) {
    error = err instanceof Error ? err.message : "Could not reach backend on port 8000";
  }

  if (error || !tile) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="max-w-sm w-full bg-white rounded-2xl p-6 text-center shadow-lg border border-red-200">
          <XCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <h1 className="text-lg font-bold text-slate-900">Unable to Load Tile</h1>
          <p className="text-sm text-slate-500 mt-1">{error || "Tile record not found."}</p>
        </div>
      </div>
    );
  }

  const locationStr = [
    tile.location?.warehouse,
    tile.location?.aisle && `Aisle ${tile.location.aisle}`,
    tile.location?.rack && `Rack ${tile.location.rack}`,
    tile.location?.bin && `Bin ${tile.location.bin}`,
  ]
    .filter(Boolean)
    .join(" • ");

  const isOut = tile.stock_status === "OUT_OF_STOCK" || tile.stock_quantity === 0;
  const isLow = tile.stock_status === "LOW_STOCK";

  return (
    <div className="min-h-screen bg-slate-100 pb-10">
      <div className="bg-slate-900 text-white px-5 py-4 flex items-center justify-between sticky top-0 z-10 shadow-md">
        <div>
          <p className="text-[11px] uppercase tracking-widest text-cyan-400 font-semibold">
            Marble AI • Warehouse Scan
          </p>
          <p className="font-mono text-sm text-slate-200">{tile.sku}</p>
        </div>
        <span className="text-xs bg-white/10 px-2.5 py-1 rounded-full text-slate-200">
          ID #{tile.id}
        </span>
      </div>

      <div className="max-w-md mx-auto p-4 space-y-4">
        <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-slate-200">
          {tile.images?.[0] ? (
            <img
              src={`http://192.168.0.201:8000${tile.images[0].image_url}`}
              alt={tile.name}
              className="w-full h-56 object-cover bg-slate-200"
            />
          ) : (
            <div className="w-full h-44 bg-slate-200 flex items-center justify-center text-5xl">
              🪨
            </div>
          )}

          <div className="p-5">
            <div className="flex items-start justify-between gap-2">
              <h1 className="text-xl font-bold text-slate-900">{tile.name}</h1>
              {tile.price_per_sqm != null && (
                <span className="shrink-0 bg-cyan-50 text-cyan-800 border border-cyan-200 text-xs font-bold px-2.5 py-1 rounded-lg">
                  ₹{tile.price_per_sqm}/sqm
                </span>
              )}
            </div>
            {tile.description && (
              <p className="text-xs text-slate-500 mt-1.5 leading-relaxed">{tile.description}</p>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 mb-1">
              <Package size={14} className="text-cyan-600" /> Available Stock
            </div>
            <p className="text-2xl font-extrabold text-slate-900">
              {tile.stock_quantity ?? "—"}
              <span className="text-xs font-normal text-slate-500 ml-1">{tile.stock_unit}</span>
            </p>
            <div className="mt-1.5">
              {isOut ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-red-600 bg-red-50 px-2 py-0.5 rounded-full">
                  <XCircle size={12} /> Out of Stock
                </span>
              ) : isLow ? (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-amber-700 bg-amber-50 px-2 py-0.5 rounded-full">
                  <AlertTriangle size={12} /> Low Stock
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 text-[11px] font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full">
                  <CheckCircle2 size={12} /> In Stock
                </span>
              )}
            </div>
          </div>

          <div className="bg-white rounded-2xl p-4 border border-slate-200 shadow-sm">
            <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 mb-1">
              <MapPin size={14} className="text-cyan-600" /> Rack Location
            </div>
            <p className="text-sm font-bold text-slate-900 leading-snug mt-1">
              {locationStr || "Pending Assignment"}
            </p>
          </div>
        </div>

        <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-sm space-y-3">
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400">
            Slab Specifications
          </h2>
          <div className="grid grid-cols-2 gap-y-3 text-sm">
            <div>
              <p className="text-xs text-slate-400 flex items-center gap-1"><Layers size={12} /> Material</p>
              <p className="font-semibold text-slate-800">{tile.material?.name || "—"}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 flex items-center gap-1"><Tag size={12} /> Finish</p>
              <p className="font-semibold text-slate-800">{tile.finish?.name || "—"}</p>
            </div>
            <div>
              <p className="text-xs text-slate-400 flex items-center gap-1"><Ruler size={12} /> Dimensions</p>
              <p className="font-semibold text-slate-800 font-mono text-xs">
                {tile.width_cm && tile.height_cm
                  ? `${tile.width_cm} × ${tile.height_cm}${tile.thickness_cm ? ` × ${tile.thickness_cm}` : ""} cm`
                  : "—"}
              </p>
            </div>
            <div>
              <p className="text-xs text-slate-400">Color / Style</p>
              <p className="font-semibold text-slate-800">
                {[tile.color_family?.name, tile.style?.name].filter(Boolean).join(" • ") || "—"}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}