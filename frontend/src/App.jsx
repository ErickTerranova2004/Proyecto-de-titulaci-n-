import { useEffect, useRef, useState } from "react";
import { api, CLAVE_SESION, sesion, urlAdmin } from "./api.js";
import { Campana, useAsignaciones, VentanaAsignaciones } from "./components/Alarma.jsx";
import AnalisisDetalle from "./components/AnalisisDetalle.jsx";
import AtenderAsignacion from "./components/AtenderAsignacion.jsx";
import { AbrirInformeContexto, Alerta, UsuarioContexto } from "./components/comunes.jsx";
import Historial from "./components/Historial.jsx";
import InformeDetalle from "./components/InformeDetalle.jsx";
import InformesRecibidos from "./components/InformesRecibidos.jsx";
import Integraciones from "./components/Integraciones.jsx";
import Login from "./components/Login.jsx";
import Modelos from "./components/Modelos.jsx";
import NuevoAnalisis from "./components/NuevoAnalisis.jsx";
import Panel from "./components/Panel.jsx";
import Pendientes from "./components/Pendientes.jsx";
import Planificador from "./components/Planificador.jsx";
import Restablecer, { enlaceRestablecer } from "./components/Restablecer.jsx";
import Usuarios from "./components/Usuarios.jsx";
import Workflows from "./components/Workflows.jsx";
import { LimiteErrores } from "./limiteErrores.js";
import { Enlace, NavegacionContexto, useNavegacion, useRuta } from "./navegacion.jsx";
import { NOMBRES_ROL, rolPrincipal, seccionesDe } from "./roles.js";
import { interpretarRuta, redireccion, rutaDe, seccionActiva } from "./rutas.js";
import { debeReiniciar, escucharSesion } from "./sesion.js";

const NOMBRE = "Riesgo de despliegue";
const SUBTITULO = "Inteligencia para decisiones de despliegue";
// Perfil del panel según el rol (Panel.jsx usa el mismo diseño para todos).
const PERFIL_PANEL = { desarrollador: "desarrollador", lider_tecnico: "lider", administrador: "administrador" };

// Cada pantalla tiene su dirección (src/rutas.js). La del enlace del correo
// (/restablecer/<uid>/<token>) es pública: se muestra con o sin sesión.
export default function App() {
  const navegacion = useRuta();
  const enlace = enlaceRestablecer(navegacion.ruta.pathname);
  return (
    <NavegacionContexto.Provider value={navegacion}>
      {enlace ? <Restablecer uid={enlace.uid} token={enlace.token} /> : <Plataforma />}
    </NavegacionContexto.Provider>
  );
}

function Plataforma() {
  const { ruta, navegar } = useNavegacion();
  const [usuario, setUsuario] = useState(null);
  const [cargando, setCargando] = useState(Boolean(sesion.token()));
  const [modelos, setModelos] = useState([]);
  // La ventana de asignaciones sale en cada ingreso hasta pulsar "Más tarde".
  const [ventanaCerrada, setVentanaCerrada] = useState(false);
  // Vistas internas sin dirección propia: se cierran al navegar.
  const [atendiendo, setAtendiendo] = useState(null);
  const [respuesta, setRespuesta] = useState(null);
  // Último «Nuevo análisis» terminado: el Planificador lo preselecciona.
  const [ultimoAnalisis, setUltimoAnalisis] = useState(null);
  const usuarioRef = useRef(null);
  usuarioRef.current = usuario;

  const rol = usuario ? rolPrincipal(usuario.roles) : null;
  const nombreUsuario = usuario ? usuario.usuario : null;
  // La alarma de asignaciones solo se activa para el desarrollador.
  const alarma = useAsignaciones(rol === "desarrollador");
  const destino = interpretarRuta(ruta.pathname, ruta.search);

  function reiniciarVista() {
    setVentanaCerrada(false);
    setAtendiendo(null);
    setRespuesta(null);
    setUltimoAnalisis(null);
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

  // Atrás/adelante o cualquier navegación cierra «Atender asignación» y, al
  // salir de «Nuevo análisis», la respuesta a una asignación.
  useEffect(() => {
    setAtendiendo(null);
    if (destino.seccion !== "nuevo") setRespuesta(null);
  }, [ruta.pathname]);

  const secciones = usuario ? seccionesDe(rol) : [];
  const permitidas = secciones.filter((s) => !s.enlace).map((s) => s.id);
  // "/", dirección desconocida, sección sin permiso o enlace antiguo del
  // correo: se reemplaza la dirección (atrás no vuelve a la incorrecta).
  const otra = usuario ? redireccion(destino, permitidas) : null;
  useEffect(() => {
    if (otra) navegar(otra, { reemplazar: true });
  }, [otra]);

  if (cargando) return <p className="cargando" role="status">Cargando plataforma…</p>;
  // Sin sesión: el inicio de sesión en la misma dirección; al entrar se
  // muestra la pantalla pedida (o el panel si el rol no la tiene).
  if (!usuario) return <Login alEntrar={cargarUsuario} />;
  if (otra) return <p className="cargando" role="status">Cargando…</p>;

  const activa = seccionActiva(destino);
  const actual = secciones.find((s) => s.id === activa) || null;
  const titulo = destino.tipo === "analisis" ? `Análisis #${destino.id}`
    : destino.tipo === "informe" ? "Informe de cumplimiento"
      : atendiendo ? "Atender asignación" : (actual ? actual.texto : "");

  function salir() {
    sesion.cerrar();
    setUsuario(null);
    setModelos([]);
    reiniciarVista();
  }

  // Menú: el Planificador abre el último análisis si lo hay.
  function rutaMenu(id) {
    if (id === "planificador" && ultimoAnalisis) return `${rutaDe(id)}?analisis=${ultimoAnalisis.id}`;
    return rutaDe(id);
  }

  function verAsignaciones() {
    setVentanaCerrada(true);
    navegar(rutaDe("panel"));
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
    navegar(rutaDe("nuevo"));
  }

  const abrirInforme = (id) => navegar(`/informes/${id}`);
  const idPlanificador = Number(new URLSearchParams(ruta.search).get("analisis")) || null;

  let contenido;
  if (atendiendo) {
    contenido = (
      <AtenderAsignacion
        key={atendiendo.id}
        asignacion={atendiendo}
        modelos={modelos}
        alNuevoAnalisis={nuevoAnalisisDeRespuesta}
        alVolver={() => setAtendiendo(null)}
      />
    );
  } else if (destino.tipo === "analisis") {
    contenido = <AnalisisDetalle key={destino.id} id={destino.id} modelos={modelos} />;
  } else if (destino.tipo === "informe") {
    contenido = <InformeDetalle key={destino.id} id={destino.id} />;
  } else {
    const s = destino.seccion;
    contenido = (
      <>
        {s === "panel" && (
          <Panel
            key={rol}
            perfil={PERFIL_PANEL[rol]}
            modelos={modelos}
            alNuevoAnalisis={rol === "administrador" ? undefined : () => navegar(rutaDe("nuevo"))}
            alActualizar={cargarModelos}
            alarma={rol === "desarrollador" ? alarma : undefined}
            alAtender={atender}
          />
        )}
        {s === "nuevo" && (
          <NuevoAnalisis
            key={respuesta ? respuesta.asignacion.id : "nuevo"}
            modelos={modelos}
            respuesta={respuesta}
            alResponder={() => alarma.recargar()}
            alAnalizar={setUltimoAnalisis}
            alPlanificar={
              permitidas.includes("planificador")
                ? (prediccion) => {
                  setUltimoAnalisis(prediccion);
                  navegar(`${rutaDe("planificador")}?analisis=${prediccion.id}`);
                }
                : undefined
            }
          />
        )}
        {s === "planificador" && (
          <Planificador key={idPlanificador ?? "sin-analisis"} analisisId={idPlanificador} inicial={ultimoAnalisis} />
        )}
        {s === "pendientes" && <Pendientes />}
        {s === "historial" && (
          rol === "desarrollador"
            ? <Historial titulo="Mi historial" descripcion="Desarrollador · sus análisis en sus repositorios asignados" mostrarDesarrollador={false} />
            : rol === "administrador"
              ? <Historial titulo="Historial de análisis" descripcion="Administrador · análisis de todos los repositorios" mostrarSeguimiento conOrigen conNivel />
              : <Historial titulo="Historial del equipo" descripcion="Líder técnico · análisis de los desarrolladores de sus repositorios asignados" mostrarSeguimiento conNivel />
        )}
        {s === "informes" && (
          rol === "administrador"
            ? <InformesRecibidos titulo="Informes de cumplimiento" descripcion="Administrador · informes de todos los desarrolladores y líderes" mostrarLider />
            : <InformesRecibidos titulo="Informes recibidos" descripcion="Líder técnico · informes de cumplimiento de sus indicaciones, del más reciente al más antiguo" />
        )}
        {s === "usuarios" && <Usuarios />}
        {s === "workflows" && <Workflows />}
        {s === "modelos" && <Modelos modelos={modelos} esAdmin alCambiar={cargarModelos} />}
        {s === "integraciones" && <Integraciones />}
      </>
    );
  }

  return (
    <UsuarioContexto.Provider value={usuario}>
    <AbrirInformeContexto.Provider value={abrirInforme}>
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
              <Enlace
                key={id}
                href={rutaMenu(id)}
                className="menu__boton"
                aria-current={!atendiendo && destino.tipo === "seccion" && activa === id ? "page" : undefined}
                alNavegar={() => setAtendiendo(null)}
              >
                <svg viewBox="0 0 24 24" className="menu__icono" aria-hidden="true"><path d={icono} /></svg>
                {texto}
              </Enlace>
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
        <header className="barra-superior"><div><span className="barra-superior__seccion">{rol ? NOMBRES_ROL[rol] : "Gestión de riesgo"}</span><span className="barra-superior__separador" aria-hidden="true">/</span><strong>{titulo}</strong></div><div className="panel__acciones">{rol === "desarrollador" && <Campana pendientes={alarma.pendientes} alAbrir={verAsignaciones} />}<span className="barra-superior__perfil">{usuario.usuario}</span></div></header><main className="contenido">
          {!rol && (
            <Alerta>Su cuenta no tiene un rol asignado. Contacte al administrador.</Alerta>
          )}
          {rol === "desarrollador" && !ventanaCerrada && alarma.pendientes.length > 0 && (
            <VentanaAsignaciones alarma={alarma} alAtender={atender} alCerrar={() => setVentanaCerrada(true)} />
          )}
          <LimiteErrores claveReinicio={atendiendo ? `atender-${atendiendo.id}` : `${ruta.pathname}${ruta.search}`}>
            {contenido}
          </LimiteErrores>
        </main>

      </div>
    </div>
    </AbrirInformeContexto.Provider>
    </UsuarioContexto.Provider>
  );
}
