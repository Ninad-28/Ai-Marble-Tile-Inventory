"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Check, Pencil, ShieldCheck } from "lucide-react";

interface InventoryItem {
  id: number;
  tile_id: number;
  quantity: number;
  unit: string;
  low_stock_threshold: number;
}

interface Tile {
  id: number; 
  sku: string; 
  name: string; 
  images: any[];
  material_id?: number;
}

const marbleGrades = [
  {
    id: 1,
    name: "Group A",
    subtitle: "Highly sound marbles with excellent structural stability. They contain very few natural flaws or voids and require virtually no chemical fills or backing."
  },
  {
    id: 2,
    name: "Group B",
    subtitle: "Similar to Group A, but may feature minimal pitting or small 'dry veins' (natural separations in the stone) that require a tiny amount of factory filling."
  },
  {
    id: 3,
    name: "Group C",
    subtitle: "Marbles with frequent geological variations, natural faults, and voids. Manufacturers heavily treat these slabs with epoxy resins and mesh backing to make them stable."
  },
  {
    id: 4,
    name: "Group D",
    subtitle: "Highly fragile stones with maximum natural flaws and dramatic, shifting veining. They require the highest level of manufacturing repair and backing, but often feature the most exotic colors."
  }
];

export default function InventoryPage() {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [tiles, setTiles]         = useState<Record<number, Tile>>({});
  const [loading, setLoading]     = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editQty, setEditQty]     = useState<number>(0);
  const [filterType, setFilterType] = useState<"all" | "low" | "out">("all");

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [invRes, tilesRes] = await Promise.all([
        api.get("/api/inventory/"),
        api.get("/api/tiles/?limit=500"),
      ]);
      setInventory(invRes.data);

      const tileMap: Record<number, Tile> = {};
      tilesRes.data.forEach((t: Tile) => { tileMap[t.id] = t; });
      setTiles(tileMap);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { fetchAll(); }, []);

  const saveQty = async (tileId: number, threshold: number) => {
    await api.put(`/api/inventory/${tileId}`, {
      quantity: editQty,
      unit: "pieces",
      low_stock_threshold: threshold,
    });
    setEditingId(null);
    fetchAll();
  };

  const filtered = inventory.filter((i) => {
    if (filterType === "low") return i.quantity <= i.low_stock_threshold;
    if (filterType === "out") return i.quantity === 0;
    return true;
  });

  const lowCount = inventory.filter(
    (i) => i.quantity <= i.low_stock_threshold
  ).length;

  const outCount = inventory.filter(
    (i) => i.quantity === 0
  ).length;

  // Group filtered items by Grade (Group A, B, C, D) using tile ID modulus distribution
  const gradeGroups: Record<number, { name: string; subtitle: string; items: InventoryItem[] }> = {};
  marbleGrades.forEach((grade) => {
    gradeGroups[grade.id] = { name: grade.name, subtitle: grade.subtitle, items: [] };
  });

  filtered.forEach((item) => {
    const gradeId = ((item.tile_id - 1) % 4) + 1;
    if (gradeGroups[gradeId]) {
      gradeGroups[gradeId].items.push(item);
    }
  });

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Marble Quality Grades</h1>
          {lowCount > 0 && (
            <p className="text-sm text-red-500 mt-1">
              ⚠️ {lowCount} tiles are low on stock
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {filterType !== "all" && (
            <button
              onClick={() => setFilterType("all")}
              className="px-3 py-2 rounded-lg text-sm font-medium border border-stone-300 text-stone-600 hover:bg-stone-50 transition"
            >
              Show All
            </button>
          )}
          <button
            onClick={() => setFilterType(filterType === "low" ? "all" : "low")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              filterType === "low"
                ? "bg-yellow-500 text-white"
                : "border border-stone-300 text-stone-600 hover:bg-stone-50"
            }`}
          >
            ⚠️ Low Stock ({lowCount})
          </button>
          <button
            onClick={() => setFilterType(filterType === "out" ? "all" : "out")}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${
              filterType === "out"
                ? "bg-red-500 text-white"
                : "border border-stone-300 text-stone-600 hover:bg-stone-50"
            }`}
          >
            ❌ Out of Stock ({outCount})
          </button>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-20 text-stone-400 bg-white rounded-xl border border-stone-200 shadow-sm">
          Loading inventory grades...
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(gradeGroups).map(([gradeIdStr, group]) => {
            const gradeId = Number(gradeIdStr);
            if (group.items.length === 0) return null;

            return (
              <div 
                key={gradeId} 
                className="bg-white rounded-xl border border-stone-200 shadow-sm overflow-hidden"
              >
                {/* Grade Card Header */}
                <div className="bg-stone-50 px-6 py-4 border-b border-stone-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="flex items-start gap-3">
                    <ShieldCheck className="w-5 h-5 text-stone-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <h2 className="font-semibold text-stone-800 text-lg">{group.name}</h2>
                      <p className="text-xs text-stone-500 mt-0.5 max-w-3xl">{group.subtitle}</p>
                    </div>
                  </div>
                  <span className="text-xs font-medium bg-stone-200/70 text-stone-700 px-2.5 py-1 rounded-full self-start sm:self-center flex-shrink-0">
                    {group.items.length} {group.items.length === 1 ? 'tile' : 'tiles'}
                  </span>
                </div>

                {/* Tiles Table for this Grade */}
                <table className="w-full text-sm">
                  <thead className="bg-stone-50/50 border-b border-stone-100 text-stone-500 text-xs uppercase tracking-wider">
                    <tr>
                      <th className="text-left px-6 py-2.5 font-medium">Tile</th>
                      <th className="text-left px-4 py-2.5 font-medium">SKU</th>
                      <th className="text-left px-4 py-2.5 font-medium">Stock</th>
                      <th className="text-left px-4 py-2.5 font-medium">Threshold</th>
                      <th className="text-left px-4 py-2.5 font-medium">Status</th>
                      <th className="text-left px-4 py-2.5 font-medium">Edit</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stone-100">
                    {group.items.map((item) => {
                      const tile = tiles[item.tile_id];
                      const isLow = item.quantity <= item.low_stock_threshold;
                      const editing = editingId === item.tile_id;

                      return (
                        <tr 
                          key={item.id} 
                          className={`transition ${isLow ? "bg-red-50/60" : "hover:bg-stone-50/60"}`}
                        >
                          <td className="px-6 py-3">
                            <div className="flex items-center gap-3">
                              <div className="w-10 h-10 rounded-lg overflow-hidden bg-stone-100 border border-stone-200 flex-shrink-0">
                                {tile?.images?.[0] ? (
                                  <img
                                    src={`http://localhost:8000${tile.images[0].image_url}`}
                                    className="w-full h-full object-cover"
                                    alt={tile.name}
                                  />
                                ) : (
                                  <div className="w-full h-full flex items-center justify-center text-lg">🪨</div>
                                )}
                              </div>
                              <span className="font-medium text-stone-800">
                                {tile?.name || `Tile #${item.tile_id}`}
                              </span>
                            </div>
                          </td>

                          <td className="px-4 py-3 font-mono text-stone-500 text-xs">
                            {tile?.sku || "—"}
                          </td>

                          <td className="px-4 py-3">
                            {editing ? (
                              <input
                                type="number" 
                                min="0"
                                value={editQty}
                                onChange={(e) => setEditQty(Number(e.target.value))}
                                className="w-20 border border-stone-400 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-stone-400"
                                autoFocus
                              />
                            ) : (
                              <span className={`font-semibold ${isLow ? "text-red-600" : "text-stone-800"}`}>
                                {item.quantity} {item.unit}
                              </span>
                            )}
                          </td>

                          <td className="px-4 py-3 text-stone-400 text-xs">
                            Min {item.low_stock_threshold}
                          </td>

                          <td className="px-4 py-3">
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                              item.quantity === 0
                                ? "bg-red-100 text-red-700"
                                : isLow
                                ? "bg-yellow-100 text-yellow-700"
                                : "bg-green-100 text-green-700"
                            }`}>
                              {item.quantity === 0 ? "Out of Stock" : isLow ? "Low Stock" : "In Stock"}
                            </span>
                          </td>

                          <td className="px-4 py-3">
                            {editing ? (
                              <button
                                onClick={() => saveQty(item.tile_id, item.low_stock_threshold)}
                                className="text-green-600 hover:text-green-800 transition"
                                title="Save"
                              >
                                <Check size={16} />
                              </button>
                            ) : (
                              <button
                                onClick={() => {
                                  setEditingId(item.tile_id);
                                  setEditQty(item.quantity);
                                }}
                                className="text-stone-400 hover:text-stone-700 transition"
                                title="Edit stock"
                              >
                                <Pencil size={16} />
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}