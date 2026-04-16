import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    coverage: {
      provider: "v8",
      thresholds: { lines: 70, functions: 70, statements: 70, branches: 60 },
      exclude: [
        "node_modules/",
        ".next/",
        "tests/",
        "**/*.config.*",
        "**/sw.ts",
        "app/layout.tsx",
      ],
    },
    exclude: ["node_modules", ".next", "tests/e2e"],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, ".") },
  },
});
