"""Filtro de registros que oculta tokens y credenciales."""

import logging
import re

PATRONES = [
    re.compile(r"(gh[pousr]_[A-Za-z0-9]{20,})"),
    re.compile(r"(github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"((?:Authorization|Bearer|token)[\"':= ]+)([^\s\"',]+)",
               re.IGNORECASE),
]


def ocultar(texto):
    texto = PATRONES[0].sub("***", texto)
    texto = PATRONES[1].sub("***", texto)
    return PATRONES[2].sub(r"\1***", texto)


class OcultarSecretos(logging.Filter):
    def filter(self, record):
        record.msg = ocultar(str(record.getMessage()))
        record.args = ()
        return True
