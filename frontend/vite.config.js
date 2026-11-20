import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// En desarrollo, /api y el administrador de Django (/admin y sus estáticos)
// se redirigen al backend.
const BACKEND = "http://127.0.0.1:8000";
// El administrador conserva el Host del navegador: Django compara el Origin
// del formulario de inicio de sesión con ese Host (protección CSRF).
const ADMIN = { target: BACKEND, changeOrigin: false };

// Modo red local: `npx vite --host 0.0.0.0` (o scripts/iniciar_demo.ps1
// -RedLocal). El celular solo habla con Vite (5174); Vite reenvía /api al
// backend en 127.0.0.1:8000, así que el backend no necesita escuchar en la red.
// strictPort: si 5174 está ocupado, Vite falla en vez de cambiar de puerto (el
// enlace del correo y la regla del firewall dependen de ese puerto).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    strictPort: true,
    proxy: { "/api": BACKEND, "/admin": ADMIN, "/static": ADMIN },
  },
});
