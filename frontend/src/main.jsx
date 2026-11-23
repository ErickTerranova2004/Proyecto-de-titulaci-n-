import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { LimiteErrores } from "./limiteErrores.js";
import "./styles/tokens.css";
import "./styles/base.css";

// Último recurso: si falla algo fuera de las secciones (menú, inicio de
// sesión), se muestra el aviso en vez de una página en blanco.
createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <LimiteErrores titulo="La plataforma tuvo un error inesperado.">
      <App />
    </LimiteErrores>
  </React.StrictMode>
);
