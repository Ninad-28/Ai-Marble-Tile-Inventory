"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { Search, Package, LayoutDashboard, LogOut, Boxes } from "lucide-react";
import { removeToken } from "@/lib/auth";
import api from "@/lib/api";

const links = [
  { href: "/dashboard",           label: "Dashboard",  icon: LayoutDashboard },
  { href: "/dashboard/search",    label: "Search Tile", icon: Search },
  { href: "/dashboard/tiles",     label: "Tiles",       icon: Boxes },
  { href: "/dashboard/inventory", label: "Inventory",   icon: Package },
];

export default function Sidebar() {
  const pathname = usePathname();
  const router   = useRouter();

  const handleLogout = async () => {
    try { await api.post("/api/auth/logout"); } catch {}
    removeToken();
    router.push("/login");
  };

  return (
    <aside className="w-64 bg-stone-900 text-white min-h-screen
                      flex flex-col fixed left-0 top-0">
      {/* Logo */}
      <div className="p-6 border-b border-stone-700">
        <div className="flex items-center gap-3">
          <span className="text-2xl">🪨</span>
          <div>
            <p className="font-bold text-white">Marble AI</p>
            <p className="text-xs text-stone-400">Admin Panel</p>
          </div>
        </div>
      </div>

      {/* Nav Links */}
      <nav className="flex-1 p-4 space-y-1">
        {links.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg
                          text-sm font-medium transition
                          ${active
                            ? "bg-stone-700 text-white"
                            : "text-stone-400 hover:bg-stone-800 hover:text-white"
                          }`}
            >
              <Icon size={18} />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Logout */}
      <div className="p-4 border-t border-stone-700">
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-4 py-2.5 rounded-lg
                     text-sm text-stone-400 hover:text-white
                     hover:bg-stone-800 w-full transition"
        >
          <LogOut size={18} />
          Logout
        </button>
      </div>
    </aside>
  );
}