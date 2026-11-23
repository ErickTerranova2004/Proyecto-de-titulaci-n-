"""Paginación opcional de los listados (historiales, pendientes, asignaciones,
informes y usuarios).

Solo con ?pagina=N la respuesta es una página:
{"total", "pagina", "por_pagina", "paginas", "resultados"}. Sin el parámetro
se devuelve la lista completa, como antes (la usan el Panel, el Planificador
y la alarma de asignaciones). Se pagina después de filtrar y ordenar, así que
las páginas respetan los filtros y el orden.
"""

from math import ceil

from django.db.models import QuerySet
from rest_framework.exceptions import ValidationError

POR_PAGINA = (25, 50, 100)
POR_DEFECTO = 25


def pedida(parametros):
    return "pagina" in parametros


def _entero(parametros, nombre, defecto):
    valor = (parametros.get(nombre) or "").strip()
    if not valor:
        return defecto
    if not valor.isdigit():
        raise ValidationError({nombre: "Debe ser un número entero positivo."})
    return int(valor)


def paginar(elementos, parametros, serializar):
    """`elementos`: QuerySet o lista ya filtrados y ordenados.
    `serializar(lista)`: convierte los elementos de la página en datos."""
    por_pagina = _entero(parametros, "por_pagina", POR_DEFECTO)
    if por_pagina not in POR_PAGINA:
        raise ValidationError({"por_pagina": "Use 25, 50 o 100."})
    pagina = _entero(parametros, "pagina", 1)
    if pagina < 1:
        raise ValidationError({"pagina": "Debe ser 1 o mayor."})
    total = elementos.count() if isinstance(elementos, QuerySet) else len(elementos)
    paginas = max(1, ceil(total / por_pagina))
    # Una página que ya no existe (p. ej. tras filtrar) muestra la última.
    pagina = min(pagina, paginas)
    inicio = (pagina - 1) * por_pagina
    return {"total": total, "pagina": pagina, "por_pagina": por_pagina,
            "paginas": paginas,
            "resultados": serializar(list(elementos[inicio:inicio + por_pagina]))}
