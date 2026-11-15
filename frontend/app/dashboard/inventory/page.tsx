"use client";
import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { Check, Pencil, ShieldCheck, Search } from "lucide-react";
import EditTileModal, { EditableTile } from "@/components/EditTileModal";

interface InventoryItem {
  id: number;
  tile_id: number;
  quantity: number;
  unit: string;
  low_stock_threshold: number;
}

type Tile = EditableTile & {
  images?: { image_url: string }[];
};

const marbleGrades = [
  {
    id: 1,
    name: "Group A",
    subtitle:
      "Highly sound marbles with excellent structural stability. They contain very few natural flaws or voids and require virtually no chemical fills or backing.",
  },
  {
    id: 2,
    name: "Group B",
    subtitle:
      "Similar to Group A, but may feature minimal pitting or small 'dry veins' that require a tiny amount of factory filling.",
  },
  {
    id: 3,
    name: "Group C",
    subtitle:
      "Marbles with frequent geological variations, natural faults, and voids. Manufacturers heavily treat these slabs with epoxy resins and mesh backing.",
  },
  {
    id: 4,
    name: "Group D",
    subtitle:
      "Highly fragile stones with maximum natural flaws and dramatic veining. They require the highest level of manufacturing repair and backing.",
  },
];

function dims(t?: Tile | null) {
  if (!t?.width_cm && !t?.height_cm) return "—";
  const w = t.width_cm ?? "?";
  const h = t.height_cm ?? "?";
  const th = t.thickness_cm != null ? ` × ${t.thickness_cm}` : "";
  return `${w}×${h}${th} cm`;
}

function matchesSearch(tile: Tile | undefined, q: string) {
  if (!q) return true;
  if (!tile) return false;
  const hay = [
    tile.name,
    tile.sku,
    tile.material?.name,
    tile.style?.name,
    tile.finish?.name,
    tile.color_family?.name,
    tile.size_format?.name,
    dims(tile),
    tile.width_cm,
    tile.height_cm,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();
  return hay.includes(q.toLowerCase());
}

export default function InventoryPage() {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [tiles, setTiles] = useState<Record<number, Tile>>({});
  const [categories, setCategories] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [editingStockId, setEditingStockId] = useState<number | null>(null);
  const [editQty, setEditQty] = useState(0);
  const [editingTile, setEditingTile] = useState<Tile | null>(null);
  const [filterType, setFilterType] = useState<"all" | "low" | "out">("all");
  const [search, setSearch] = useState("");

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [invRes, tilesRes, catRes] = await Promise.all([
        api.get("/api/inventory/"),
        api.get("/api/tiles/?limit=500"),
        api.get("/api/categories/all"),
      ]);
      setInventory(invRes.data);
      const tileMap: Record<number, Tile> = {};
      tilesRes.data.forEach((t: Tile) => {
        tileMap[t.id] = t;
      });
      setTiles(tileMap);
      setCategories(catRes.data);
    } catch {}
    setLoading(false);
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const saveQty = async (tileId: number, threshold: number) => {
    await api.put(`/api/inventory/${tileId}`, {
      quantity: editQty,
      unit: "pieces",
      low_stock_threshold: threshold,
    });
    setEditingStockId(null);
    fetchAll();
  };

  const filtered = useMemo(() => {
    return inventory.filter((i) => {
      if (filterType === "low") return i.quantity <= i.low_stock_threshold;
      if (filterType === "out") return i.quantity === 0;
      return true;
    }).filter((i) => matchesSearch(tiles[i.tile_id], search.trim()));
  }, [inventory, filterType, tiles, search]);

  const lowCount = inventory.filter((i) => i.quantity <= i.low_stock_threshold).length;
  const outCount = inventory.filter((i) => i.quantity === 0).length;

  const gradeGroups: Record<
    number,
    { name: string; subtitle: string; items: InventoryItem[] }
  > = {};
  marbleGrades.forEach((grade) => {
    gradeGroups[grade.id] = { name: grade.name, subtitle: grade.subtitle, items: [] };
  });
  filtered.forEach((item) => {
    const gradeId = ((item.tile_id - 1) % 4) + 1;
    if (gradeGroups[gradeId]) gradeGroups[gradeId].items.push(item);
  });

  return (
    <div>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Marble Quality Grades</h1>
          {lowCount > 0 && (
            <p className="text-sm text-red-500 mt-1">⚠️ {lowCount} tiles are low on stock</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {filterType !== "all" && (
            <button
              onClick={() => setFilterType("all")}
              className="px-3 py-2 rounded-lg text-sm font-medium border border-stone-300 text-stone-600 hover:bg-stone-50"
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

      {/* Search — same idea as catalog */}
      <div className="relative mb-4 max-w-lg">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search name, SKU, color, material, finish, 60x60..."
          className="w-full border border-stone-300 rounded-lg pl-9 pr-4 py-2 text-sm text-stone-900
                     placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-400"
        />
      </div>

      {loading ? (
        <div className="text-center py-20 text-stone-400 bg-white rounded-xl border border-stone-200 shadow-sm">
          Loading inventory grades...
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-stone-400 bg-white rounded-xl border border-stone-200">
          No inventory rows match your filters.
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
                <div className="bg-stone-50 px-6 py-4 border-b border-stone-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                  <div className="flex items-start gap-3">
                    <ShieldCheck className="w-5 h-5 text-stone-600 mt-0.5 flex-shrink-0" />
                    <div>
                      <h2 className="font-semibold text-stone-800 text-lg">{group.name}</h2>
                      <p className="text-xs text-stone-500 mt-0.5 max-w-3xl">{group.subtitle}</p>
                    </div>
                  </div>
                  <span className="text-xs font-medium bg-stone-200/70 text-stone-700 px-2.5 py-1 rounded-full self-start sm:self-center">
                    {group.items.length} {group.items.length === 1 ? "tile" : "tiles"}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-sm min-w-[900px]">
                    <thead className="bg-stone-50/50 border-b border-stone-100 text-stone-500 text-xs uppercase tracking-wider">
                      <tr>
                        <th className="text-left px-6 py-2.5 font-medium">Tile</th>
                        <th className="text-left px-3 py-2.5 font-medium">SKU</th>
                        <th className="text-left px-3 py-2.5 font-medium">Material</th>
                        <th className="text-left px-3 py-2.5 font-medium">Color</th>
                        <th className="text-left px-3 py-2.5 font-medium">Finish</th>
                        <th className="text-left px-3 py-2.5 font-medium">Style</th>
                        <th className="text-left px-3 py-2.5 font-medium">Dims</th>
                        <th className="text-left px-3 py-2.5 font-medium">Stock</th>
                        <th className="text-left px-3 py-2.5 font-medium">Status</th>
                        <th className="text-left px-3 py-2.5 font-medium">Edit</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-stone-100">
                      {group.items.map((item) => {
                        const tile = tiles[item.tile_id];
                        const isLow = item.quantity <= item.low_stock_threshold;
                        const editingStock = editingStockId === item.tile_id;

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
                                    <div className="w-full h-full flex items-center justify-center text-lg">
                                      🪨
                                    </div>
                                  )}
                                </div>
                                <span className="font-medium text-stone-800">
                                  {tile?.name || `Tile #${item.tile_id}`}
                                </span>
                              </div>
                            </td>
                            <td className="px-3 py-3 font-mono text-stone-500 text-xs">
                              {tile?.sku || "—"}
                            </td>
                            <td className="px-3 py-3 text-stone-600 text-xs">
                              {tile?.material?.name || "—"}
                            </td>
                            <td className="px-3 py-3 text-stone-600 text-xs">
                              {tile?.color_family?.name || "—"}
                            </td>
                            <td className="px-3 py-3 text-stone-600 text-xs">
                              {tile?.finish?.name || "—"}
                            </td>
                            <td className="px-3 py-3 text-stone-600 text-xs">
                              {tile?.style?.name || "—"}
                            </td>
                            <td className="px-3 py-3 text-stone-600 text-xs font-mono whitespace-nowrap">
                              {dims(tile)}
                            </td>
                            <td className="px-3 py-3">
                              {editingStock ? (
                                <input
                                  type="number"
                                  min="0"
                                  value={editQty}
                                  onChange={(e) => setEditQty(Number(e.target.value))}
                                  className="w-20 border border-stone-400 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-stone-400"
                                  autoFocus
                                />
                              ) : (
                                <span
                                  className={`font-semibold ${isLow ? "text-red-600" : "text-stone-800"}`}
                                >
                                  {item.quantity} {item.unit}
                                </span>
                              )}
                            </td>
                            <td className="px-3 py-3">
                              <span
                                className={`px-2 py-1 rounded-full text-xs font-medium ${
                                  item.quantity === 0
                                    ? "bg-red-100 text-red-700"
                                    : isLow
                                      ? "bg-yellow-100 text-yellow-700"
                                      : "bg-green-100 text-green-700"
                                }`}
                              >
                                {item.quantity === 0
                                  ? "Out of Stock"
                                  : isLow
                                    ? "Low Stock"
                                    : "In Stock"}
                              </span>
                            </td>
                            <td className="px-3 py-3">
                              <div className="flex items-center gap-2">
                                {editingStock ? (
                                  <button
                                    onClick={() =>
                                      saveQty(item.tile_id, item.low_stock_threshold)
                                    }
                                    className="text-green-600 hover:text-green-800"
                                    title="Save stock"
                                  >
                                    <Check size={16} />
                                  </button>
                                ) : (
                                  <button
                                    onClick={() => {
                                      setEditingStockId(item.tile_id);
                                      setEditQty(item.quantity);
                                    }}
                                    className="text-stone-400 hover:text-stone-700"
                                    title="Edit stock"
                                  >
                                    <Pencil size={16} />
                                  </button>
                                )}
                                {tile && (
                                  <button
                                    onClick={() => setEditingTile(tile)}
                                    className="text-xs text-stone-600 hover:text-stone-900 underline underline-offset-2"
                                    title="Edit tile features"
                                  >
                                    Features
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {editingTile && (
        <EditTileModal
          tile={editingTile}
          categories={categories}
          onClose={() => setEditingTile(null)}
          onSaved={(updated) => {
            setTiles((prev) => ({
              ...prev,
              [updated.id]: { ...prev[updated.id], ...updated },
            }));
          }}
        />
      )}
    </div>
  );
}
