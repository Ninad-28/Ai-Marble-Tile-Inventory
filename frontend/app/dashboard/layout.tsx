"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { isLoggedIn } from "@/lib/auth";
import Sidebar from "@/components/Sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();

  useEffect(() => {
    if (!isLoggedIn()) router.push("/login");
  }, [router]);

  return (
    <div className="flex min-h-screen bg-stone-50">
      <Sidebar />
      <main className="ml-64 flex-1 p-8">{children}</main>
    </div>
  );
}