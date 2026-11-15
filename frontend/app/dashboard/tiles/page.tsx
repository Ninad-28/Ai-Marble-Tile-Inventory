"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api";
import { Plus, Pencil, X, Search } from "lucide-react";
import EditTileModal, { EditableTile } from "@/components/EditTileModal";

interface Category { id: number; name: string; }
type Tile = EditableTile & {
  is_active: boolean;
  images: { image_url: string }[];
};

function dims(tile: Tile) {
  if (tile.width_cm == null && tile.height_cm == null) return "—";
  return `${tile.width_cm ?? "?"}×${tile.height_cm ?? "?"}${
    tile.thickness_cm != null ? `×${tile.thickness_cm}` : ""
  }`;
}

export default function TilesPage() {
  const [tiles, setTiles] = useState<Tile[]>([]);
  const [categories, setCategories] = useState<any>({});
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");
  const [filterMat, setFilterMat] = useState("");
  const [editingTile, setEditingTile] = useState<Tile | null>(null);

  const [form, setForm] = useState({
    sku: "", name: "", description: "",
    material_id: "", style_id: "", finish_id: "",
    size_format_id: "", application_id: "",
    color_family_id: "", origin_id: "",
    width_cm: "", height_cm: "",
    thickness_cm: "", price_per_sqm: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [tileImage, setTileImage] = useState<File | null>(null);

  const fetchTiles = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.append("search", search);
      if (filterMat) params.append("material_id", filterMat);
      params.append("limit", "200");
      const res = await api.get(`/api/tiles/?${params}`);
      setTiles(res.data);
    } catch {}
    setLoading(false);
  };

  const fetchCategories = async () => {
    try {
      const res = await api.get("/api/categories/all");
      setCategories(res.data);
    } catch {}
  };

  useEffect(() => { fetchCategories(); }, []);
  useEffect(() => {
    const t = setTimeout(fetchTiles, 250);
    return () => clearTimeout(t);
  }, [search, filterMat]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError("");
    try {
      if (tileImage) {
        const fd = new FormData();
        fd.append("sku", form.sku);
        fd.append("name", form.name);
        fd.append("material_id", String(form.material_id));
        if (form.description) fd.append("description", form.description);
        [
          "style_id", "finish_id", "size_format_id", "application_id",
          "color_family_id", "origin_id", "width_cm", "height_cm",
          "thickness_cm", "price_per_sqm",
        ].forEach((k) => {
          const v = (form as any)[k];
          if (v !== "") fd.append(k, String(v));
        });
        fd.append("image", tileImage);
        await api.post("/api/tiles/with-image", fd);
      } else {
        const payload: any = { ...form };
        Object.keys(payload).forEach((k) => {
          if (payload[k] === "") payload[k] = null;
          else if (k.endsWith("_id") || k.endsWith("_cm") || k === "price_per_sqm") {
            payload[k] = payload[k] ? Number(payload[k]) : null;
          }
        });
        await api.post("/api/tiles/", payload);
      }
      setShowForm(false);
      setForm({
        sku: "", name: "", description: "",
        material_id: "", style_id: "", finish_id: "",
        size_format_id: "", application_id: "",
        color_family_id: "", origin_id: "",
        width_cm: "", height_cm: "",
        thickness_cm: "", price_per_sqm: "",
      });
      setTileImage(null);
      fetchTiles();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Failed to add tile");
    }
    setSubmitting(false);
  };

  const deactivate = async (id: number, sku: string) => {
    if (!confirm(`Deactivate ${sku}?`)) return;
    await api.delete(`/api/tiles/${id}`);
    fetchTiles();
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-stone-800">Tile Catalog</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-stone-800 text-white px-4 py-2 rounded-lg text-sm hover:bg-stone-700 transition"
        >
          <Plus size={16} />
          Add New Tile
        </button>
      </div>

      {showForm && (
        <div className="bg-white border border-stone-200 rounded-xl p-6 mb-6 shadow-sm">
          <h2 className="font-semibold text-stone-800 mb-4">New Tile</h2>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div>
                <label className="text-xs font-medium text-stone-600">SKU *</label>
                <input
                  required value={form.sku}
                  onChange={(e) => setForm({ ...form, sku: e.target.value })}
                  placeholder="e.g. CAR-WHT-001"
                  className="w-full border border-stone-300 rounded-lg text-stone-900 placeholder-stone-500 px-3 py-2 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-stone-400"
                />
              </div>
              <div className="col-span-2">
                <label className="text-xs font-medium text-stone-600">Name *</label>
                <input
                  required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Carrara White 60x60"
                  className="w-full border border-stone-300 rounded-lg text-stone-900 placeholder-stone-500 px-3 py-2 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-stone-400"
                />
              </div>
              {[
                { key: "material_id", label: "Material *", data: categories.materials, required: true },
                { key: "style_id", label: "Style", data: categories.styles },
                { key: "finish_id", label: "Finish", data: categories.finishes },
                { key: "size_format_id", label: "Size Format", data: categories.sizes },
                { key: "application_id", label: "Application", data: categories.applications },
                { key: "color_family_id", label: "Color Family", data: categories.colors },
                { key: "origin_id", label: "Origin", data: categories.origins },
              ].map(({ key, label, data, required }) => (
                <div key={key}>
                  <label className="text-xs font-medium text-stone-600">{label}</label>
                  <select
                    required={required}
                    value={(form as any)[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    className="w-full border border-stone-300 rounded-lg text-stone-900 px-3 py-2 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-stone-400 bg-white"
                  >
                    <option value="">-- Select --</option>
                    {(data || []).map((c: Category) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              ))}
              {[
                { key: "width_cm", label: "Width (cm)" },
                { key: "height_cm", label: "Height (cm)" },
                { key: "thickness_cm", label: "Thickness (cm)" },
                { key: "price_per_sqm", label: "Price / sqm" },
              ].map(({ key, label }) => (
                <div key={key}>
                  <label className="text-xs font-medium text-stone-600">{label}</label>
                  <input
                    type="number" step="0.01"
                    value={(form as any)[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    className="w-full border border-stone-300 rounded-lg text-stone-900 px-3 py-2 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-stone-400"
                  />
                </div>
              ))}
              <div className="col-span-2 md:col-span-3">
                <label className="text-xs font-medium text-stone-600">Description</label>
                <textarea
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  rows={2}
                  className="w-full border border-stone-300 rounded-lg text-stone-900 px-3 py-2 text-sm mt-1 focus:outline-none focus:ring-2 focus:ring-stone-400"
                />
              </div>
              <div className="col-span-2 md:col-span-3">
                <label className="text-xs font-medium text-stone-600">Tile Image (optional)</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => setTileImage(e.target.files?.[0] || null)}
                  className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm mt-1 file:mr-3 file:py-1 file:px-3 file:rounded-md file:border-0 file:bg-stone-100 file:text-stone-700"
                />
              </div>
            </div>
            {formError && <p className="text-red-500 text-sm mt-3">{formError}</p>}
            <div className="flex gap-3 mt-4">
              <button type="submit" disabled={submitting} className="bg-stone-800 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-stone-700 disabled:opacity-50">
                {submitting ? "Saving..." : "Save Tile"}
              </button>
              <button type="button" onClick={() => setShowForm(false)} className="border border-stone-300 px-5 py-2 rounded-lg text-sm text-stone-600 hover:bg-stone-50">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-stone-400" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search name, SKU, color, material, 60x60..."
            className="border border-stone-300 rounded-lg pl-9 pr-4 py-2 text-sm text-stone-900
                       placeholder-stone-400 focus:outline-none focus:ring-2 focus:ring-stone-400 w-72"
          />
        </div>
        <select
          value={filterMat}
          onChange={(e) => setFilterMat(e.target.value)}
          className="border border-stone-300 rounded-lg px-3 py-2 text-stone-900 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-stone-400"
        >
          <option value="">All Materials</option>
          {(categories.materials || []).map((m: Category) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
      </div>

      <div className="bg-white rounded-xl border border-stone-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm min-w-[960px]">
            <thead className="bg-stone-50 border-b border-stone-200">
              <tr>
                {["Image", "SKU", "Name", "Material", "Color", "Finish", "Style", "Dims", "Status", "Actions"].map((h) => (
                  <th key={h} className="text-left px-3 py-3 text-stone-600 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-100">
              {loading ? (
                <tr><td colSpan={10} className="text-center py-12 text-stone-400">Loading...</td></tr>
              ) : tiles.length === 0 ? (
                <tr><td colSpan={10} className="text-center py-12 text-stone-400">No tiles found</td></tr>
              ) : (
                tiles.map((tile) => (
                  <tr key={tile.id} className="hover:bg-stone-50 transition">
                    <td className="px-3 py-3">
                      <div className="w-12 h-12 rounded-lg overflow-hidden bg-stone-100 border border-stone-200">
                        {tile.images?.[0] ? (
                          <img src={`http://localhost:8000${tile.images[0].image_url}`} alt={tile.name} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-xl">🪨</div>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-3 font-mono text-stone-600 text-xs">
                      <Link href={`/dashboard/tiles/${tile.id}`} className="hover:underline">{tile.sku}</Link>
                    </td>
                    <td className="px-3 py-3 font-medium text-stone-800">
                      <Link href={`/dashboard/tiles/${tile.id}`} className="hover:underline">{tile.name}</Link>
                    </td>
                    <td className="px-3 py-3 text-stone-500 text-xs">{tile.material?.name || "—"}</td>
                    <td className="px-3 py-3 text-stone-500 text-xs">{tile.color_family?.name || "—"}</td>
                    <td className="px-3 py-3 text-stone-500 text-xs">{tile.finish?.name || "—"}</td>
                    <td className="px-3 py-3 text-stone-500 text-xs">{tile.style?.name || "—"}</td>
                    <td className="px-3 py-3 text-stone-500 text-xs font-mono whitespace-nowrap">{dims(tile)}</td>
                    <td className="px-3 py-3">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${tile.is_active ? "bg-green-50 text-green-700" : "bg-red-50 text-red-600"}`}>
                        {tile.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => setEditingTile(tile)}
                          className="text-stone-400 hover:text-stone-700"
                          title="Edit features"
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          onClick={() => deactivate(tile.id, tile.sku)}
                          className="text-red-400 hover:text-red-600"
                          title="Deactivate"
                        >
                          <X size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-3 border-t border-stone-100 text-xs text-stone-400">
          {tiles.length} tiles shown
        </div>
      </div>

      {editingTile && (
        <EditTileModal
          tile={editingTile}
          categories={categories}
          onClose={() => setEditingTile(null)}
          onSaved={() => fetchTiles()}
        />
      )}
    </div>
  );
}
