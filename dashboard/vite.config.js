import { defineConfig, loadEnv } from "vite";
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

export default defineConfig(({ mode }) => {
  // Load env variables from repository root and dashboard directory
  const rootDir = path.resolve(__dirname, "..");
  const env = { ...process.env, ...loadEnv(mode, rootDir, "") };
  const cartoApiKey = env.CARTO_API_KEY || env.VITE_CARTO_API_KEY || "";

  return {
    root: "./",
    server: {
      port: port,
      strictPort: true,
    },
    build: {
      outDir: "dist",
      emptyOutDir: true,
    },
    define: {
      __CARTO_KEY__: JSON.stringify(cartoApiKey),
    },
  };
});
