"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

const items = [
  { href: "/", label: "الرئيسية", icon: "home" },
  { href: "/market", label: "آخر تحديث للسوق", icon: "market" },
  { href: "/charts", label: "الرسوم الشهرية", icon: "chart" },
] as const;

function Icon({ name }: { name: (typeof items)[number]["icon"] }) {
  if (name === "home") {
    return <path d="m3 11 9-8 9 8v9a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z" />;
  }
  if (name === "market") {
    return <><path d="M4 20V10" /><path d="M10 20V4" /><path d="M16 20v-7" /><path d="M22 20V7" /></>;
  }
  return <><path d="M3 3v18h18" /><path d="m6 15 4-4 4 3 6-8" /></>;
}

export function Sidebar({ email }: { email: string }) {
  const pathname = usePathname();
  const [openPath, setOpenPath] = useState<string | null>(null);
  const open = openPath === pathname;

  return (
    <aside dir="rtl" className="fixed left-5 top-5 z-50 flex flex-col-reverse items-end print:hidden">
      {open && (
        <div id="floating-navigation" className="mt-3 w-72 overflow-hidden rounded-2xl border border-white/10 bg-[#111c30]/95 shadow-2xl shadow-black/50 backdrop-blur">
          <nav className="p-2" aria-label="القائمة الرئيسية">
            {items.map((item) => {
              const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  aria-current={active ? "page" : undefined}
                  className={`flex items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold transition ${active ? "bg-emerald-500/15 text-emerald-300" : "text-gray-300 hover:bg-white/5 hover:text-white"}`}
                >
                  <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-width-1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                    <Icon name={item.icon} />
                  </svg>
                  {item.label}
                </Link>
              );
            })}
          </nav>
          <div className="border-t border-white/10 p-3">
            <p dir="ltr" className="mb-2 truncate px-2 text-left text-xs text-gray-500">{email}</p>
            <form action="/auth/logout" method="post">
              <button type="submit" className="flex w-full items-center gap-3 rounded-xl px-4 py-3 text-sm font-bold text-red-300 transition hover:bg-red-500/10">
                <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-width-1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <path d="M10 17l5-5-5-5" /><path d="M15 12H3" /><path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5" />
                </svg>
                تسجيل الخروج
              </button>
            </form>
          </div>
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpenPath(open ? null : pathname)}
        aria-expanded={open}
        aria-controls="floating-navigation"
        className="flex items-center gap-2 rounded-full border border-emerald-400/30 bg-emerald-500 px-5 py-3 text-sm font-black text-[#07120d] shadow-xl shadow-emerald-950/40 transition hover:bg-emerald-400"
      >
        <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-width-2" strokeLinecap="round" aria-hidden="true">
          <path d="M4 6h16M4 12h16M4 18h16" />
        </svg>
        القائمة
      </button>
    </aside>
  );
}
