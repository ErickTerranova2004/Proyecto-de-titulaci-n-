import { useEffect, useState } from "react";
import { api, sesion } from "./api.js";
import { Alerta, UsuarioContexto } from "./components/comunes.jsx";
import Historial from "./components/Historial.jsx";
import Integraciones from "./components/Integraciones.jsx";
import Login from "./components/Login.jsx";
import Modelos from "./components/Modelos.jsx";
import NuevoAnalisis from "./components/NuevoAnalisis.jsx";
import Panel from "./components/Panel.jsx";

const NOMBRE = "Riesgo de despliegue";
const SUBTITULO = "Inteligencia para decisiones de despliegue";
const PESTANAS = [
  ["panel", "Resumen ejecutivo", "M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z"],
  ["nuevo", "Nuevo análisis", "M12 5v14M5 12h14"],
  ["historial", "Historial", "M12 7v5l3 3M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z"],
  [
    "modelos",
    "Modelos",
    "M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z",
  ],
];
// Solo para el administrador.
const PESTANA_INTEGRACIONES = ["integraciones", "Integraciones", "M9 7H6a5 5 0 0 0 0 10h3M15 7h3a5 5 0 0 1 0 10h-3M8 12h8"];

export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(Boolean(sesion.token()));
  const [vista, setVista] = useState("panel");
  const [modelos, setModelos] = useState([]);

  const cargarUsuario = () =>
    api
      .yo()
      .then(setUsuario)
      .catch(() => setUsuario(null))
      .finally(() => setCargando(false));
  const cargarModelos = () => api.modelos().then(setModelos).catch(() => setModelos([]));

  useEffect(() => {
    if (sesion.token()) cargarUsuario();
  }, []);
  useEffect(() => {
    if (usuario) cargarModelos();
  }, [usuario]);

  if (cargando) return <p className="cargando" role="status">Cargando plataforma…</p>;
  if (!usuario) return <Login alEntrar={cargarUsuario} />;

  const esAdmin = usuario.roles.includes("administrador");

  function salir() {
    sesion.cerrar();
    setUsuario(null);
    setModelos([]);
    setVista("panel");
  }

  return (
    <UsuarioContexto.Provider value={usuario}>
    <div className="app">
      <aside className="lateral">
        <header className="lateral__cabecera">
          <span className="marca__simbolo" aria-hidden="true">RD</span><p className="marca">{NOMBRE}</p>
          <p className="secundario">{SUBTITULO}</p>
        </header>

        <p className="menu__etiqueta">ESPACIO DE TRABAJO</p><nav className="menu" aria-label="Secciones de la plataforma">
          {(esAdmin ? [...PESTANAS, PESTANA_INTEGRACIONES] : PESTANAS).map(([id, texto, icono]) => (
            <button
              key={id}
              type="button"
              className="menu__boton"
              aria-current={vista === id ? "page" : undefined}
              onClick={() => setVista(id)}
            >
              <svg viewBox="0 0 24 24" className="menu__icono" aria-hidden="true"><path d={icono} /></svg>
              {texto}
            </button>
          ))}
        </nav>

        <div className="lateral__usuario">
          <p>
            <strong>{usuario.usuario}</strong>
            <span className="secundario">{usuario.roles.join(", ") || "sin rol"}</span>
          </p>
          <button className="boton boton--secundario boton--pequeno" type="button" onClick={salir}>Cerrar sesión</button>
        </div>
      </aside>

      <div className="principal">
        <header className="barra-superior"><div><span className="barra-superior__seccion">Gestión de riesgo</span><span className="barra-superior__separador" aria-hidden="true">/</span><strong>{[...PESTANAS, PESTANA_INTEGRACIONES].find(([id]) => id === vista)?.[1]}</strong></div><span className="barra-superior__perfil">{usuario.usuario}</span></header><main className="contenido">
          {!usuario.roles.length && (
            <Alerta>Su cuenta no tiene un rol asignado. Contacte al administrador.</Alerta>
          )}
          {vista === "panel" && (
            <Panel modelos={modelos} alNuevoAnalisis={() => setVista("nuevo")} alActualizar={cargarModelos} />
          )}
          {vista === "nuevo" && <NuevoAnalisis modelos={modelos} />}
          {vista === "historial" && <Historial modelos={modelos} />}
          {vista === "modelos" && <Modelos modelos={modelos} esAdmin={esAdmin} alCambiar={cargarModelos} />}
          {vista === "integraciones" && esAdmin && <Integraciones />}
        </main>

      </div>
    </div>
    </UsuarioContexto.Provider>
  );
}

