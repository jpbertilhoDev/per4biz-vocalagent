"use client";

import { useEffect } from "react";
import { AUTH_TOKEN_STORAGE_KEY } from "@/lib/api";

/**
 * On mount, extract `#session=<jwt>` from the URL hash (set by the backend
 * OAuth callback redirect), store it in localStorage, and clean the URL
 * so the token doesn't linger in the address bar.
 *
 * This is the fallback auth transport for browsers that block cross-site
 * cookies (Chrome 3rd-party cookie deprecation 2024+). The cookie is still
 * set server-side — this is a belt-and-suspenders approach. The subsequent
 * API calls send both cookie (if the browser allows) and Authorization
 * header (always).
 */
export function AuthTokenCapture() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const hash = window.location.hash;
    if (!hash || !hash.startsWith("#session=")) return;

    const token = hash.slice("#session=".length);
    if (!token) return;

    try {
      window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    } catch {
      // quota or disabled — fall through; cookie path may still work
    }

    // Strip fragment from URL without reloading or adding to history
    const cleanUrl = window.location.pathname + window.location.search;
    window.history.replaceState(null, "", cleanUrl);
  }, []);

  return null;
}
