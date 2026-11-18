// Restablecimiento de contraseña por correo. El enlace del correo apunta a
// FRONTEND_URL/restablecer/<uid>/<token> (backend/riesgo/services/restablecimiento.py).

const RUTA = /^\/restablecer\/([A-Za-z0-9_-]+)\/([A-Za-z0-9-]+)\/?$/;

// {uid, token} si la ruta es la del enlace del correo; null si no.
export function enlaceRestablecer(ruta) {
  const m = RUTA.exec(ruta || "");
  return m ? { uid: m[1], token: m[2] } : null;
}

// Comprobaciones previas al envío (las reglas completas de Django las aplica
// el backend: longitud, contraseñas comunes, solo números, parecido al usuario).
export function problemaContrasena(contrasena, confirmacion) {
  if (!contrasena) return "Escriba la nueva contraseña.";
  if (contrasena.length < 8) return "La contraseña debe tener al menos 8 caracteres.";
  if (/^\d+$/.test(contrasena)) return "La contraseña no puede tener solo números.";
  if (contrasena !== confirmacion) return "Las dos contraseñas no coinciden.";
  return "";
}

// Mensaje del envío del enlace para el administrador.
export function textoEnvio(usuario, envio) {
  if (!envio) return "";
  if (!envio.enviado) return `No se pudo enviar el correo a ${usuario}. Revise la configuración del correo.`;
  if (envio.medio === "consola") {
    return (
      `El correo no está configurado: el enlace para ${usuario} se escribió en la consola del servidor ` +
      "(no llegó a su buzón)."
    );
  }
  return `Enlace enviado a ${envio.correo}. Vale una hora y un solo uso.`;
}
