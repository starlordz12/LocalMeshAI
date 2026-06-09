import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// LocalMeshAI frontend dev/build config.
// The backend base URL is read at runtime from VITE_API_BASE (see .env.example);
// nothing is hardcoded to an absolute path.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    // three.js + drei are inherently large; split them out and lift the warning threshold.
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks: {
          three: ["three"],
          r3f: ["@react-three/fiber", "@react-three/drei"],
        },
      },
    },
  },
});
