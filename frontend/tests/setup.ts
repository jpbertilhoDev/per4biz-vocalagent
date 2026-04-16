import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, beforeEach } from "vitest";

// jsdom in this vitest setup exposes `localStorage` as an empty object without
// the Storage API, which breaks zustand's persist middleware. Provide a minimal
// in-memory Storage polyfill so stores using `persist(... localStorage ...)`
// can write/read in tests.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();
  get length() {
    return this.store.size;
  }
  clear() {
    this.store.clear();
  }
  getItem(key: string) {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }
  setItem(key: string, value: string) {
    this.store.set(key, String(value));
  }
  removeItem(key: string) {
    this.store.delete(key);
  }
  key(index: number) {
    return Array.from(this.store.keys())[index] ?? null;
  }
}

if (typeof window !== "undefined") {
  Object.defineProperty(window, "localStorage", {
    value: new MemoryStorage(),
    writable: true,
    configurable: true,
  });
  Object.defineProperty(globalThis, "localStorage", {
    value: window.localStorage,
    writable: true,
    configurable: true,
  });
}

beforeEach(() => {
  if (typeof localStorage !== "undefined") {
    localStorage.clear();
  }
});

afterEach(() => {
  cleanup();
});
