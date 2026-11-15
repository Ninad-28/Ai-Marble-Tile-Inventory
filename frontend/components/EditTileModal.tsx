"use client";
import { useEffect, useState } from "react";
import api, { apiErrorMessage } from "@/lib/api";
import { X } from "lucide-react";

export type Category = { id: number; name: string };

export type EditableTile = {
  id: number;
  sku: string;
  name: string;
  description?: string | null;
  material_id: number;
  style_id?: number | null;
  finish_id?: number | null;
  size_format_id?: number | null;
  application_id?: number | null;
  color_family_id?: number | null;
  origin_id?: number | null;
  width_cm?: number | null;
  height_cm?: number | null;
  thickness_cm?: number | null;
  price_per_sqm?: number | null;
  material?: Category | null;
  style?: Category | null;
  finish?: Category | null;
  size_format?: Category | null;
  application?: Category | null;
  color_family?: Category | null;
  origin?: Category | null;
};

type Categories = {
  materials?: Category[];
  styles?: Category[];
  finishes?: Category[];
  sizes?: Category[];
  applications?: Category[];
  colors?: Category[];
  origins?: Category[];
};

type FormState = {
  name: string;
  description: string;
  material_id: string;
  style_id: string;
  finish_id: string;
  size_format_id: string;
  application_id: string;
  color_family_id: string;
  origin_id: string;
  width_cm: string;
  height_cm: string;
  thickness_cm: string;
  price_per_sqm: string;
};

function tileToForm(tile: EditableTile): FormState {
  const id = (v?: number | null) => (v != null ? String(v) : "");
  const num = (v?: number | null) => (v != null ? String(v) : "");
  return {
    name: tile.name || "",
    description: tile.description || "",
    material_id: id(tile.material_id ?? tile.material?.id),
    style_id: id(tile.style_id ?? tile.style?.id),
    finish_id: id(tile.finish_id ?? tile.finish?.id),
    size_format_id: id(tile.size_format_id ?? tile.size_format?.id),
    application_id: id(tile.application_id ?? tile.application?.id),
    color_family_id: id(tile.color_family_id ?? tile.color_family?.id),
    origin_id: id(tile.origin_id ?? tile.origin?.id),
    width_cm: num(tile.width_cm),
    height_cm: num(tile.height_cm),
    thickness_cm: num(tile.thickness_cm),
    price_per_sqm: num(tile.price_per_sqm),
  };
}

type Props = {
  tile: EditableTile;
  categories: Categories;
  onClose: () => void;
  onSaved: (updated: EditableTile) => void;
};

export default function EditTileModal({ tile, categories, onClose, onSaved }: Props) {
  const [form, setForm] = useState<FormState>(() => tileToForm(tile));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    setForm(tileToForm(tile));
  }, [tile]);

  const set = (key: keyof FormState, value: string) =>
    setForm((prev) => ({ ...prev, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError("");
    try {
      const payload: Record<string, unknown> = {
        name: form.name.trim(),
        description: form.description.trim() || null,
        material_id: Number(form.material_id),
        style_id: form.style_id ? Number(form.style_id) : null,
        finish_id: form.finish_id ? Number(form.finish_id) : null,
        size_format_id: form.size_format_id ? Number(form.size_format_id) : null,
        application_id: form.application_id ? Number(form.application_id) : null,
        color_family_id: form.color_family_id ? Number(form.color_family_id) : null,
        origin_id: form.origin_id ? Number(form.origin_id) : null,
        width_cm: form.width_cm ? Number(form.width_cm) : null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
        thickness_cm: form.thickness_cm ? Number(form.thickness_cm) : null,
        price_per_sqm: form.price_per_sqm ? Number(form.price_per_sqm) : null,
      };
      const res = await api.put(`/api/tiles/${tile.id}`, payload);
      onSaved(res.data);
      onClose();
    } catch (err) {
      setError(apiErrorMessage(err, "Failed to update tile"));
    } finally {
      setSaving(false);
    }
  };

  const selects: { key: keyof FormState; label: string; data?: Category[]; required?: boolean }[] = [
    { key: "material_id", label: "Material *", data: categories.materials, required: true },
    { key: "style_id", label: "Style", data: categories.styles },
    { key: "finish_id", label: "Finish", data: categories.finishes },
    { key: "size_format_id", label: "Size Format", data: categories.sizes },
    { key: "application_id", label: "Application", data: categories.applications },
    { key: "color_family_id", label: "Color", data: categories.colors },
    { key: "origin_id", label: "Origin", data: categories.origins },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 py-4 border-b border-stone-200 sticky top-0 bg-white">
          <div>
            <h2 className="font-semibold text-stone-800 text-lg">Edit Tile</h2>
            <p className="text-xs text-stone-500 font-mono mt-0.5">{tile.sku}</p>
          </div>
          <button type="button" onClick={onClose} className="text-stone-400 hover:text-stone-700">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="text-xs font-medium text-stone-600">Name *</label>
            <input
              required
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm mt-1 text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-400"
            />
          </div>

          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {selects.map(({ key, label, data, required }) => (
              <div key={key}>
                <label className="text-xs font-medium text-stone-600">{label}</label>
                <select
                  required={required}
                  value={form[key]}
                  onChange={(e) => set(key, e.target.value)}
                  className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm mt-1 text-stone-900 bg-white focus:outline-none focus:ring-2 focus:ring-stone-400"
                >
                  <option value="">-- Select --</option>
                  {(data || []).map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {(
              [
                ["width_cm", "Width (cm)"],
                ["height_cm", "Height (cm)"],
                ["thickness_cm", "Thickness (cm)"],
                ["price_per_sqm", "Price / sqm"],
              ] as [keyof FormState, string][]
            ).map(([key, label]) => (
              <div key={key}>
                <label className="text-xs font-medium text-stone-600">{label}</label>
                <input
                  type="number"
                  step="0.01"
                  value={form[key]}
                  onChange={(e) => set(key, e.target.value)}
                  className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm mt-1 text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-400"
                />
              </div>
            ))}
          </div>

          <div>
            <label className="text-xs font-medium text-stone-600">Description</label>
            <textarea
              rows={2}
              value={form.description}
              onChange={(e) => set("description", e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm mt-1 text-stone-900 focus:outline-none focus:ring-2 focus:ring-stone-400"
            />
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <div className="flex gap-3 pt-2">
            <button
              type="submit"
              disabled={saving}
              className="bg-stone-800 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-stone-700 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save Changes"}
            </button>
            <button
              type="button"
              onClick={onClose}
              className="border border-stone-300 px-5 py-2 rounded-lg text-sm text-stone-600 hover:bg-stone-50"
            >
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
