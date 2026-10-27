import { useEffect, useRef, useState } from "react";
import { api, CLAVE_SESION, sesion, urlAdmin } from "./api.js";
import { Campana, useAsignaciones, VentanaAsignaciones } from "./components/Alarma.jsx";
import AtenderAsignacion from "./components/AtenderAsignacion.jsx";
import { Alerta, UsuarioContexto } from "./components/comunes.jsx";
import Historial from "./components/Historial.jsx";
import Integraciones from "./components/Integraciones.jsx";
import Login from "./components/Login.jsx";
import Modelos from "./components/Modelos.jsx";
import NuevoAnalisis from "./components/NuevoAnalisis.jsx";
import Panel from "./components/Panel.jsx";
import Pendientes from "./components/Pendientes.jsx";
import Usuarios from "./components/Usuarios.jsx";
import Workflows from "./components/Workflows.jsx";
import { NOMBRES_ROL, rolPrincipal, seccionesDe } from "./roles.js";
import { debeReiniciar, escucharSesion } from "./sesion.js";

const NOMBRE = "Riesgo de despliegue";
const SUBTITULO = "Inteligencia para decisiones de despliegue";
// Perfil del panel según el rol (Panel.jsx usa el mismo diseño para todos).
const PERFIL_PANEL = { desarrollador: "desarrollador", lider_tecnico: "lider", administrador: "administrador" };

export default function App() {
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(Boolean(sesion.token()));
  const [vista, setVista] = useState(null);
  const [modelos, setModelos] = useState([]);
  // La ventana de asignaciones sale en cada ingreso hasta pulsar "Más tarde".
  const [ventanaCerrada, setVentanaCerrada] = useState(false);
  const [atendiendo, setAtendiendo] = useState(null);
  const [respuesta, setRespuesta] = useState(null);
  const usuarioRef = useRef(null);
  usuarioRef.current = usuario;

  const rol = usuario ? rolPrincipal(usuario.roles) : null;
  const nombreUsuario = usuario ? usuario.usuario : null;
  // La alarma de asignaciones solo se activa para el desarrollador.
  const alarma = useAsignaciones(rol === "desarrollador");

  function reiniciarVista() {
    setVista(null);
    setVentanaCerrada(false);
    setAtendiendo(null);
    setRespuesta(null);
  }

  const cargarUsuario = () =>
    api
      .yo()
      .then((yo) => {
        setUsuario(yo);
        reiniciarVista();
      })
      .catch(() => setUsuario(null))
      .finally(() => setCargando(false));
  const cargarModelos = () => api.modelos().then(setModelos).catch(() => setModelos([]));

  useEffect(() => {
    if (sesion.token()) cargarUsuario();
  }, []);
  useEffect(() => {
    if (usuario) cargarModelos();
  }, [nombreUsuario]);

  // Si el token de la pestaña cambia (otra pestaña, pestaña duplicada o sesión
  // caducada), la interfaz no puede seguir siendo la del usuario anterior.
  useEffect(() => {
    if (!usuario) return undefined;
    return escucharSesion(window, CLAVE_SESION, () => {
      if (!sesion.token()) {
        setUsuario(null);
        return;
      }
      api
        .yo()
        .then((yo) => {
          if (debeReiniciar(usuarioRef.current, yo)) {
            setUsuario(yo);
            reiniciarVista();
          }
        })
        .catch(() => setUsuario(null));
    });
  }, [Boolean(usuario)]);

  if (cargando) return <p className="cargando" role="status">Cargando plataforma…</p>;
  if (!usuario) return <Login alEntrar={cargarUsuario} />;

  const secciones = seccionesDe(rol);
  // Si la vista elegida no existe para el rol, se vuelve al panel del rol.
  const actual = secciones.find((s) => s.id === vista && !s.enlace) || secciones[0] || null;
  const idActual = actual ? actual.id : null;

  function salir() {
    sesion.cerrar();
    setUsuario(null);
    setModelos([]);
    reiniciarVista();
  }

  function irA(id) {
    setAtendiendo(null);
    if (id !== "nuevo") setRespuesta(null);
    setVista(id);
  }

  function verAsignaciones() {
    setVentanaCerrada(true);
    irA("panel");
    setTimeout(() => {
      const bloque = document.getElementById("mis-asignaciones");
      if (bloque) bloque.scrollIntoView({ behavior: "smooth" });
    }, 0);
  }

  function atender(asignacion) {
    setVentanaCerrada(true);
    setAtendiendo(asignacion);
  }

  function nuevoAnalisisDeRespuesta(asignacion, prediccion) {
    setRespuesta({
      asignacion,
      repositorio: asignacion.repositorio,
      workflow_path: asignacion.workflow_path,
      rama: prediccion ? prediccion.rama : undefined,
    });
    setAtendiendo(null);
    setVista("nuevo");
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
              <a key={id} className="menu__boton" href={urlAdmin(enlace)}>
                <svg viewBox="0 0 24 24" className="menu__icono" aria-hidden="true"><path d={icono} /></svg>
                {texto}
                <span className="solo-lector"> (abre el administrador de Django)</span>
              </a>
            ) : (
              <button
                key={id}
                type="button"
                className="menu__boton"
                aria-current={!atendiendo && idActual === id ? "page" : undefined}
                onClick={() => irA(id)}
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
        <header className="barra-superior"><div><span className="barra-superior__seccion">{rol ? NOMBRES_ROL[rol] : "Gestión de riesgo"}</span><span className="barra-superior__separador" aria-hidden="true">/</span><strong>{atendiendo ? "Atender asignación" : (actual ? actual.texto : "")}</strong></div><div className="panel__acciones">{rol === "desarrollador" && <Campana pendientes={alarma.pendientes} alAbrir={verAsignaciones} />}<span className="barra-superior__perfil">{usuario.usuario}</span></div></header><main className="contenido">
          {!rol && (
            <Alerta>Su cuenta no tiene un rol asignado. Contacte al administrador.</Alerta>
          )}
          {rol === "desarrollador" && !ventanaCerrada && alarma.pendientes.length > 0 && (
            <VentanaAsignaciones alarma={alarma} alAtender={atender} alCerrar={() => setVentanaCerrada(true)} />
          )}
          {atendiendo ? (
            <AtenderAsignacion
              key={atendiendo.id}
              asignacion={atendiendo}
              modelos={modelos}
              alNuevoAnalisis={nuevoAnalisisDeRespuesta}
              alVolver={() => setAtendiendo(null)}
            />
          ) : (
            <>
              {idActual === "panel" && (
                <Panel
                  key={rol}
                  perfil={PERFIL_PANEL[rol]}
                  modelos={modelos}
                  alNuevoAnalisis={rol === "administrador" ? undefined : () => irA("nuevo")}
                  alActualizar={cargarModelos}
                  alarma={rol === "desarrollador" ? alarma : undefined}
                  alAtender={atender}
                />
              )}
              {idActual === "nuevo" && (
                <NuevoAnalisis
                  key={respuesta ? respuesta.asignacion.id : "nuevo"}
                  modelos={modelos}
                  respuesta={respuesta}
                  alResponder={() => alarma.recargar()}
                />
              )}
              {idActual === "pendientes" && <Pendientes modelos={modelos} />}
              {idActual === "historial" && (
                rol === "desarrollador"
                  ? <Historial modelos={modelos} titulo="Mi historial" descripcion="Desarrollador · sus análisis en sus repositorios asignados" mostrarDesarrollador={false} />
                  : <Historial modelos={modelos} titulo="Historial del equipo" descripcion="Líder técnico · análisis de los desarrolladores de sus repositorios asignados" mostrarSeguimiento />
              )}
              {idActual === "usuarios" && <Usuarios />}
              {idActual === "workflows" && <Workflows />}
              {idActual === "modelos" && <Modelos modelos={modelos} esAdmin alCambiar={cargarModelos} />}
              {idActual === "integraciones" && <Integraciones />}
            </>
          )}
        </main>

      </div>
    </div>
    </UsuarioContexto.Provider>
  );
}