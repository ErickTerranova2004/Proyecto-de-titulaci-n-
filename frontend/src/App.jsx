import { useEffect, useState } from "react";
import { api, sesion, urlAdmin } from "./api.js";
import { AvisoAsignaciones, Campana, useAsignaciones } from "./components/Alarma.jsx";
import { Alerta, UsuarioContexto } from "./components/comunes.jsx";
import Historial from "./components/Historial.jsx";
import Integraciones from "./components/Integraciones.jsx";
import Login from "./components/Login.jsx";
import Modelos from "./components/Modelos.jsx";
import NuevoAnalisis from "./components/NuevoAnalisis.jsx";
import Panel from "./components/Panel.jsx";
import Pendientes from "./components/Pendientes.jsx";
import { NOMBRES_ROL, rolPrincipal, seccionesDe } from "./roles.js";

const NOMBRE = "Riesgo de despliegue";
const SUBTITULO = "Inteligencia para decisiones de despliegue";
// Perfil del panel según el rol (Panel.jsx usa el mismo diseño para todos).
const PERFIL_PANEL = { desarrollador: "desarrollador", lider_tecnico: "lider", administrador: "administrador" };

export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(Boolean(sesion.token()));
  const [vista, setVista] = useState(null);
  const [modelos, setModelos] = useState([]);
  const [avisoCerrado, setAvisoCerrado] = useState(false);

  const rol = usuario ? rolPrincipal(usuario.roles) : null;
  // La alarma de asignaciones solo se activa para el desarrollador.
  const alarma = useAsignaciones(rol === "desarrollador");

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

  const secciones = seccionesDe(rol);
  // Si la vista elegida no existe para el rol, se vuelve al panel del rol.
  const actual = secciones.find((s) => s.id === vista && !s.enlace) ?? secciones[0] ?? null;

  function salir() {
    sesion.cerrar();
    setUsuario(null);
    setModelos([]);
    setVista(null);
    setAvisoCerrado(false);
  }

  function verAsignaciones() {
    setAvisoCerrado(true);
    setVista("panel");
    setTimeout(() => document.getElementById("mis-asignaciones")?.scrollIntoView({ behavior: "smooth" }), 0);
  }

  return (
    <UsuarioContexto.Provider value={usuario}>
    <div className="app">
      <aside className="lateral">
        <header className="lateral__cabecera">
          <span className="marca__simbolo" aria-hidden="true">RD</span><p className="marca">{NOMBRE}</p>
          <p className="secundario">{SUBTITULO}</p>
        </header>

        <p className="menu__etiqueta">ESPACIO DE TRABAJO</p><nav className="menu" aria-label={rol ? `Secciones del perfil ${NOMBRES_ROL[rol]}` : "Secciones de la plataforma"}>
          {secciones.map(({ id, texto, icono, enlace }) =>
            enlace ? (
              <a key={id} className="menu__boton" href={urlAdmin(enlace)} target="_blank" rel="noopener noreferrer">
                <svg viewBox="0 0 24 24" className="menu__icono" aria-hidden="true"><path d={icono} /></svg>
                {texto}
                <span className="solo-lector"> (abre el administrador de Django en una pestaña nueva)</span>
              </a>
            ) : (
              <button
                key={id}
                type="button"
                className="menu__boton"
                aria-current={actual?.id === id ? "page" : undefined}
                onClick={() => setVista(id)}
              >
                <svg viewBox="0 0 24 24" className="menu__icono" aria-hidden="true"><path d={icono} /></svg>
                {texto}
              </button>
            ),
          )}
        </nav>

        <div className="lateral__usuario">
          <p>
            <strong>{usuario.usuario}</strong>
            <span className="secundario">{rol ? NOMBRES_ROL[rol] : "sin rol"}</span>
          </p>
          <button className="boton boton--secundario boton--pequeno" type="button" onClick={salir}>Cerrar sesión</button>
        </div>
      </aside>

      <div className="principal">
        <header className="barra-superior"><div><span className="barra-superior__seccion">{rol ? NOMBRES_ROL[rol] : "Gestión de riesgo"}</span><span className="barra-superior__separador" aria-hidden="true">/</span><strong>{actual?.texto}</strong></div><div className="panel__acciones">{rol === "desarrollador" && <Campana pendientes={alarma.pendientes} alAbrir={verAsignaciones} />}<span className="barra-superior__perfil">{usuario.usuario}</span></div></header><main className="contenido">
          {!rol && (
            <Alerta>Su cuenta no tiene un rol asignado. Contacte al administrador.</Alerta>
          )}
          {rol === "desarrollador" && !avisoCerrado && (
            <AvisoAsignaciones pendientes={alarma.pendientes} alVer={verAsignaciones} alCerrar={() => setAvisoCerrado(true)} />
          )}
          {actual?.id === "panel" && (
            <Panel
              key={rol}
              perfil={PERFIL_PANEL[rol]}
              modelos={modelos}
              alNuevoAnalisis={rol === "administrador" ? undefined : () => setVista("nuevo")}
              alActualizar={cargarModelos}
              alarma={rol === "desarrollador" ? alarma : undefined}
            />
          )}
          {actual?.id === "nuevo" && <NuevoAnalisis modelos={modelos} />}
          {actual?.id === "pendientes" && <Pendientes modelos={modelos} />}
          {actual?.id === "historial" && (
            rol === "desarrollador"
              ? <Historial modelos={modelos} titulo="Mi historial" descripcion="Desarrollador · sus análisis en sus repositorios asignados" mostrarDesarrollador={false} />
              : <Historial modelos={modelos} titulo="Historial del equipo" descripcion="Líder técnico · análisis de los desarrolladores de sus repositorios asignados" mostrarSeguimiento />
          )}
          {actual?.id === "modelos" && <Modelos modelos={modelos} esAdmin alCambiar={cargarModelos} />}
          {actual?.id === "integraciones" && <Integraciones />}
        </main>

      </div>
    </div>
    </UsuarioContexto.Provider>
  );
}
