import { getCurrentUser } from "@/lib/auth";
import { getDashboardData } from "@/lib/data";

export async function GET() {
  if (!(await getCurrentUser())) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  return Response.json(await getDashboardData(), {
    headers: { "Cache-Control": "private, no-store" },
  });
}
