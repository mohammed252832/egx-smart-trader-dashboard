"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import type { DataNotice } from "@/lib/types";
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

export function SiteHeader({ displayName, notices }: { displayName: string; notices: DataNotice[] }) {
  const pathname = usePathname();
  // A panel is tied to the page it was opened on, so navigating closes it.
  const [panel, setPanel] = useState<{ path: string; kind: "menu" | "bell" } | null>(null);
  const current = panel?.path === pathname ? panel.kind : null;
  const open = current === "menu";
  const bellOpen = current === "bell";
  const toggle = (kind: "menu" | "bell") => setPanel(current === kind ? null : { path: pathname, kind });

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setPanel(null);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, []);

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
          <button
            type="button"
            onClick={() => toggle("bell")}
            aria-expanded={bellOpen}
            aria-controls="notices-panel"
            className="btn-quiet relative !px-3"
            aria-label={notices.length ? `التنبيهات (${notices.length})` : "التنبيهات"}
            title="التنبيهات"
          >
            <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" /><path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
            </svg>
            {notices.length > 0 && (
              <span className={`absolute -top-1 -start-1 flex h-5 min-w-5 items-center justify-center rounded-full px-1 text-[11px] font-bold text-white ${notices.some((n) => n.level === "error") ? "bg-down" : "bg-warn"}`}>
                {notices.length}
              </span>
            )}
          </button>
          <form action="/auth/logout" method="post">
            <button type="submit" className="btn-quiet !px-3" aria-label="تسجيل الخروج" title="تسجيل الخروج">
              <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M10 17l5-5-5-5" /><path d="M15 12H3" /><path d="M14 3h5a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-5" />
              </svg>
            </button>
          </form>
          <button
            type="button"
            onClick={() => toggle("menu")}
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
          {bellOpen && (
            <section
              id="notices-panel"
              aria-label="التنبيهات"
              className="card absolute end-0 top-full mt-2 max-h-[70vh] w-[min(24rem,calc(100vw-2.5rem))] overflow-y-auto p-3 shadow-lg"
            >
              <h2 className="px-1 pb-2 text-sm font-bold">تنبيهات البيانات</h2>
              {notices.length === 0 ? (
                <p className="rounded-lg bg-up-soft p-3 text-sm text-up">لا توجد تنبيهات. البيانات محدّثة.</p>
              ) : (
                <ul className="space-y-2">
                  {notices.map((notice) => (
                    <li
                      key={notice.id}
                      className={`rounded-lg border p-3 text-sm leading-6 ${notice.level === "error" ? "border-down/30 bg-down-soft text-down" : "border-warn/30 bg-warn-soft text-warn"}`}
                    >
                      <p className="font-bold">{notice.title}</p>
                      <p className="mt-1">{notice.body}</p>
                      {notice.details && (
                        <details className="mt-2">
                          <summary className="cursor-pointer text-xs font-semibold underline-offset-2 hover:underline">التفاصيل التقنية</summary>
                          <p dir="ltr" className="mt-2 break-words text-left text-xs leading-5">{notice.details}</p>
                        </details>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          )}
        </div>
      </div>
    </header>
  );
}
