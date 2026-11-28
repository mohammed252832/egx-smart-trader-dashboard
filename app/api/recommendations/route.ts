import { getCurrentUser } from "@/lib/auth";
import { getDashboardData } from "@/lib/data";

export async function GET() {
  const user = await getCurrentUser();
  if (!user || user.status !== "approved") {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  return Response.json(await getDashboardData(), {
    headers: { "Cache-Control": "private, no-store" },
  });
}
