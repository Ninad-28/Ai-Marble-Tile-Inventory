"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Check, Pencil } from "lucide-react";

interface InventoryItem {
  id: number;
  tile_id: number;
  quantity: number;
  unit: string;
  low_stock_threshold: number;
}

interface Tile {
  id: number; sku: string; name: string; images: any[];
}

export default function InventoryPage() {
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [tiles, setTiles]         = useState<Record<number, Tile>>({});
  const [loading, setLoading]     = useState(true);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editQty, setEditQty]     = useState<number>(0);
  const [showLowOnly, setShowLowOnly] = useState(false);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [invRes, tilesRes] = await Promise.all([
        api.get("/api/inventory/"),
        api.get("/api/tiles/?limit=500"),
      ]);
      setInventory(invRes.data);

      // Build tile lookup map
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

  const filtered = showLowOnly
    ? inventory.filter((i) => i.quantity <= i.low_stock_threshold)
    : inventory;

  const lowCount = inventory.filter(
    (i) => i.quantity <= i.low_stock_threshold
  ).length;

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-stone-800">Inventory</h1>
          {lowCount > 0 && (
            <p className="text-sm text-red-500 mt-1">
              ⚠️ {lowCount} tiles are low on stock
            </p>
          )}
        </div>
        <button
          onClick={() => setShowLowOnly(!showLowOnly)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition
            ${showLowOnly
              ? "bg-red-500 text-white"
              : "border border-stone-300 text-stone-600 hover:bg-stone-50"
            }`}
        >
          {showLowOnly ? "Show All" : `⚠️ Low Stock (${lowCount})`}
        </button>
      </div>

      {/* Table */}
      <div className="bg-white rounded-xl border border-stone-200
                      shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-stone-50 border-b border-stone-200">
            <tr>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Tile
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                SKU
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Stock
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Threshold
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Status
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Edit
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {loading ? (
              <tr>
                <td colSpan={6}
                    className="text-center py-12 text-stone-400">
                  Loading...
                </td>
              </tr>
            ) : filtered.map((item) => {
              const tile    = tiles[item.tile_id];
              const isLow   = item.quantity <= item.low_stock_threshold;
              const editing = editingId === item.tile_id;

              return (
                <tr key={item.id}
                    className={`transition ${
                      isLow ? "bg-red-50" : "hover:bg-stone-50"
                    }`}>
                  {/* Tile Info */}
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg overflow-hidden
                                      bg-stone-100 border border-stone-200
                                      flex-shrink-0">
                        {tile?.images?.[0] ? (
                          <img
                            src={`http://localhost:8000${tile.images[0].image_url}`}
                            className="w-full h-full object-cover"
                            alt={tile.name}
                          />
                        ) : (
                          <div className="w-full h-full flex items-center
                                          justify-center text-lg">🪨</div>
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

                  {/* Editable Quantity */}
                  <td className="px-4 py-3">
                    {editing ? (
                      <input
                        type="number" min="0"
                        value={editQty}
                        onChange={(e) => setEditQty(Number(e.target.value))}
                        className="w-20 border border-stone-400 rounded
                                   px-2 py-1 text-sm focus:outline-none
                                   focus:ring-2 focus:ring-stone-400"
                        autoFocus
                      />
                    ) : (
                      <span className={`font-semibold ${
                        isLow ? "text-red-600" : "text-stone-800"
                      }`}>
                        {item.quantity} {item.unit}
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-3 text-stone-400 text-xs">
                    Min {item.low_stock_threshold}
                  </td>

                  {/* Status Badge */}
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs
                                      font-medium ${
                      item.quantity === 0
                        ? "bg-red-100 text-red-700"
                        : isLow
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-green-100 text-green-700"
                    }`}>
                      {item.quantity === 0
                        ? "Out of Stock"
                        : isLow ? "Low Stock" : "In Stock"}
                    </span>
                  </td>

                  {/* Edit / Save Button */}
                  <td className="px-4 py-3">
                    {editing ? (
                      <button
                        onClick={() =>
                          saveQty(item.tile_id, item.low_stock_threshold)
                        }
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

        <div className="px-4 py-3 border-t border-stone-100
                        text-xs text-stone-400">
          {filtered.length} items shown
        </div>
      </div>
    </div>
  );
}