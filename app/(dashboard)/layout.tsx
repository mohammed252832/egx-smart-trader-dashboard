import type { ReactNode } from "react";
import { SiteHeader } from "@/app/site-header";
import { requireUser } from "@/lib/auth";

export const instant = false;

export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const user = await requireUser();
  return (
    <>
      <SiteHeader displayName={user.displayName} />
      {children}
    </>
  );
}
