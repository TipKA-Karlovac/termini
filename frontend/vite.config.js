import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// U razvoju Vite prosljeđuje /api na Django, pa preglednik sve vidi kao jednu
// adresu i kolačići prijave rade bez CORS-a.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": process.env.API_URL || "http://127.0.0.1:8000",
    },
  },
});
