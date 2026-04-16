"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";

const THRESHOLD = 80;
const MAX_PULL = 150;

/**
 * Lightweight pull-to-refresh gesture.
 *
 * Pure touch events (no external lib) to keep the PWA bundle small and
 * avoid runtime deps for a single gesture. Activates only when the page
 * is scrolled to the top and the user pulls down past THRESHOLD pixels.
 */
export function PullToRefresh({
  onRefresh,
  children,
}: {
  onRefresh: () => Promise<void> | void;
  children: ReactNode;
}) {
  const startY = useRef<number | null>(null);
  const [pullDistance, setPullDistance] = useState(0);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const handleTouchStart = (e: TouchEvent) => {
      if (window.scrollY === 0) {
        startY.current = e.touches[0].clientY;
      }
    };
    const handleTouchMove = (e: TouchEvent) => {
      if (startY.current === null) return;
      const delta = e.touches[0].clientY - startY.current;
      if (delta > 0 && window.scrollY === 0) {
        if (e.cancelable) e.preventDefault();
        setPullDistance(Math.min(delta, MAX_PULL));
      }
    };
    const handleTouchEnd = async () => {
      if (pullDistance >= THRESHOLD && !refreshing) {
        setRefreshing(true);
        try {
          await onRefresh();
        } finally {
          setRefreshing(false);
        }
      }
      startY.current = null;
      setPullDistance(0);
    };

    window.addEventListener("touchstart", handleTouchStart, { passive: true });
    window.addEventListener("touchmove", handleTouchMove, { passive: false });
    window.addEventListener("touchend", handleTouchEnd);
    return () => {
      window.removeEventListener("touchstart", handleTouchStart);
      window.removeEventListener("touchmove", handleTouchMove);
      window.removeEventListener("touchend", handleTouchEnd);
    };
  }, [pullDistance, refreshing, onRefresh]);

  const indicatorVisible = pullDistance > 0 || refreshing;
  const opacity = Math.min(pullDistance / THRESHOLD, 1);

  return (
    <>
      {indicatorVisible && (
        <div
          aria-live="polite"
          role="status"
          className="pointer-events-none fixed inset-x-0 top-0 z-20 flex justify-center py-2"
          style={{ transform: `translateY(${Math.min(pullDistance, THRESHOLD)}px)` }}
        >
          <div
            className="h-6 w-6 rounded-full border-2 border-[#0A84FF] border-t-transparent"
            style={{
              opacity,
              animation: refreshing ? "spin 0.8s linear infinite" : "none",
            }}
          />
        </div>
      )}
      {children}
    </>
  );
}

export default PullToRefresh;
