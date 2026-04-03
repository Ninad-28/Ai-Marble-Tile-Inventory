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
      const res = await api.post("/api/search/image", form);
      setResults(res.data.results);
      setResponseMs(res.data.response_time_ms);
      setSearched(true);
    } catch {
      alert("Search failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold text-stone-800 mb-2">
        Visual Tile Search
      </h1>
      <p className="text-stone-500 text-sm mb-6">
        Upload or snap a photo to find the matching tile in inventory
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Upload Panel */}
        <div>
          <div
            onClick={() => fileRef.current?.click()}
            className="border-2 border-dashed border-stone-300 rounded-2xl
                       p-10 text-center cursor-pointer hover:border-stone-500
                       hover:bg-stone-50 transition"
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
              className="mt-4 w-full bg-stone-800 text-white py-3 rounded-xl
                         font-medium hover:bg-stone-700 transition
                         disabled:opacity-50 flex items-center
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
              <p className="text-sm text-stone-500 font-medium">
                Top {results.length} matches found
              </p>
              {results.map((r, i) => (
                <TileResultCard key={r.tile_id} result={r} rank={i} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}