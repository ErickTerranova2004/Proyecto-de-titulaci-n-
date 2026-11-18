import { useState } from "react";
import { api, sesion } from "../api.js";
import { Alerta } from "./comunes.jsx";

export default function Login({ alEntrar }) {
  const [olvido, setOlvido] = useState(false);
  const [usuario, setUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      const { token } = await api.login(usuario, clave);
      sesion.guardar(token);
      alEntrar();
    } catch {
      setError("Usuario o contraseña incorrectos.");
    } finally {
      setEnviando(false);
    }
  }

  return (
    <div className="acceso">
      <div className="acceso__tarjeta">
        <section className="acceso__presentacion" aria-label="Presentación de la plataforma">
          <div>
            <span className="acceso__monograma" aria-hidden="true">RD</span><p className="acceso__sello">UNEMI · IA predictiva</p>
            <p className="acceso__titulo">
              Control de riesgo.<br /><span>Supervisión de despliegues.</span>
            </p>
            <p className="secundario">
              Evalúe el riesgo de sus despliegues en GitHub Actions con análisis predictivo, explicación
              de los factores (SHAP) y recomendaciones.
            </p>
          </div>
          <p className="secundario">Plataforma predictiva · Proyecto de titulación 2026</p>
        </section>

        {olvido ? (
          <OlvidoContrasena alVolver={() => setOlvido(false)} />
        ) : (
        <section className="acceso__formulario" aria-labelledby="titulo-login">
          <h1 id="titulo-login">Acceso a la plataforma</h1>
          <p className="secundario">Ingrese sus credenciales para acceder a la plataforma.</p>
          <form className="formulario" onSubmit={enviar}>
            <div className="campo">
              <label htmlFor="login-usuario">Usuario</label>
              <input
                id="login-usuario"
                autoComplete="username"
                value={usuario}
                onChange={(e) => setUsuario(e.target.value)}
                required
              />
            </div>
            <div className="campo">
              <label htmlFor="login-clave">Contraseña</label>
              <input
                id="login-clave"
                type="password"
                autoComplete="current-password"
                value={clave}
                onChange={(e) => setClave(e.target.value)}
                required
              />
            </div>
            <Alerta>{error}</Alerta>
            <button className="boton" type="submit" disabled={enviando}>
              {enviando ? "Iniciando sesión…" : "Iniciar sesión"}
            </button>
          </form>
          <button className="boton-enlace" type="button" onClick={() => setOlvido(true)}>
            ¿Olvidó su contraseña?
          </button>
        </section>
        )}
      </div>
    </div>
  );
}

// Pide el enlace de restablecimiento. La respuesta es la misma exista o no
// una cuenta con ese correo (no se revela qué usuarios existen).
function OlvidoContrasena({ alVolver }) {
  const [correo, setCorreo] = useState("");
  const [respuesta, setRespuesta] = useState(null);
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  async function enviar(e) {
    e.preventDefault();
    setError("");
    setEnviando(true);
    try {
      setRespuesta(await api.olvideContrasena(correo.trim()));
    } catch (err) {
      setError(err.message);
    } finally {
      setEnviando(false);
    }
  }

  return (
    <section className="acceso__formulario" aria-labelledby="titulo-olvido">
      <h1 id="titulo-olvido">¿Olvidó su contraseña?</h1>
      {respuesta ? (
        <>
          <p className="gestion-aviso" role="status">{respuesta.mensaje}</p>
          {!respuesta.correo_configurado && (
            <p className="secundario nota-pie">
              El envío de correos no está configurado en el servidor: el enlace se escribe en la consola del
              servidor. Contacte al administrador.
            </p>
          )}
        </>
      ) : (
        <>
          <p className="secundario">
            Escriba el correo registrado en su cuenta. Le enviaremos un enlace para elegir una contraseña nueva.
          </p>
          <form className="formulario" onSubmit={enviar}>
            <div className="campo">
              <label htmlFor="olvido-correo">Correo electrónico</label>
              <input
                id="olvido-correo"
                type="email"
                autoComplete="email"
                value={correo}
                onChange={(e) => setCorreo(e.target.value)}
                required
                autoFocus
              />
            </div>
            <Alerta>{error}</Alerta>
            <button className="boton" type="submit" disabled={enviando}>
              {enviando ? "Enviando…" : "Enviar enlace"}
            </button>
          </form>
        </>
      )}
      <button className="boton-enlace" type="button" onClick={alVolver}>
        ← Volver al inicio de sesión
      </button>
    </section>
  );
}


