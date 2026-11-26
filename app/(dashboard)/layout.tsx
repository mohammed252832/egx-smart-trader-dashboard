import type { ReactNode } from "react";
import { Sidebar } from "@/app/sidebar";
import { requireUser } from "@/lib/auth";

export const instant = false;

export default async function DashboardLayout({ children }: { children: ReactNode }) {
  const user = await requireUser();
  return (
    <>
      <Sidebar email={user.email} />
      {children}
    </>
  );
}
