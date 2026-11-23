import { useEffect, useState } from "react";
import { api, sesion } from "../api.js";
import { problemaContrasena } from "../restablecer.js";
import { Alerta } from "./comunes.jsx";

export { enlaceRestablecer } from "../restablecer.js";

// Pantalla pública del enlace del correo: el usuario elige su nueva
// contraseña. El enlace vale una hora y un solo uso (lo comprueba el backend).
export default function Restablecer({ uid, token }) {
  const [estado, setEstado] = useState("validando"); // validando | valido | no_valido | listo
  const [cuenta, setCuenta] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [confirmacion, setConfirmacion] = useState("");
  const [error, setError] = useState("");
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api
      .validarEnlace(uid, token)
      .then((r) => {
        setCuenta(r.usuario);
        setEstado("valido");
      })
      .catch((e) => {
        setError(e.message);
        setEstado("no_valido");
      });
  }, [uid, token]);

  async function enviar(e) {
    e.preventDefault();
    const problema = problemaContrasena(contrasena, confirmacion);
    if (problema) {
      setError(problema);
      return;
    }
    setEnviando(true);
    setError("");
    try {
      await api.restablecerContrasena(uid, token, contrasena, confirmacion);
      // Las sesiones abiertas de la cuenta se cerraron en el backend.
      sesion.cerrar();
      // El token del enlace ya no vale: se quita de la barra de direcciones.
      window.history.replaceState(null, "", "/");
      setEstado("listo");
    } catch (err) {
      setError(err.message);
      if (err.datos?.codigo === "enlace_no_valido") setEstado("no_valido");
    } finally {
      setEnviando(false);
    }
  }

  const irAlInicio = () => window.location.assign("/");

  return (
    <div className="acceso">
      <div className="acceso__tarjeta acceso__tarjeta--simple">
        <section className="acceso__formulario" aria-labelledby="titulo-restablecer">
          <span className="acceso__monograma" aria-hidden="true">RD</span>
          <h1 id="titulo-restablecer">Restablecer contraseña</h1>

          {estado === "validando" && <p role="status" className="secundario">Comprobando el enlace…</p>}

          {estado === "no_valido" && (
            <>
              <Alerta>{error || "El enlace no es válido o ya caducó."}</Alerta>
              <button className="boton" type="button" onClick={irAlInicio}>Ir al inicio de sesión</button>
            </>
          )}

          {estado === "listo" && (
            <>
              <p className="gestion-aviso" role="status">
                Contraseña actualizada. Ya puede iniciar sesión como <strong>{cuenta}</strong> con la nueva contraseña.
              </p>
              <button className="boton" type="button" onClick={irAlInicio}>Iniciar sesión</button>
            </>
          )}

          {estado === "valido" && (
            <>
              <p className="secundario">
                Elija una contraseña nueva para la cuenta <strong>{cuenta}</strong>.
              </p>
              <form className="formulario" onSubmit={enviar} noValidate>
                {/* Para que el gestor de contraseñas la asocie a la cuenta. */}
                <input type="text" autoComplete="username" value={cuenta} readOnly hidden />
                <div className="campo">
                  <label htmlFor="restablecer-clave">Nueva contraseña</label>
                  <input
                    id="restablecer-clave"
                    type="password"
                    autoComplete="new-password"
                    value={contrasena}
                    onChange={(e) => setContrasena(e.target.value)}
                    aria-describedby="restablecer-reglas"
                    required
                    autoFocus
                  />
                </div>
                <div className="campo">
                  <label htmlFor="restablecer-confirmacion">Confirme la nueva contraseña</label>
                  <input
                    id="restablecer-confirmacion"
                    type="password"
                    autoComplete="new-password"
                    value={confirmacion}
                    onChange={(e) => setConfirmacion(e.target.value)}
                    required
                  />
                </div>
                <ul id="restablecer-reglas" className="secundario nota-pie acceso__reglas">
                  <li>Al menos 8 caracteres.</li>
                  <li>Que no sea una contraseña común ni tenga solo números.</li>
                  <li>Que no se parezca a su usuario ni a su correo.</li>
                </ul>
                <Alerta>{error}</Alerta>
                <button className="boton" type="submit" disabled={enviando}>
                  {enviando ? "Guardando…" : "Guardar la nueva contraseña"}
                </button>
              </form>
            </>
          )}
        </section>
      </div>
    </div>
  );
}
