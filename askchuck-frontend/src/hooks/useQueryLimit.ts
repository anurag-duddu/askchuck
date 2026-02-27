import { useState, useCallback, useEffect } from "react";
import { User } from "firebase/auth";

const FREE_LIMIT = parseInt(
  process.env.NEXT_PUBLIC_FREE_QUERY_LIMIT || "5",
  10
);
const STORAGE_KEY = "askchuck_anon_count";

interface QueryLimitResult {
  canQuery: boolean;
  queriesUsed: number;
  queriesLeft: number;
  increment: () => void;
  reset: () => void;
}

export function useQueryLimit(user: User | null): QueryLimitResult {
  const [queriesUsed, setQueriesUsed] = useState<number>(0);

  // Hydrate from localStorage on mount (client-side only)
  useEffect(() => {
    if (typeof window !== "undefined") {
      const stored = parseInt(localStorage.getItem(STORAGE_KEY) || "0", 10);
      setQueriesUsed(isNaN(stored) ? 0 : stored);
    }
  }, []);

  const increment = useCallback(() => {
    if (typeof window === "undefined") return;
    setQueriesUsed((prev) => {
      const next = prev + 1;
      localStorage.setItem(STORAGE_KEY, String(next));
      return next;
    });
  }, []);

  const reset = useCallback(() => {
    if (typeof window === "undefined") return;
    localStorage.removeItem(STORAGE_KEY);
    setQueriesUsed(0);
  }, []);

  // Authenticated users always have access
  if (user !== null) {
    return {
      canQuery: true,
      queriesUsed,
      queriesLeft: Infinity,
      increment,
      reset,
    };
  }

  const queriesLeft = Math.max(0, FREE_LIMIT - queriesUsed);

  return {
    canQuery: queriesLeft > 0,
    queriesUsed,
    queriesLeft,
    increment,
    reset,
  };
}
