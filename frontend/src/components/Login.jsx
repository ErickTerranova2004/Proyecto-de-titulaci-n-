import { useState } from "react";
import { api, sesion } from "../api.js";
import { Alerta } from "./comunes.jsx";

export default function Login({ alEntrar }) {
  const [usuario, setUsuario] = useState("");
  const [clave, setClave] = useState("");
  const [error, setError] = useState("");

  async function enviar(e) {
    e.preventDefault();
    setError("");
    try {
      const { token } = await api.login(usuario, clave);
      sesion.guardar(token);
      alEntrar();
    } catch {
      setError("Usuario o contraseña incorrectos.");
    }
  }

  return (
    <section className="tarjeta login" aria-labelledby="titulo-login">
      <h1 id="titulo-login">Iniciar sesión</h1>
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
        <div>
          <button className="boton" type="submit">Entrar</button>
        </div>
      </form>
    </section>
  );
}
