"use client";
import { useEffect, useState } from "react";
import api from "@/lib/api";
import { Plus, Pencil, X, Check } from "lucide-react";

interface Category { id: number; name: string; }
interface Tile {
  id: number; sku: string; name: string;
  is_active: boolean;
  material?: Category; finish?: Category;
  color_family?: Category; images: any[];
}

export default function TilesPage() {
  const [tiles, setTiles]           = useState<Tile[]>([]);
  const [categories, setCategories] = useState<any>({});
  const [loading, setLoading]       = useState(true);
  const [showForm, setShowForm]     = useState(false);
  const [search, setSearch]         = useState("");
  const [filterMat, setFilterMat]   = useState("");

  // New tile form state
  const [form, setForm] = useState({
    sku: "", name: "", description: "",
    material_id: "", style_id: "", finish_id: "",
    size_format_id: "", application_id: "",
    color_family_id: "", origin_id: "",
    width_cm: "", height_cm: "",
    thickness_cm: "", price_per_sqm: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError]   = useState("");

  // ── Fetch ──────────────────────────────────────────────
  const fetchTiles = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search)    params.append("search", search);
      if (filterMat) params.append("material_id", filterMat);
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
  useEffect(() => { fetchTiles(); }, [search, filterMat]);

  // ── Submit New Tile ────────────────────────────────────
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setFormError("");
    try {
      const payload: any = { ...form };
      // Convert empty strings to null, numbers to int
      Object.keys(payload).forEach((k) => {
        if (payload[k] === "") payload[k] = null;
        else if (
          k.endsWith("_id") || k.endsWith("_cm") ||
          k === "price_per_sqm"
        ) {
          payload[k] = payload[k] ? Number(payload[k]) : null;
        }
      });
      await api.post("/api/tiles/", payload);
      setShowForm(false);
      setForm({
        sku: "", name: "", description: "",
        material_id: "", style_id: "", finish_id: "",
        size_format_id: "", application_id: "",
        color_family_id: "", origin_id: "",
        width_cm: "", height_cm: "",
        thickness_cm: "", price_per_sqm: "",
      });
      fetchTiles();
    } catch (err: any) {
      setFormError(err.response?.data?.detail || "Failed to add tile");
    }
    setSubmitting(false);
  };

  // ── Deactivate ─────────────────────────────────────────
  const deactivate = async (id: number, sku: string) => {
    if (!confirm(`Deactivate ${sku}?`)) return;
    await api.delete(`/api/tiles/${id}`);
    fetchTiles();
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-stone-800">Tile Catalog</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 bg-stone-800 text-white
                     px-4 py-2 rounded-lg text-sm hover:bg-stone-700 transition"
        >
          <Plus size={16} />
          Add New Tile
        </button>
      </div>

      {/* Add Tile Form */}
      {showForm && (
        <div className="bg-white border border-stone-200 rounded-xl
                        p-6 mb-6 shadow-sm">
          <h2 className="font-semibold text-stone-800 mb-4">New Tile</h2>
          <form onSubmit={handleSubmit}>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">

              {/* SKU */}
              <div>
                <label className="text-xs font-medium text-stone-600">
                  SKU *
                </label>
                <input
                  required value={form.sku}
                  onChange={(e) => setForm({ ...form, sku: e.target.value })}
                  placeholder="e.g. CAR-WHT-001"
                  className="w-full border border-stone-300 rounded-lg
                             px-3 py-2 text-sm mt-1 focus:outline-none
                             focus:ring-2 focus:ring-stone-400"
                />
              </div>

              {/* Name */}
              <div className="col-span-2">
                <label className="text-xs font-medium text-stone-600">
                  Name *
                </label>
                <input
                  required value={form.name}
                  onChange={(e) => setForm({ ...form, name: e.target.value })}
                  placeholder="e.g. Carrara White 60x60"
                  className="w-full border border-stone-300 rounded-lg
                             px-3 py-2 text-sm mt-1 focus:outline-none
                             focus:ring-2 focus:ring-stone-400"
                />
              </div>

              {/* Category Dropdowns */}
              {[
                { key: "material_id",    label: "Material *",    data: categories.materials,    required: true },
                { key: "style_id",       label: "Style",         data: categories.styles },
                { key: "finish_id",      label: "Finish",        data: categories.finishes },
                { key: "size_format_id", label: "Size Format",   data: categories.sizes },
                { key: "application_id", label: "Application",   data: categories.applications },
                { key: "color_family_id",label: "Color Family",  data: categories.colors },
                { key: "origin_id",      label: "Origin",        data: categories.origins },
              ].map(({ key, label, data, required }) => (
                <div key={key}>
                  <label className="text-xs font-medium text-stone-600">
                    {label}
                  </label>
                  <select
                    required={required}
                    value={(form as any)[key]}
                    onChange={(e) => setForm({ ...form, [key]: e.target.value })}
                    className="w-full border border-stone-300 rounded-lg
                               px-3 py-2 text-sm mt-1 focus:outline-none
                               focus:ring-2 focus:ring-stone-400 bg-white"
                  >
                    <option value="">-- Select --</option>
                    {(data || []).map((c: Category) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              ))}

              {/* Dimensions */}
              {[
                { key: "width_cm",      label: "Width (cm)" },
                { key: "height_cm",     label: "Height (cm)" },
                { key: "thickness_cm",  label: "Thickness (cm)" },
                { key: "price_per_sqm", label: "Price / sqm" },
              ].map(({ key, label }) => (
                <div key={key}>
                  <label className="text-xs font-medium text-stone-600">
                    {label}
                  </label>
                  <input
                    type="number" step="0.01"
                    value={(form as any)[key]}
                    onChange={(e) =>
                      setForm({ ...form, [key]: e.target.value })
                    }
                    className="w-full border border-stone-300 rounded-lg
                               px-3 py-2 text-sm mt-1 focus:outline-none
                               focus:ring-2 focus:ring-stone-400"
                  />
                </div>
              ))}

              {/* Description */}
              <div className="col-span-2 md:col-span-3">
                <label className="text-xs font-medium text-stone-600">
                  Description
                </label>
                <textarea
                  value={form.description}
                  onChange={(e) =>
                    setForm({ ...form, description: e.target.value })
                  }
                  rows={2}
                  className="w-full border border-stone-300 rounded-lg
                             px-3 py-2 text-sm mt-1 focus:outline-none
                             focus:ring-2 focus:ring-stone-400"
                />
              </div>
            </div>

            {formError && (
              <p className="text-red-500 text-sm mt-3">{formError}</p>
            )}

            <div className="flex gap-3 mt-4">
              <button
                type="submit" disabled={submitting}
                className="bg-stone-800 text-white px-5 py-2 rounded-lg
                           text-sm font-medium hover:bg-stone-700
                           disabled:opacity-50 transition"
              >
                {submitting ? "Saving..." : "Save Tile"}
              </button>
              <button
                type="button" onClick={() => setShowForm(false)}
                className="border border-stone-300 px-5 py-2 rounded-lg
                           text-sm text-stone-600 hover:bg-stone-50 transition"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-4">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or SKU..."
          className="border border-stone-300 rounded-lg px-4 py-2
                     text-sm focus:outline-none focus:ring-2
                     focus:ring-stone-400 w-64"
        />
        <select
          value={filterMat}
          onChange={(e) => setFilterMat(e.target.value)}
          className="border border-stone-300 rounded-lg px-3 py-2
                     text-sm bg-white focus:outline-none
                     focus:ring-2 focus:ring-stone-400"
        >
          <option value="">All Materials</option>
          {(categories.materials || []).map((m: Category) => (
            <option key={m.id} value={m.id}>{m.name}</option>
          ))}
        </select>
      </div>

      {/* Tile Table */}
      <div className="bg-white rounded-xl border border-stone-200 shadow-sm overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-stone-50 border-b border-stone-200">
            <tr>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Image
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                SKU
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Name
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Material
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Finish
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Status
              </th>
              <th className="text-left px-4 py-3 text-stone-600 font-medium">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stone-100">
            {loading ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-stone-400">
                  Loading...
                </td>
              </tr>
            ) : tiles.length === 0 ? (
              <tr>
                <td colSpan={7} className="text-center py-12 text-stone-400">
                  No tiles found
                </td>
              </tr>
            ) : (
              tiles.map((tile) => (
                <tr key={tile.id} className="hover:bg-stone-50 transition">
                  {/* Thumbnail */}
                  <td className="px-4 py-3">
                    <div className="w-12 h-12 rounded-lg overflow-hidden
                                    bg-stone-100 border border-stone-200">
                      {tile.images?.[0] ? (
                        <img
                          src={`http://localhost:8000${tile.images[0].image_url}`}
                          alt={tile.name}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center
                                        justify-center text-xl">🪨</div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3 font-mono text-stone-600">
                    {tile.sku}
                  </td>
                  <td className="px-4 py-3 font-medium text-stone-800">
                    {tile.name}
                  </td>
                  <td className="px-4 py-3 text-stone-500">
                    {tile.material?.name || "—"}
                  </td>
                  <td className="px-4 py-3 text-stone-500">
                    {tile.finish?.name || "—"}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium
                      ${tile.is_active
                        ? "bg-green-50 text-green-700"
                        : "bg-red-50 text-red-600"
                      }`}>
                      {tile.is_active ? "Active" : "Inactive"}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() => deactivate(tile.id, tile.sku)}
                      className="text-red-400 hover:text-red-600 transition"
                      title="Deactivate"
                    >
                      <X size={16} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Footer count */}
        <div className="px-4 py-3 border-t border-stone-100
                        text-xs text-stone-400">
          {tiles.length} tiles shown
        </div>
      </div>
    </div>
  );
}