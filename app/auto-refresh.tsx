"use client";

import { useEffect } from "react";

export function AutoRefresh() {
  useEffect(() => {
    const interval = window.setInterval(() => {
      if (document.visibilityState === "visible") window.location.reload();
    }, 600_000);
    return () => window.clearInterval(interval);
  }, []);

  return null;
}
