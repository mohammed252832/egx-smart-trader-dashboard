"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { BrandMark } from "./brand-mark";

const items = [
  { href: "/", label: "الرئيسية", icon: "home" },
  { href: "/market", label: "آخر تحديث للسوق", icon: "market" },
  { href: "/charts", label: "الرسوم الشهرية", icon: "chart" },
  { href: "/account", label: "حسابي", icon: "user" },
] as const;

function Icon({ name }: { name: (typeof items)[number]["icon"] }) {
  if (name === "home") return <path d="m3 11 9-8 9 8v9a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z" />;
  if (name === "market") return <><path d="M4 20V10" /><path d="M10 20V4" /><path d="M16 20v-7" /><path d="M22 20V7" /></>;
  if (name === "chart") return <><path d="M3 3v18h18" /><path d="m6 15 4-4 4 3 6-8" /></>;
  return <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>;
}

export function SiteHeader({ displayName }: { displayName: string }) {
  const pathname = usePathname();
  const [openPath, setOpenPath] = useState<string | null>(null);
  const open = openPath === pathname;

  return (
    <header dir="rtl" className="sticky top-0 z-50 border-b border-line bg-card/95 backdrop-blur print:hidden">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-5 py-3 sm:px-8">
        <Link href="/" className="flex items-center gap-3">
          <BrandMark />
          <span>
            <span className="block text-lg font-bold leading-tight">EGX Smart Trader</span>
            <span className="block text-xs text-muted">البورصة المصرية</span>
          </span>
        </Link>

        <div className="relative flex items-center gap-2">
          <span className="hidden text-sm text-muted sm:inline">{displayName}</span>
          <form action="/auth/logout" method="post">
            <button type="submit" className="btn-quiet !px-3" aria-label="تسجيل الخروج" title="تسجيل الخروج">
              <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M10 17l5-5-5-5" /><path d="M15 12H3" /><path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5" />
              </svg>
            </button>
          </form>
          <button
            type="button"
            onClick={() => setOpenPath(open ? null : pathname)}
            aria-expanded={open}
            aria-controls="main-navigation"
            className="btn-quiet"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            القائمة
          </button>

          {open && (
            <nav
              id="main-navigation"
              aria-label="القائمة الرئيسية"
              className="card absolute end-0 top-full mt-2 w-72 p-2 shadow-lg"
            >
              {items.map((item) => {
                const active = item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-semibold transition ${active ? "bg-brand-soft text-brand" : "text-ink hover:bg-brand-soft"}`}
                  >
                    <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <Icon name={item.icon} />
                    </svg>
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          )}
        </div>
      </div>
    </header>
  );
}
