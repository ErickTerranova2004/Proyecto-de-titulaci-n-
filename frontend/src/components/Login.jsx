import { useState } from "react";
import { api, sesion } from "../api.js";
import { Alerta } from "./comunes.jsx";

export default function Login({ alEntrar }) {
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
        </section>
      </div>
    </div>
  );
}


