import { defineConfig } from "vite";
import fs from "fs";
import path from "path";

// Read per-worktree dev port or default to 5173
let port = 5173;
const devPortPath = path.resolve(__dirname, "../.dev-port");
if (fs.existsSync(devPortPath)) {
  const content = fs.readFileSync(devPortPath, "utf-8").trim();
  const parsed = parseInt(content, 10);
  if (!isNaN(parsed)) {
    port = parsed;
  }
}

export default defineConfig({
  root: "./",
  server: {
    port: port,
    strictPort: true,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
