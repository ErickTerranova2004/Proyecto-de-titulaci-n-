// Límite de errores (error boundary) de React.
//
// Un error al renderizar un componente desmonta todo el árbol y deja la
// interfaz en blanco. Este componente lo atrapa y muestra un aviso en su
// lugar; el resto de la interfaz (menú, cabecera) sigue funcionando.
//
// Está escrito sin JSX para que las pruebas (node --test) puedan importarlo.
import { Component, createElement as h } from "react";

export const MENSAJE_ERROR = "Esta sección tuvo un error inesperado y no se pudo mostrar.";

export class LimiteErrores extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
    this.reintentar = this.reintentar.bind(this);
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    const registrar = this.props.alError || ((e, i) => console.error("Error en la interfaz:", e, i && i.componentStack));
    registrar(error, info);
  }

  // Al cambiar de sección (otra claveReinicio) se vuelve a intentar.
  componentDidUpdate(previas) {
    if (this.state.error && previas.claveReinicio !== this.props.claveReinicio) {
      this.setState({ error: null });
    }
  }

  reintentar() {
    this.setState({ error: null });
  }

  render() {
    const { error } = this.state;
    if (!error) return this.props.children === undefined ? null : this.props.children;
    const recargar = () => window.location.reload();
    return h(
      "div",
      { className: "alerta limite-errores", role: "alert" },
      h("p", null, h("strong", null, this.props.titulo || MENSAJE_ERROR)),
      h("p", { className: "secundario" }, "Detalle: ", String((error && error.message) || error)),
      h(
        "p",
        { className: "limite-errores__acciones" },
        h("button", { type: "button", className: "boton boton--secundario boton--pequeno", onClick: this.reintentar }, "Reintentar"),
        " ",
        h("button", { type: "button", className: "boton boton--secundario boton--pequeno", onClick: recargar }, "Recargar la página"),
      ),
    );
  }
}
