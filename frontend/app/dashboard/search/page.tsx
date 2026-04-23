"use client";
import { useState, useRef } from "react";
import api from "@/lib/api";
import TileResultCard from "@/components/TileResultCard";
import { Upload, Camera, Loader2 } from "lucide-react";

export default function SearchPage() {
  const [preview, setPreview]   = useState<string | null>(null);
  const [results, setResults]   = useState<any[]>([]);
  const [loading, setLoading]   = useState(false);
  const [searched, setSearched] = useState(false);
  const [responseMs, setResponseMs] = useState<number | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = (file: File) => {
    setPreview(URL.createObjectURL(file));
    setResults([]);
    setSearched(false);
  };

  const handleSearch = async () => {
    if (!fileRef.current?.files?.[0]) return;
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", fileRef.current.files[0]);
      const res = await api.post("/api/search/image?top_k=3", form);
      setResults(res.data.results);
      setResponseMs(res.data.response_time_ms);
      setSearched(true);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Search failed";
      alert(`Search failed: ${JSON.stringify(msg)}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 via-white to-slate-100 p-6 sm:p-10">
      <div className="max-w-6xl mx-auto rounded-3xl bg-white shadow-xl border border-slate-200 p-6 sm:p-8">
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-3">
          Visual Tile Search
        </h1>
        <p className="text-slate-600 text-base sm:text-lg mb-6">
          Upload or snap a photo to find the matching tile in inventory. We've Got This!!!😉 
        </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Upload Panel */}
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5 shadow-inner ring-1 ring-slate-100">
          <div
            onClick={() => fileRef.current?.click()}
            className="border-2 border-dashed border-slate-300 rounded-2xl
                       p-8 md:p-10 text-center cursor-pointer hover:border-cyan-400
                       hover:bg-cyan-50 transition-all duration-300"
          >
            {preview ? (
              <img src={preview} alt="Preview"
                   className="max-h-64 mx-auto rounded-lg object-contain" />
            ) : (
              <div className="text-stone-400">
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
            onChange={(e) => e.target.files?.[0] &&
                             handleFile(e.target.files[0])}
          />

          {preview && (
            <button
              onClick={handleSearch}
              disabled={loading}
              className="mt-4 w-full bg-gradient-to-r from-cyan-600 to-blue-600 text-white py-3 rounded-xl
                         font-semibold tracking-wide hover:from-cyan-500 hover:to-blue-500 active:scale-[0.98]
                         transition duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center
                         justify-center gap-2"
            >
              {loading ? (
                <><Loader2 size={18} className="animate-spin" /> Searching...</>
              ) : (
                <><Camera size={18} /> Find This Tile</>
              )}
            </button>
          )}

          {responseMs && (
            <p className="text-center text-xs text-stone-400 mt-2">
              ⚡ Result in {responseMs}ms
            </p>
          )}
        </div>

        {/* Results Panel */}
        <div>
          {!searched && !loading && (
            <div className="text-center text-stone-400 mt-16">
              <p className="text-5xl mb-3">🔍</p>
              <p>Upload a photo to see matches</p>
            </div>
          )}

          {loading && (
            <div className="text-center text-stone-400 mt-16">
              <Loader2 size={40} className="animate-spin mx-auto mb-3" />
              <p>Analyzing tile...</p>
            </div>
          )}

          {searched && results.length === 0 && (
            <div className="text-center text-stone-400 mt-16">
              <p className="text-5xl mb-3">❌</p>
              <p>No matches found</p>
            </div>
          )}

          {results.length > 0 && (
            <div className="space-y-4">
              <p className="text-sm text-cyan-800 font-semibold tracking-wide">
                Top {results.length} matches found
              </p>
              <div className="rounded-xl bg-gradient-to-r from-cyan-50 to-blue-50 p-4 border border-cyan-100 text-sm font-medium text-cyan-700 shadow-inner">Candidates are ranked by similarity and confidence.</div>
              {results.map((r, i) => (
                <TileResultCard key={r.tile_id} result={r} rank={i} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  </div>
  );
}