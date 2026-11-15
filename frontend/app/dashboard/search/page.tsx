"use client";
import { useState, useRef } from "react";
import api from "@/lib/api";
import TileResultCard from "@/components/TileResultCard";
import { Upload, Camera, Loader2, Crop, RotateCcw, X, Check } from "lucide-react";

type SearchResult = {
  tile_id: number;
  sku: string;
  name: string;
  confidence: number;
  location: { aisle: string | null; rack: string | null; bin: string | null; warehouse?: string; display?: string };
  stock: { quantity: number | null; unit: string; is_low: boolean };
  image_url: string;
  details?: { material?: { name: string }; finish?: { name: string }; style?: { name: string }; width_cm?: number; height_cm?: number; price_per_sqm?: number };
};

type CropBox = { x: number; y: number; w: number; h: number }; // percentages 0..100
type DragMode = "draw" | "move" | "nw" | "ne" | "sw" | "se" | null;

export default function SearchPage() {
  const [originalFile, setOriginalFile] = useState<File | null>(null);
  const [originalUrl, setOriginalUrl] = useState<string | null>(null);
  const [activeFile, setActiveFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [isCropped, setIsCropped] = useState(false);

  // Interactive cursor crop state (in % of image)
  const [cropOpen, setCropOpen] = useState(false);
  const [cropBox, setCropBox] = useState<CropBox>({ x: 10, y: 10, w: 80, h: 80 });
  const [dragMode, setDragMode] = useState<DragMode>(null);
  const dragStartRef = useRef<{ ptrX: number; ptrY: number; box: CropBox }>({
    ptrX: 0,
    ptrY: 0,
    box: { x: 10, y: 10, w: 80, h: 80 },
  });

  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [responseMs, setResponseMs] = useState<number | null>(null);
  const [error, setError] = useState("");

  const fileRef = useRef<HTMLInputElement>(null);
  const cropAreaRef = useRef<HTMLDivElement>(null);
  const cropImgRef = useRef<HTMLImageElement>(null);

  const isGatekeeperFiltered =
    error.toLowerCase().includes("valid marble") ||
    error.toLowerCase().includes("gatekeeper") ||
    error.toLowerCase().includes("not a recognized");

  const resetCropBox = () => setCropBox({ x: 10, y: 10, w: 80, h: 80 });

  const handleFile = (file: File) => {
    const url = URL.createObjectURL(file);
    setOriginalFile(file);
    setOriginalUrl(url);
    setActiveFile(file);
    setPreview(url);
    setIsCropped(false);
    resetCropBox();
    setResults([]);
    setSearched(false);
    setError("");
    setResponseMs(null);
  };

  const clearImage = () => {
    setOriginalFile(null);
    setOriginalUrl(null);
    setActiveFile(null);
    setPreview(null);
    setIsCropped(false);
    setResults([]);
    setSearched(false);
    setError("");
    setResponseMs(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  // Convert pointer clientX/clientY to percentage (0..100) inside image container
  const getPointerPercent = (e: React.PointerEvent) => {
    const rect = cropAreaRef.current?.getBoundingClientRect();
    if (!rect || rect.width === 0 || rect.height === 0) return { px: 0, py: 0 };
    const px = Math.min(100, Math.max(0, ((e.clientX - rect.left) / rect.width) * 100));
    const py = Math.min(100, Math.max(0, ((e.clientY - rect.top) / rect.height) * 100));
    return { px, py };
  };

  const startDrag = (e: React.PointerEvent, mode: DragMode) => {
    e.stopPropagation();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    const { px, py } = getPointerPercent(e);
    setDragMode(mode);
    dragStartRef.current = { ptrX: px, ptrY: py, box: { ...cropBox } };
    if (mode === "draw") {
      setCropBox({ x: px, y: py, w: 0, h: 0 });
    }
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!dragMode) return;
    const { px, py } = getPointerPercent(e);
    const { ptrX, ptrY, box } = dragStartRef.current;
    const dx = px - ptrX;
    const dy = py - ptrY;
    const minSize = 5;

    if (dragMode === "draw") {
      const x = Math.min(ptrX, px);
      const y = Math.min(ptrY, py);
      const w = Math.abs(px - ptrX);
      const h = Math.abs(py - ptrY);
      setCropBox({ x, y, w, h });
    } else if (dragMode === "move") {
      const newX = Math.min(100 - box.w, Math.max(0, box.x + dx));
      const newY = Math.min(100 - box.h, Math.max(0, box.y + dy));
      setCropBox({ ...box, x: newX, y: newY });
    } else if (dragMode === "se") {
      setCropBox({
        ...box,
        w: Math.min(100 - box.x, Math.max(minSize, box.w + dx)),
        h: Math.min(100 - box.y, Math.max(minSize, box.h + dy)),
      });
    } else if (dragMode === "nw") {
      const newX = Math.min(box.x + box.w - minSize, Math.max(0, box.x + dx));
      const newY = Math.min(box.y + box.h - minSize, Math.max(0, box.y + dy));
      setCropBox({
        x: newX,
        y: newY,
        w: box.w + (box.x - newX),
        h: box.h + (box.y - newY),
      });
    } else if (dragMode === "ne") {
      const newY = Math.min(box.y + box.h - minSize, Math.max(0, box.y + dy));
      setCropBox({
        x: box.x,
        y: newY,
        w: Math.min(100 - box.x, Math.max(minSize, box.w + dx)),
        h: box.h + (box.y - newY),
      });
    } else if (dragMode === "sw") {
      const newX = Math.min(box.x + box.w - minSize, Math.max(0, box.x + dx));
      setCropBox({
        x: newX,
        y: box.y,
        w: box.w + (box.x - newX),
        h: Math.min(100 - box.y, Math.max(minSize, box.h + dy)),
      });
    }
  };

  const endDrag = () => {
    if (!dragMode) return;
    // If user clicked without dragging a box, restore previous box
    if (dragMode === "draw" && (cropBox.w < 4 || cropBox.h < 4)) {
      setCropBox(dragStartRef.current.box);
    }
    setDragMode(null);
  };

  const applyCrop = () => {
    const img = cropImgRef.current;
    if (!img || !originalFile) return;

    const srcX = Math.round((cropBox.x / 100) * img.naturalWidth);
    const srcY = Math.round((cropBox.y / 100) * img.naturalHeight);
    const srcW = Math.round((cropBox.w / 100) * img.naturalWidth);
    const srcH = Math.round((cropBox.h / 100) * img.naturalHeight);

    if (srcW <= 5 || srcH <= 5) return;

    const canvas = document.createElement("canvas");
    canvas.width = srcW;
    canvas.height = srcH;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.drawImage(img, srcX, srcY, srcW, srcH, 0, 0, srcW, srcH);

    canvas.toBlob((blob) => {
      if (!blob) return;
      const baseName = originalFile.name.replace(/\.[^/.]+$/, "");
      const croppedFile = new File([blob], `${baseName}_cropped.jpg`, { type: "image/jpeg" });
      setActiveFile(croppedFile);
      setPreview(URL.createObjectURL(blob));
      setIsCropped(true);
      setCropOpen(false);
      setResults([]);
      setSearched(false);
      setError("");
    }, "image/jpeg", 0.95);
  };

  const handleSearch = async () => {
    if (!activeFile) return;
    setLoading(true);
    setError("");
    setSearched(false);
    const startTime = performance.now();
    try {
      const form = new FormData();
      form.append("file", activeFile);
      const res = await api.post("/api/search/image?top_k=3", form);
      const matches = await Promise.all(
        (res.data.results || []).map(async (result: SearchResult) => {
          try {
            const detail = await api.get(`/api/tiles/${result.tile_id}`);
            return {
              ...result,
              details: detail.data,
              stock: detail.data.inventory
                ? {
                    quantity: detail.data.inventory.quantity,
                    unit: detail.data.inventory.unit,
                    is_low: detail.data.low_stock,
                  }
                : { quantity: null, unit: "pieces", is_low: false },
            };
          } catch {
            return result;
          }
        }),
      );
      setResults(matches);
      setResponseMs(res.data.response_time_ms ?? Math.round(performance.now() - startTime));
      setSearched(true);
    } catch (err: unknown) {
      const axiosError = err as { response?: { data?: { detail?: unknown } }; message?: string };
      const msg = axiosError.response?.data?.detail || axiosError.message || "Search failed";
      setResponseMs(Math.round(performance.now() - startTime));
      setError(typeof msg === "string" ? msg : "Search failed. Please try another image.");
    } finally {
      setLoading(false);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="min-h-screen lg:h-screen lg:overflow-hidden bg-gradient-to-b from-slate-50 via-white to-slate-100 p-4 sm:p-6 flex flex-col">
      <div className="max-w-6xl w-full mx-auto flex-1 min-h-0 flex flex-col rounded-3xl bg-white shadow-xl border border-slate-200 p-6 sm:p-8">
        <div className="shrink-0">
          <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-2">
            Visual Tile Search
          </h1>
          <p className="text-slate-600 text-base sm:text-lg mb-5">
            Upload one tile photo, crop it, and search matching products in the current inventory.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 flex-1 min-h-0">
          {/* Upload Panel (Stationary on left) */}
          <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-inner ring-1 ring-slate-100 self-start">
            <div
              onClick={() => fileRef.current?.click()}
              className="border-2 border-dashed border-slate-300 rounded-2xl
                         p-6 md:p-8 text-center cursor-pointer hover:border-cyan-400
                         hover:bg-cyan-50 transition-all duration-300"
            >
              {preview ? (
                <div className="space-y-2">
                  <img
                    src={preview}
                    alt="Preview"
                    className="max-h-52 mx-auto rounded-lg object-contain shadow-sm"
                  />
                  <p className="text-xs font-medium text-cyan-700">Replace photo</p>
                </div>
              ) : (
                <div className="text-stone-400 py-6">
                  <Upload size={40} className="mx-auto mb-3" />
                  <p className="font-medium">Click to upload tile photo</p>
                  <p className="text-xs mt-1">JPG, PNG supported</p>
                </div>
              )}
            </div>

            <input
              ref={fileRef}
              type="file"
              accept="image/*"
              capture="environment"
              className="hidden"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
            />

            {/* Selected File & Crop Bar */}
            {activeFile && preview && (
              <div className="mt-4">
                <div className="flex items-center justify-between rounded-xl bg-white border border-slate-200 p-3 shadow-sm">
                  <div className="flex items-center gap-3 min-w-0">
                    <img
                      src={preview}
                      alt="Thumb"
                      className="w-11 h-11 rounded-lg object-cover border border-slate-200 shrink-0"
                    />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-slate-800 truncate">
                        {originalFile?.name.replace(/\.[^/.]+$/, "")}{" "}
                        {isCropped && <span className="text-cyan-600">(cropped)</span>}
                      </p>
                      <p className="text-xs text-slate-400">{formatFileSize(activeFile.size)}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      type="button"
                      onClick={() => setCropOpen(true)}
                      title="Crop image"
                      className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:text-cyan-700 hover:bg-cyan-50 border border-slate-200 transition inline-flex items-center gap-1.5"
                    >
                      <Crop size={14} /> Crop
                    </button>
                    <button
                      type="button"
                      onClick={clearImage}
                      title="Remove image"
                      className="p-2 rounded-lg text-slate-400 hover:text-red-600 hover:bg-red-50 transition"
                    >
                      <X size={16} />
                    </button>
                  </div>
                </div>

                <p className="text-xs mt-1.5 ml-1">
                  {isCropped ? (
                    <span className="text-emerald-600 font-medium inline-flex items-center gap-1">
                      <Check size={13} /> Crop confirmed
                    </span>
                  ) : (
                    <span className="text-slate-400">Crop is optional before searching.</span>
                  )}
                </p>

                <button
                  onClick={handleSearch}
                  disabled={loading}
                  className="mt-3 w-full bg-gradient-to-r from-cyan-600 to-blue-600 text-white py-3 rounded-xl
                             font-semibold tracking-wide hover:from-cyan-500 hover:to-blue-500 active:scale-[0.98]
                             transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center
                             justify-center gap-2"
                >
                  {loading ? (
                    <><Loader2 size={18} className="animate-spin" /> Analyzing & searching...</>
                  ) : (
                    <><Camera size={18} /> Find This Tile</>
                  )}
                </button>
              </div>
            )}

            {responseMs !== null && (
              <p className="text-center text-xs text-stone-400 mt-2">
                ⚡ Result in {responseMs}ms
              </p>
            )}
          </div>

          {/* Results Panel (Internal scroll for matched tiles) */}
          <div className="flex flex-col min-h-0 h-full">
            {!searched && !loading && !error && (
              <div className="text-center text-stone-400 my-auto py-12">
                <p className="text-5xl mb-3">🔍</p>
                <p>Upload a photo to see matches</p>
              </div>
            )}

            {loading && (
              <div className="text-center text-stone-400 my-auto py-12">
                <Loader2 size={40} className="animate-spin mx-auto mb-3" />
                <p>Analyzing tile...</p>
              </div>
            )}

            {((searched && results.length === 0) || isGatekeeperFiltered) && !loading && (
              <div className="text-center text-stone-400 my-auto max-w-md mx-auto p-6 rounded-2xl bg-stone-50 border border-stone-200 shadow-sm">
                <p className="text-4xl mb-3">🛡️</p>
                <h3 className="text-base font-semibold text-stone-700">MobileNetV3 Gatekeeper Filtered</h3>
                <p className="text-xs text-stone-500 mt-1">
                  Input rejected: Not a recognized marble or stone tile surface. Out-of-distribution images are filtered prior to vector retrieval.
                </p>
              </div>
            )}

            {results.length > 0 && (
              <div className="flex flex-col min-h-0 flex-1">
                {/* Pinned Header inside Results Panel */}
                <div className="shrink-0 space-y-2.5 pb-3">
                  <p className="text-sm text-cyan-800 font-semibold tracking-wide">
                    Top {results.length} matches found
                  </p>
                  <div className="rounded-xl bg-gradient-to-r from-cyan-50 to-blue-50 p-3.5 border border-cyan-100 text-sm font-medium text-cyan-700 shadow-inner">
                    Candidates are ranked by visual similarity.
                  </div>
                </div>

                {/* Scrollable Container for the 3 Tile Cards */}
                <div className="flex-1 min-h-0 overflow-y-auto pr-2 space-y-4">
                  {results.map((r, i) => (
                    <TileResultCard key={r.tile_id} result={r} rank={i} />
                  ))}
                </div>
              </div>
            )}

            {error && !isGatekeeperFiltered && (
              <p className="mt-4 rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">
                {error}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Interactive Cursor Crop Modal */}
      {cropOpen && originalUrl && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-xs p-4">
          <div className="w-full max-w-lg rounded-2xl bg-white shadow-2xl border border-slate-200 p-6">
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-lg font-bold text-slate-900">Crop Tile Surface</h2>
              <button
                type="button"
                onClick={() => setCropOpen(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X size={20} />
              </button>
            </div>
            <p className="text-xs text-slate-500 mb-4">
              Click and drag to select the tile area, or drag the box / corners to adjust.
            </p>

            {/* Interactive Image Stage */}
            <div className="flex justify-center items-center bg-slate-900 rounded-xl p-3 select-none">
              <div
                ref={cropAreaRef}
                onPointerDown={(e) => startDrag(e, "draw")}
                onPointerMove={onPointerMove}
                onPointerUp={endDrag}
                className="relative inline-block overflow-hidden cursor-crosshair touch-none"
              >
                <img
                  ref={cropImgRef}
                  src={originalUrl}
                  alt="Crop target"
                  draggable={false}
                  className="max-h-[360px] max-w-full block select-none pointer-events-none"
                />

                {/* Selection Window (dims outside via box-shadow) */}
                <div
                  onPointerDown={(e) => startDrag(e, "move")}
                  style={{
                    left: `${cropBox.x}%`,
                    top: `${cropBox.y}%`,
                    width: `${cropBox.w}%`,
                    height: `${cropBox.h}%`,
                    boxShadow: "0 0 0 9999px rgba(0, 0, 0, 0.58)",
                  }}
                  className="absolute border-2 border-white cursor-move"
                >
                  {/* Rule of thirds grid */}
                  <div className="absolute inset-0 grid grid-cols-3 grid-rows-3 pointer-events-none">
                    <div className="border-r border-b border-white/30" />
                    <div className="border-r border-b border-white/30" />
                    <div className="border-b border-white/30" />
                    <div className="border-r border-b border-white/30" />
                    <div className="border-r border-b border-white/30" />
                    <div className="border-b border-white/30" />
                    <div className="border-r border-white/30" />
                    <div className="border-r border-white/30" />
                    <div />
                  </div>

                  {/* 4 Corner Resize Handles */}
                  <span
                    onPointerDown={(e) => startDrag(e, "nw")}
                    className="absolute -top-1.5 -left-1.5 w-3.5 h-3.5 bg-white border-2 border-cyan-600 rounded-xs cursor-nwse-resize"
                  />
                  <span
                    onPointerDown={(e) => startDrag(e, "ne")}
                    className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 bg-white border-2 border-cyan-600 rounded-xs cursor-nesw-resize"
                  />
                  <span
                    onPointerDown={(e) => startDrag(e, "sw")}
                    className="absolute -bottom-1.5 -left-1.5 w-3.5 h-3.5 bg-white border-2 border-cyan-600 rounded-xs cursor-nesw-resize"
                  />
                  <span
                    onPointerDown={(e) => startDrag(e, "se")}
                    className="absolute -bottom-1.5 -right-1.5 w-3.5 h-3.5 bg-white border-2 border-cyan-600 rounded-xs cursor-nwse-resize"
                  />
                </div>
              </div>
            </div>

            {/* Footer Controls */}
            <div className="mt-5 flex items-center justify-between">
              <span className="text-xs text-slate-400 font-mono">
                Selection: {Math.round(cropBox.w)}% × {Math.round(cropBox.h)}%
              </span>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={resetCropBox}
                  className="px-3.5 py-2 rounded-lg border border-slate-200 text-slate-700 text-xs font-medium hover:bg-slate-50 inline-flex items-center gap-1.5"
                >
                  <RotateCcw size={13} /> Reset
                </button>
                <button
                  type="button"
                  onClick={() => setCropOpen(false)}
                  className="px-3.5 py-2 rounded-lg border border-slate-200 text-slate-700 text-xs font-medium hover:bg-slate-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={applyCrop}
                  className="px-4 py-2 rounded-lg bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700 shadow-sm"
                >
                  Use This Crop
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}