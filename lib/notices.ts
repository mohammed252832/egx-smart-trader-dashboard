import "server-only";

import { cache } from "react";
import { getDashboardData } from "./data";
import type { DataNotice } from "./types";

/** One dashboard read per request, shared by the layout (bell) and the home page. */
export const getDashboardDataOnce = cache(getDashboardData);

/** Data-health notices for the header bell. Never throws: a failure becomes a notice. */
export const getNotices = cache(async (): Promise<DataNotice[]> => {
  try {
    const { isStale, expectedSession, marketRefresh } = await getDashboardDataOnce();
    const notices: DataNotice[] = [];

    if (isStale) {
      notices.push({
        id: "stale",
        level: "warn",
        title: "البيانات أقدم من آخر جلسة",
        body: `البيانات المعروضة أقدم من آخر جلسة متوقعة (${expectedSession ?? "—"}). قد يكون تشغيل التحليل متأخراً أو يوم عطلة؛ تحقق من تبويب Actions.`,
      });
    }

    if (marketRefresh?.last_error) {
      const failed =
        !marketRefresh.last_success_at ||
        Date.parse(marketRefresh.updated_at) > Date.parse(marketRefresh.last_success_at);
      notices.push({
        id: "refresh",
        level: failed ? "error" : "warn",
        title: failed ? "تعذّر آخر تحديث للأسعار" : "اكتمل تحديث الأسعار جزئياً",
        body: failed
          ? "نعرض آخر بيانات ناجحة. تحقق من مصادر الأسعار."
          : "بعض الأسهم لم تصل أسعارها من المصادر، ونعرض آخر بيانات ناجحة لها.",
        details: marketRefresh.last_error,
      });
    }

    return notices;
  } catch (error) {
    console.error("Notices read failed", error);
    return [
      {
        id: "unavailable",
        level: "error",
        title: "تعذّر قراءة حالة البيانات",
        body: "لم نتمكن من التحقق من حداثة البيانات الآن. أعد تحميل الصفحة بعد قليل.",
      },
    ];
  }
});
