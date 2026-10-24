import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, /api y el administrador de Django (/admin y sus estáticos)
// se redirigen al backend.
const BACKEND = "http://127.0.0.1:8000";
// El administrador conserva el Host del navegador: Django compara el Origin
// del formulario de inicio de sesión con ese Host (protección CSRF).
const ADMIN = { target: BACKEND, changeOrigin: false };

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: { "/api": BACKEND, "/admin": ADMIN, "/static": ADMIN },
  },
});
