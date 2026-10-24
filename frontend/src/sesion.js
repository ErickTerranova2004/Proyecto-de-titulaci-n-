// Coherencia entre la sesión del navegador y la interfaz mostrada.
//
// La interfaz (menú y panel) se elige con el rol de /api/yo/. Si el token de
// esta pestaña cambia (otra pestaña que comparte el almacenamiento, una
// pestaña duplicada o un token caducado), la interfaz no debe seguir siendo la
// del usuario anterior. App vuelve a consultar /api/yo/ al recuperar el foco y
// cuando cambia el token en otra pestaña (evento "storage").
import { rolPrincipal } from "./roles.js";

// true si la respuesta de /api/yo/ ya no corresponde a lo que se muestra.
export function debeReiniciar(usuarioMostrado, yo) {
  if (!usuarioMostrado) return Boolean(yo);
  if (!yo) return true;
  return (
    usuarioMostrado.usuario !== yo.usuario ||
    rolPrincipal(usuarioMostrado.roles) !== rolPrincipal(yo.roles)
  );
}

// Llama a `alCambiar` al recuperar el foco o la visibilidad de la pestaña y
// cuando otra pestaña modifica la clave del token. Devuelve la función para
// dejar de escuchar.
export function escucharSesion(ventana, clave, alCambiar) {
  const alVolver = () => {
    if (ventana.document.visibilityState === "visible") alCambiar();
  };
  const alAlmacenar = (evento) => {
    if (evento.key === clave || evento.key === null) alCambiar();
  };
  ventana.addEventListener("focus", alVolver);
  ventana.document.addEventListener("visibilitychange", alVolver);
  ventana.addEventListener("storage", alAlmacenar);
  return () => {
    ventana.removeEventListener("focus", alVolver);
    ventana.document.removeEventListener("visibilitychange", alVolver);
    ventana.removeEventListener("storage", alAlmacenar);
  };
}
