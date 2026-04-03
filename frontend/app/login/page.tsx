"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { setToken } from "@/lib/auth";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await api.post("/api/auth/login", { email, password });
      setToken(res.data.access_token);
      router.push("/dashboard");
    } catch {
      setError("Invalid email or password");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-stone-100 flex items-center justify-center">
      <div className="bg-white rounded-2xl shadow-lg p-10 w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">🪨</div>
          <h1 className="text-2xl font-bold text-stone-800">Marble AI</h1>
          <p className="text-stone-500 text-sm mt-1">
            Inventory & Visual Search System
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleLogin} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">
              Email
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-4 py-2.5
                         focus:outline-none focus:ring-2 focus:ring-stone-400"
              placeholder="admin@marble.com"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-stone-700 mb-1">
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-stone-300 rounded-lg px-4 py-2.5
                         focus:outline-none focus:ring-2 focus:ring-stone-400"
              placeholder="••••••••"
              required
            />
          </div>

          {error && (
            <p className="text-red-500 text-sm text-center">{error}</p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-stone-800 text-white py-2.5 rounded-lg
                       font-medium hover:bg-stone-700 transition disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </div>
    </div>
  );
}