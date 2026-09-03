"use client";
import { useState } from "react";
import api from "@/lib/api";
import { FileText, Plus, Trash2, Download, Calculator } from "lucide-react";

interface QuoteItem {
  tile_name: string;
  material: string;
  sku: string;
  quantity: number;
  length_cm: number;
  width_cm: number;
  price_per_sqm: number;
}

const MATERIAL_PRICES: Record<string, number> = {
  "Marble": 45.0,
  "Granite": 65.0,
  "Quartzite": 95.0,
  "Travertine": 55.0,
  "Limestone": 50.0,
  "Onyx": 150.0,
  "Slate": 40.0,
  "Porcelain": 30.0,
  "Ceramic": 25.0,
  "string": 35.0,
};

export default function QuotationsPage() {
  const [clientName, setClientName] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [items, setItems] = useState<QuoteItem[]>([
    {
      tile_name: "Carrara White Slab",
      material: "Marble",
      sku: "CAR-WHT-001",
      quantity: 50,
      length_cm: 60,
      width_cm: 60,
      price_per_sqm: 45.0,
    },
  ]);
  const [loading, setLoading] = useState(false);

  const addItem = () => {
    setItems([
      ...items,
      {
        tile_name: "",
        material: "Marble",
        sku: "",
        quantity: 10,
        length_cm: 60,
        width_cm: 60,
        price_per_sqm: 45.0,
      },
    ]);
  };

  const removeItem = (index: number) => {
    setItems(items.filter((_, i) => i !== index));
  };

  const updateItem = (index: number, field: keyof QuoteItem, value: any) => {
    const updated = [...items];
    if (field === "material") {
      updated[index].material = value;
      updated[index].price_per_sqm = MATERIAL_PRICES[value] || 50.0;
    } else {
      updated[index] = { ...updated[index], [field]: value };
    }
    setItems(updated);
  };

  const calculateItemTotals = (item: QuoteItem) => {
    const areaPerPiece = (item.length_cm * item.width_cm) / 10000.0;
    const totalSqm = areaPerPiece * item.quantity;
    const baseTotal = totalSqm * item.price_per_sqm;
    return { totalSqm, baseTotal };
  };

  const subtotal = items.reduce(
    (acc, curr) => acc + calculateItemTotals(curr).baseTotal,
    0
  );
  const gst = subtotal * 0.18;
  const grandTotal = subtotal + gst;

  const handleDownloadPDF = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await api.post(
        "/api/quotations/generate-pdf",
        { client_name: clientName, company_name: companyName, items },
        { responseType: "blob" }
      );

      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `quote_₹{companyName || "client"}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (err) {
      console.error("Failed to generate PDF quotation", err);
    }
    setLoading(false);
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <FileText className="w-8 h-8 text-stone-700" />
        <div>
          <h1 className="text-2xl font-bold text-stone-800">
            Industrial B2B Quotation Builder
          </h1>
          <p className="text-xs text-stone-500">
          Material-based pricing, automatic area (m²) & 18% GST calculation
          </p>
        </div>
      </div>

      <form
        onSubmit={handleDownloadPDF}
        className="bg-white rounded-xl border border-stone-200 p-6 shadow-sm space-y-6"
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-stone-600 uppercase mb-1">
              Client Contact Name
            </label>
            <input
              type="text"
              required
              value={clientName}
              onChange={(e) => setClientName(e.target.value)}
              placeholder="e.g., Rajesh Sharma"
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm text-stone-900 bg-white"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-stone-600 uppercase mb-1">
              Company / Project Name
            </label>
            <input
              type="text"
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="e.g., Apex Builders Ltd."
              className="w-full border border-stone-300 rounded-lg px-3 py-2 text-sm text-stone-900 bg-white"
            />
          </div>
        </div>

        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-stone-700 text-sm uppercase tracking-wider">
              Selected Materials & Slabs
            </h3>
            <button
              type="button"
              onClick={addItem}
              className="flex items-center gap-1 text-xs bg-stone-100 hover:bg-stone-200 text-stone-700 px-3 py-1.5 rounded-lg transition font-medium"
            >
              <Plus size={14} /> Add Slab Item
            </button>
          </div>

          <div className="space-y-3">
            {items.map((item, idx) => {
              const { totalSqm, baseTotal } = calculateItemTotals(item);
              return (
                <div
                  key={idx}
                  className="grid grid-cols-12 gap-2 bg-stone-50 p-3.5 rounded-lg border border-stone-200 items-center text-xs"
                >
                  <div className="col-span-3">
                    <label className="block text-[10px] text-stone-500 font-medium mb-0.5">
                      Material Type
                    </label>
                    <select
                      value={item.material}
                      onChange={(e) => updateItem(idx, "material", e.target.value)}
                      className="w-full border border-stone-300 rounded px-2 py-1 text-xs text-stone-900 bg-white"
                    >
                      {Object.keys(MATERIAL_PRICES).map((mat) => (
                        <option key={mat} value={mat}>{mat}</option>
                      ))}
                    </select>
                  </div>

                  <div className="col-span-2">
                    <label className="block text-[10px] text-stone-500 font-medium mb-0.5">
                      Tile / Slab Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g., Carrara"
                      value={item.tile_name}
                      onChange={(e) => updateItem(idx, "tile_name", e.target.value)}
                      className="w-full border border-stone-300 rounded px-2 py-1 text-xs text-stone-900 bg-white"
                      required
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="block text-[10px] text-stone-500 font-medium mb-0.5">
                      SKU
                    </label>
                    <input
                      type="text"
                      placeholder="SKU-101"
                      value={item.sku}
                      onChange={(e) => updateItem(idx, "sku", e.target.value)}
                      className="w-full border border-stone-300 rounded px-2 py-1 text-xs text-stone-900 bg-white font-mono"
                      required
                    />
                  </div>

                  <div className="col-span-1">
                    <label className="block text-[10px] text-stone-500 font-medium mb-0.5">
                      Qty
                    </label>
                    <input
                      type="number"
                      min="1"
                      value={item.quantity}
                      onChange={(e) => updateItem(idx, "quantity", Number(e.target.value))}
                      className="w-full border border-stone-300 rounded px-2 py-1 text-xs text-stone-900 bg-white"
                      required
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="block text-[10px] text-stone-500 font-medium mb-0.5">
                      Rate/m² (₹)
                    </label>
                    <input
                      type="number"
                      min="0"
                      step="0.1"
                      value={item.price_per_sqm}
                      onChange={(e) => updateItem(idx, "price_per_sqm", Number(e.target.value))}
                      className="w-full border border-stone-300 rounded px-2 py-1 text-xs text-stone-900 bg-white font-semibold"
                      required
                    />
                  </div>

                  <div className="col-span-1 text-right">
                    <label className="block text-[10px] text-stone-500 font-medium mb-0.5">
                      Area
                    </label>
                    <span className="font-semibold text-stone-700">
                      {totalSqm.toFixed(1)} m²
                    </span>
                  </div>

                  <div className="col-span-1 flex justify-end">
                    <button
                      type="button"
                      onClick={() => removeItem(idx)}
                      disabled={items.length === 1}
                      className="text-stone-400 hover:text-red-600 p-1 disabled:opacity-20 mt-3"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Summary Card */}
        <div className="bg-stone-50 rounded-lg p-4 border border-stone-200 flex flex-col sm:flex-row justify-between items-end gap-4">
          <div className="flex items-center gap-2 text-stone-500 text-xs">
            <Calculator size={16} />
            <span>Includes 18% standard industrial tax assessment.</span>
          </div>
          <div className="w-full sm:w-64 space-y-1.5 text-right text-xs">
            <div className="flex justify-between text-stone-600">
              <span>Base Subtotal:</span>
              <span className="font-semibold font-mono">₹{subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between text-stone-600">
              <span>GST (18%):</span>
              <span className="font-semibold font-mono text-amber-700">
                ₹{gst.toFixed(2)}
              </span>
            </div>
            <div className="border-t border-stone-300 pt-1.5 flex justify-between text-sm font-bold text-stone-900">
              <span>Grand Total:</span>
              <span className="font-mono text-base">₹{grandTotal.toFixed(2)}</span>
            </div>
          </div>
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-stone-900 hover:bg-stone-800 text-white font-medium py-3 rounded-lg transition flex items-center justify-center gap-2 text-sm disabled:opacity-50"
        >
          <Download size={16} />
          {loading ? "Generating PDF..." : "Download Official Tax Quotation PDF"}
        </button>
      </form>
    </div>
  );
}