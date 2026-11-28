import type { ReactNode } from "react";
import { SiteHeader } from "@/app/site-header";
import { requireUser } from "@/lib/auth";
import { getNotices } from "@/lib/notices";

export const instant = false;

export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const user = await requireUser();
  const notices = await getNotices();
  return (
    <>
      <SiteHeader displayName={user.displayName} notices={notices} />
      {children}
    </>
  );
}
