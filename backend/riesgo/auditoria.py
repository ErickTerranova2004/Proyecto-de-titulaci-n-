"""Auditoría de las tablas propias (diagrama ER, docs/modelo_er.png).

Cada tabla propia tiene est_registro, usu_creacion, fec_creacion,
usu_modificacion y fec_modificacion (modelo abstracto Auditoria). Se llenan
solos en todas las vías de escritura:

- save(), create(), get_or_create(), update_or_create() y bulk_create(): los
  campos UsuarioAuditoria se calculan al guardar, como auto_now_add/auto_now
  en las fechas (pre_save).
- save(update_fields=[...]): Auditoria.save añade los campos de modificación.
- QuerySet.update() y bulk_update(): AuditoriaQuerySet los añade.

El usuario sale del contexto de la escritura:

- Peticiones: MiddlewareAuditoria guarda la petición y el usuario se lee al
  escribir (DRF autentica el token dentro de la vista y lo copia a
  request.user, así que el middleware no necesita conocerlo de antemano).
- Comandos: ComandoAuditado (base de los comandos de riesgo) fija el usuario
  del comando, p. ej. «analisis_lote» o «comando:registrar_modelo».
- Fuera de ambos (shell, migraciones de datos, pruebas que escriben con el
  ORM): USUARIO_SISTEMA.

est_registro: 'A' (activo) o 'I' (inactivo), char(1) como en el ER. Solo
Repositorio usa 'I'; no hay borrado lógico ('E').
"""

import contextvars
from contextlib import contextmanager

from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone

USUARIO_SISTEMA = "sistema"
USUARIO_ANONIMO = "anonimo"
COLUMNAS_MODIFICACION = ("usu_modificacion", "fec_modificacion")

_contexto = contextvars.ContextVar("auditoria_usuario", default=None)


def usuario_actual():
    """Nombre de usuario que se guarda en usu_creacion/usu_modificacion."""
    valor = _contexto.get()
    if valor is None:
        return USUARIO_SISTEMA
    if isinstance(valor, str):
        return valor
    usuario = getattr(valor, "user", None)  # HttpRequest
    if usuario is not None and usuario.is_authenticated:
        return usuario.get_username()[:150]
    return USUARIO_ANONIMO


@contextmanager
def como(usuario):
    """Las escrituras dentro del bloque se atribuyen a `usuario` (nombre o
    instancia de usuario)."""
    nombre = usuario if isinstance(usuario, str) else usuario.get_username()
    token = _contexto.set(nombre[:150])
    try:
        yield
    finally:
        _contexto.reset(token)


class MiddlewareAuditoria:
    """Atribuye las escrituras de cada petición a su usuario autenticado."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _contexto.set(request)
        try:
            return self.get_response(request)
        finally:
            _contexto.reset(token)


class ComandoAuditado(BaseCommand):
    """Base de los comandos que escriben en la base de datos."""

    def usuario_auditoria(self, opciones):
        return f"comando:{self.__module__.rsplit('.', 1)[-1]}"

    def execute(self, *args, **opciones):
        with como(self.usuario_auditoria(opciones)):
            return super().execute(*args, **opciones)


class CharFijo(models.CharField):
    """char(n) de longitud fija (el ER usa char(1) para est_registro)."""

    def db_type(self, connection):
        return f"char({self.max_length})"


class UsuarioAuditoria(models.CharField):
    """Usuario que crea (al_crear=True) o modifica por última vez la fila."""

    def __init__(self, *args, al_crear=False, **kwargs):
        kwargs.setdefault("max_length", 150)
        kwargs.setdefault("blank", True)
        kwargs.setdefault("default", "")
        kwargs.setdefault("editable", False)
        self.al_crear = al_crear
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        nombre, ruta, args, kwargs = super().deconstruct()
        if self.al_crear:
            kwargs["al_crear"] = True
        return nombre, ruta, args, kwargs

    def pre_save(self, instancia, add):
        valor = getattr(instancia, self.attname)
        if self.al_crear and not (add and not valor):
            return valor  # solo al crear, y sin pisar un valor explícito
        valor = usuario_actual()
        setattr(instancia, self.attname, valor)
        return valor


def campos_modificacion(modelo):
    return [f for f in modelo._meta.concrete_fields
            if f.column in COLUMNAS_MODIFICACION]


def _valor_modificacion(campo, ahora):
    return ahora if isinstance(campo, models.DateTimeField) else usuario_actual()


class AuditoriaQuerySet(models.QuerySet):
    """update() y bulk_update() también registran quién y cuándo."""

    def update(self, **kwargs):
        ahora = timezone.now()
        for campo in campos_modificacion(self.model):
            kwargs.setdefault(campo.name, _valor_modificacion(campo, ahora))
        return super().update(**kwargs)

    update.alters_data = True

    def bulk_update(self, objs, fields, batch_size=None):
        ahora = timezone.now()
        campos = campos_modificacion(self.model)
        for obj in objs:
            for campo in campos:
                setattr(obj, campo.attname, _valor_modificacion(campo, ahora))
        nombres = list(fields) + [c.name for c in campos if c.name not in fields]
        return super().bulk_update(objs, nombres, batch_size=batch_size)

    bulk_update.alters_data = True


class Auditoria(models.Model):
    """Campos de auditoría del ER. Un modelo que ya tenía su fecha de
    creación la conserva con db_column="fec_creacion" y anula la heredada
    (fec_creacion = None)."""

    ESTADOS = [("A", "Activo"), ("I", "Inactivo")]

    est_registro = CharFijo(max_length=1, choices=ESTADOS, default="A")
    usu_creacion = UsuarioAuditoria(al_crear=True)
    fec_creacion = models.DateTimeField(auto_now_add=True)
    usu_modificacion = UsuarioAuditoria()
    fec_modificacion = models.DateTimeField(auto_now=True)

    objects = AuditoriaQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        campos = kwargs.get("update_fields")
        if campos:
            kwargs["update_fields"] = set(campos) | {
                c.name for c in campos_modificacion(type(self))}
        super().save(*args, **kwargs)
