import { useEffect, useMemo, useState } from "react";
import { api } from "../api.js";
import { NOMBRES_ROL } from "../roles.js";
import { Alerta, Fecha } from "./comunes.jsx";
import { Aviso, Dialogo, Filtros, Indicador } from "./gestion.jsx";

// Gestión de cuentas: rol, estado, contraseña y repositorios asignados.
// Los permisos reales los aplica el backend (views_gestion.py).

const ROLES = ["administrador", "lider_tecnico", "desarrollador"];
// Roles que solo ven los repositorios que se les asignan.
const CON_ACCESOS = ["lider_tecnico", "desarrollador"];
const FILTROS = [
  ["todos", "Todos"],
  ["administrador", "Administradores"],
  ["lider_tecnico", "Líderes técnicos"],
  ["desarrollador", "Desarrolladores"],
  ["sin_rol", "Sin rol"],
  ["inactivos", "Inactivos"],
];

function cumple(u, filtro) {
  if (filtro === "todos") return true;
  if (filtro === "sin_rol") return !u.rol;
  if (filtro === "inactivos") return !u.activo;
  return u.rol === filtro;
}

function textoRepositorios(u) {
  if (u.rol === "administrador") return <span className="secundario">Todos (administrador)</span>;
  if (!u.rol) return <span className="secundario">—</span>;
  const n = u.repositorios.length;
  if (!n) return <span className="gestion-estado gestion-estado--pendiente">Ninguno asignado</span>;
  return `${n} ${n === 1 ? "repositorio" : "repositorios"}`;
}

export default function Usuarios() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState("");
  const [aviso, setAviso] = useState("");
  const [cargando, setCargando] = useState(false);
  const [filtro, setFiltro] = useState("todos");
  const [busqueda, setBusqueda] = useState("");
  const [editando, setEditando] = useState(null);
  const [creando, setCreando] = useState(false);

  function cargar() {
    setCargando(true);
    setError("");
    api
      .gestionUsuarios()
      .then(setDatos)
      .catch((e) => setError(e.message))
      .finally(() => setCargando(false));
  }
  useEffect(cargar, []);

  function avisar(texto) {
    setAviso(texto);
    setTimeout(() => setAviso(""), 3500);
  }

  function reemplazar(u) {
    setDatos((d) => ({
      ...d,
      usuarios: d.usuarios.some((x) => x.id === u.id)
        ? d.usuarios.map((x) => (x.id === u.id ? u : x))
        : [...d.usuarios, u].sort((a, b) => a.usuario.localeCompare(b.usuario)),
    }));
  }

  const usuarios = datos ? datos.usuarios : [];
  const conteos = useMemo(
    () => Object.fromEntries(FILTROS.map(([id]) => [id, usuarios.filter((u) => cumple(u, id)).length])),
    [usuarios],
  );
  const texto = busqueda.trim().toLowerCase();
  const visibles = usuarios.filter(
    (u) =>
      cumple(u, filtro) &&
      (!texto ||
        u.usuario.toLowerCase().includes(texto) ||
        u.correo.toLowerCase().includes(texto) ||
        u.nombre.toLowerCase().includes(texto)),
  );
  const sinRepos = usuarios.filter((u) => CON_ACCESOS.includes(u.rol) && !u.repositorios.length).length;

  return (
    <section className="vista" aria-labelledby="titulo-usuarios">
      <div className="panel__cabecera">
        <div>
          <h1 id="titulo-usuarios">Usuarios y accesos</h1>
          <p className="secundario">Roles, estado de las cuentas y repositorios que puede consultar cada usuario</p>
        </div>
        <div className="panel__acciones">
          <button className="boton boton--secundario" type="button" onClick={cargar} disabled={cargando}>
            {cargando ? "Actualizando…" : "Actualizar"}
          </button>
          <button className="boton" type="button" onClick={() => setCreando(true)} disabled={!datos}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
            Nuevo usuario
          </button>
        </div>
      </div>

      <Alerta>{error}</Alerta>
      <Aviso texto={aviso} />
      {!datos && !error && <p role="status" className="secundario">Cargando usuarios…</p>}

      {datos && (
        <>
          <div className="kpis">
            <Indicador icono="usuarios" titulo="Usuarios" valor={conteos.todos} detalle={`${conteos.inactivos} inactivos`} />
            <Indicador icono="verificado" titulo="Administradores" valor={conteos.administrador} detalle="Acceso total" />
            <Indicador icono="repositorio" titulo="Líderes técnicos" valor={conteos.lider_tecnico} detalle="Deciden despliegues" />
            <Indicador icono="workflows" titulo="Desarrolladores" valor={conteos.desarrollador} detalle="Realizan análisis" />
            <Indicador
              icono="alto"
              titulo="Requieren atención"
              valor={conteos.sin_rol + sinRepos}
              nivel={conteos.sin_rol + sinRepos ? "alto" : undefined}
              detalle={`${conteos.sin_rol} sin rol · ${sinRepos} sin repositorios`}
            />
          </div>

          <section className="tarjeta" aria-labelledby="titulo-cuentas">
            <h2 id="titulo-cuentas">Cuentas registradas</h2>
            <div className="gestion-barra">
              <Filtros opciones={FILTROS} valor={filtro} conteos={conteos} alCambiar={setFiltro} etiqueta="Filtrar por rol o estado" />
              <label className="campo campo--en-linea gestion-buscar">
                <span className="solo-lector">Buscar usuario</span>
                <input
                  type="search"
                  placeholder="Buscar por usuario, nombre o correo"
                  value={busqueda}
                  onChange={(e) => setBusqueda(e.target.value)}
                />
              </label>
            </div>

            {!visibles.length ? (
              <p className="secundario">No hay usuarios que coincidan con el filtro.</p>
            ) : (
              <div className="tabla-contenedor">
                <table>
                  <caption className="solo-lector">Usuarios de la plataforma</caption>
                  <thead>
                    <tr>
                      <th scope="col">Usuario</th>
                      <th scope="col">Rol</th>
                      <th scope="col">Repositorios</th>
                      <th scope="col">Estado</th>
                      <th scope="col">Último acceso</th>
                      <th scope="col"><span className="solo-lector">Acciones</span></th>
                    </tr>
                  </thead>
                  <tbody>
                    {visibles.map((u) => (
                      <tr key={u.id}>
                        <td>
                          <div className="gestion-persona">
                            <span className="gestion-avatar" aria-hidden="true">{u.usuario.slice(0, 2).toUpperCase()}</span>
                            <div>
                              <strong>
                                {u.usuario}
                                {u.es_actual && <span className="gestion-insignia">Usted</span>}
                              </strong>
                              <span className="secundario">{u.correo || "Sin correo"}</span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className={`gestion-insignia gestion-insignia--${u.rol || "sin-rol"}`}>
                            {u.rol ? NOMBRES_ROL[u.rol] : "Sin rol"}
                          </span>
                        </td>
                        <td>{textoRepositorios(u)}</td>
                        <td>
                          <span className={`gestion-estado gestion-estado--${u.activo ? "ok" : "apagado"}`}>
                            {u.activo ? "Activo" : "Inactivo"}
                          </span>
                        </td>
                        <td>{u.ultimo_acceso ? <Fecha valor={u.ultimo_acceso} /> : <span className="secundario">Nunca</span>}</td>
                        <td>
                          <button className="boton boton--secundario boton--pequeno" type="button" onClick={() => setEditando(u)}>
                            Gestionar<span className="solo-lector"> la cuenta de {u.usuario}</span>
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}

      {creando && (
        <DialogoNuevo
          alCerrar={() => setCreando(false)}
          alCrear={(u) => {
            reemplazar(u);
            setCreando(false);
            avisar(`Usuario ${u.usuario} creado.`);
            // Si necesita repositorios, se abre directamente para asignarlos.
            if (CON_ACCESOS.includes(u.rol)) setEditando(u);
          }}
        />
      )}
      {editando && (
        <DialogoUsuario
          usuario={editando}
          repositorios={datos.repositorios}
          alCerrar={() => setEditando(null)}
          alGuardar={(u) => {
            reemplazar(u);
            setEditando(null);
            avisar(`Cambios de ${u.usuario} guardados.`);
          }}
        />
      )}
    </section>
  );
}

function SelectorRol({ valor, alCambiar, deshabilitado }) {
  return (
    <select value={valor} onChange={(e) => alCambiar(e.target.value)} disabled={deshabilitado}>
      <option value="">Sin rol</option>
      {ROLES.map((r) => <option key={r} value={r}>{NOMBRES_ROL[r]}</option>)}
    </select>
  );
}

function DialogoNuevo({ alCerrar, alCrear }) {
  const [form, setForm] = useState({ usuario: "", correo: "", contrasena: "", rol: "desarrollador" });
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);
  const cambiar = (campo) => (e) => setForm({ ...form, [campo]: e.target.value });

  function enviar(e) {
    e.preventDefault();
    setEnviando(true);
    setError("");
    api
      .crearUsuario({ ...form, rol: form.rol || null })
      .then(alCrear)
      .catch((err) => setError(err.message))
      .finally(() => setEnviando(false));
  }

  return (
    <Dialogo titulo="Nuevo usuario" alCerrar={alCerrar}>
      <form onSubmit={enviar}>
        <label className="campo"><span>Nombre de usuario</span>
          <input value={form.usuario} onChange={cambiar("usuario")} required autoFocus autoComplete="off" />
        </label>
        <label className="campo"><span>Correo electrónico</span>
          <input type="email" value={form.correo} onChange={cambiar("correo")} />
        </label>
        <label className="campo"><span>Contraseña inicial</span>
          <input type="password" value={form.contrasena} onChange={cambiar("contrasena")} required autoComplete="new-password" />
        </label>
        <p className="secundario nota-pie">Mínimo 8 caracteres, no solo números ni una contraseña común.</p>
        <label className="campo"><span>Rol</span>
          <SelectorRol valor={form.rol} alCambiar={(rol) => setForm({ ...form, rol })} />
        </label>
        <Alerta>{error}</Alerta>
        <div className="gestion-dialogo__acciones">
          <button type="button" className="boton boton--secundario" onClick={alCerrar}>Cancelar</button>
          <button className="boton" disabled={enviando}>{enviando ? "Creando…" : "Crear usuario"}</button>
        </div>
      </form>
    </Dialogo>
  );
}

function DialogoUsuario({ usuario, repositorios, alCerrar, alGuardar }) {
  const [rol, setRol] = useState(usuario.rol || "");
  const [activo, setActivo] = useState(usuario.activo);
  const [correo, setCorreo] = useState(usuario.correo);
  const [contrasena, setContrasena] = useState("");
  const [asignados, setAsignados] = useState(() => new Set(usuario.repositorios.map((r) => r.id)));
  const [error, setError] = useState("");
  const [guardando, setGuardando] = useState(false);
  const rolBloqueado = usuario.es_actual || usuario.superusuario;

  async function guardar(e) {
    e.preventDefault();
    const cambios = {};
    if ((usuario.rol || "") !== rol) cambios.rol = rol || null;
    if (usuario.activo !== activo) cambios.activo = activo;
    if (usuario.correo !== correo.trim()) cambios.correo = correo.trim();
    if (contrasena) cambios.contrasena = contrasena;
    const antes = usuario.repositorios.map((r) => r.id).sort().join(",");
    const despues = [...asignados].sort().join(",");

    setGuardando(true);
    setError("");
    try {
      let resultado = usuario;
      if (Object.keys(cambios).length) resultado = await api.editarUsuario(usuario.id, cambios);
      if (CON_ACCESOS.includes(rol) && antes !== despues) resultado = await api.accesosUsuario(usuario.id, [...asignados]);
      alGuardar(resultado);
    } catch (err) {
      setError(err.message);
      setGuardando(false);
    }
  }

  return (
    <Dialogo titulo={`Cuenta de ${usuario.usuario}`} alCerrar={alCerrar} ancho={720}>
      <form onSubmit={guardar}>
        <dl className="gestion-datos">
          <dt>Alta</dt><dd><Fecha valor={usuario.alta} /></dd>
          <dt>Último acceso</dt><dd>{usuario.ultimo_acceso ? <Fecha valor={usuario.ultimo_acceso} /> : "Nunca"}</dd>
        </dl>

        <div className="rejilla rejilla--2">
          <label className="campo"><span>Rol</span>
            <SelectorRol valor={rol} alCambiar={setRol} deshabilitado={rolBloqueado} />
          </label>
          <label className="campo"><span>Correo electrónico</span>
            <input type="email" value={correo} onChange={(e) => setCorreo(e.target.value)} />
          </label>
        </div>
        {rolBloqueado && (
          <p className="secundario nota-pie">
            {usuario.superusuario ? "El superusuario siempre es administrador." : "No puede cambiar su propio rol."}
          </p>
        )}

        <label className="gestion-check">
          <input type="checkbox" checked={activo} onChange={(e) => setActivo(e.target.checked)} disabled={usuario.es_actual} />
          <span>Cuenta activa {!activo && "· al guardar se cerrarán sus sesiones abiertas"}</span>
        </label>

        <label className="campo"><span>Nueva contraseña (opcional)</span>
          <input
            type="password"
            value={contrasena}
            onChange={(e) => setContrasena(e.target.value)}
            placeholder="Dejar vacío para no cambiarla"
            autoComplete="new-password"
          />
        </label>

        {CON_ACCESOS.includes(rol) ? (
          <SelectorRepositorios repositorios={repositorios} asignados={asignados} alCambiar={setAsignados} />
        ) : (
          <p className="secundario nota-pie">
            {rol === "administrador"
              ? "El administrador ve todos los repositorios; no necesita asignaciones."
              : "Asigne un rol para poder darle acceso a repositorios."}
          </p>
        )}

        <Alerta>{error}</Alerta>
        <div className="gestion-dialogo__acciones">
          <button type="button" className="boton boton--secundario" onClick={alCerrar}>Cancelar</button>
          <button className="boton" disabled={guardando}>{guardando ? "Guardando…" : "Guardar cambios"}</button>
        </div>
      </form>
    </Dialogo>
  );
}

function SelectorRepositorios({ repositorios, asignados, alCambiar }) {
  const [filtro, setFiltro] = useState("");
  const porId = useMemo(() => Object.fromEntries(repositorios.map((r) => [r.id, r])), [repositorios]);
  const t = filtro.trim().toLowerCase();
  const opciones = repositorios
    .filter((r) => !asignados.has(r.id) && (!t || r.nombre_completo.toLowerCase().includes(t)))
    .slice(0, 40);
  const elegidos = [...asignados]
    .map((id) => porId[id])
    .filter(Boolean)
    .sort((a, b) => a.nombre_completo.localeCompare(b.nombre_completo));

  function alternar(id) {
    const s = new Set(asignados);
    if (s.has(id)) s.delete(id);
    else s.add(id);
    alCambiar(s);
  }

  return (
    <fieldset className="gestion-repos">
      <legend>Repositorios asignados ({asignados.size})</legend>
      {elegidos.length ? (
        <ul className="gestion-etiquetas">
          {elegidos.map((r) => (
            <li key={r.id}>
              {r.nombre_completo}
              <button type="button" onClick={() => alternar(r.id)} aria-label={`Quitar ${r.nombre_completo}`}>×</button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="secundario">Sin repositorios: no podrá realizar ni consultar análisis.</p>
      )}
      <label className="campo"><span>Añadir repositorio</span>
        <input
          type="search"
          value={filtro}
          onChange={(e) => setFiltro(e.target.value)}
          placeholder={`Buscar entre ${repositorios.length} repositorios`}
        />
      </label>
      {opciones.length ? (
        <ul className="gestion-opciones">
          {opciones.map((r) => (
            <li key={r.id}>
              <button type="button" onClick={() => alternar(r.id)}>
                + {r.nombre_completo}
                {r.es_demostracion && <span className="gestion-insignia">demo</span>}
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <p className="secundario">No hay más repositorios que coincidan.</p>
      )}
    </fieldset>
  );
}