"use client";
import { useState, useEffect, useCallback, useRef } from "react";

const clientCache = new Map<string, { data: any; time: number }>();

export function usePolling<T>(
  fetcher: () => Promise<T>,
  intervalMs: number = 15000
) {
  const key = fetcher.toString();
  const cached = clientCache.get(key);

  const [data, setData] = useState<T | null>(cached ? cached.data : null);
  const [loading, setLoading] = useState(!cached);
  const [error, setError] = useState<string | null>(null);

  const fetcherRef = useRef(fetcher);
  const inFlightRef = useRef(false);
  const visibleRef = useRef(true);
  fetcherRef.current = fetcher;

  const refresh = useCallback(async () => {
    if (inFlightRef.current) return;
    if (!visibleRef.current) return;

    inFlightRef.current = true;
    try {
      const result = await fetcherRef.current();
      setData(result);
      clientCache.set(key, { data: result, time: Date.now() });
      setError(null);
    } catch (e: any) {
      setError(e.message || "Failed to fetch");
    } finally {
      setLoading(false);
      inFlightRef.current = false;
    }
  }, [key]);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, intervalMs);

    const onVisibility = () => {
      visibleRef.current = !document.hidden;
      if (!document.hidden) refresh();
    };
    document.addEventListener("visibilitychange", onVisibility);

    return () => {
      clearInterval(id);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [refresh, intervalMs]);

  return { data, loading, error, refresh };
}
