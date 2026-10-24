"""Crea o actualiza un usuario de la plataforma con su rol y repositorios.

Se puede repetir sin duplicar: si el usuario existe se actualiza. El
administrador se crea siempre como superusuario con is_staff. --repos fija
la lista completa de repositorios asignados (los que no estén se quitan).

    manage.py crear_usuario prueba_dev --rol desarrollador --repos dueño/repo
    manage.py crear_usuario prueba_admin --rol administrador --password ...

Sin --password la contraseña se pide por teclado (no queda en el historial).
"""

from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from riesgo.models import ROLES, AccesoRepositorio, Repositorio


class Command(BaseCommand):
    help = "Crea o actualiza un usuario con su rol y sus repositorios asignados."

    def add_arguments(self, parser):
        parser.add_argument("usuario")
        parser.add_argument("--rol", required=True, choices=ROLES)
        parser.add_argument("--password",
                            help="Si se omite, se pide por teclado (o se "
                                 "conserva la actual si el usuario existe).")
        parser.add_argument("--repos", nargs="*",
                            help="Repositorios propietario/nombre. Fija la "
                                 "lista completa de accesos del usuario.")

    def handle(self, *args, **opciones):
        nombre, rol = opciones["usuario"], opciones["rol"]
        modelo = get_user_model()
        existe = modelo.objects.filter(username=nombre).exists()
        clave = opciones["password"]
        if clave is None and not existe:
            clave = getpass(f"Contraseña para {nombre}: ")
            if clave != getpass("Repita la contraseña: "):
                raise CommandError("Las contraseñas no coinciden.")
        if clave is not None and not clave:
            raise CommandError("La contraseña no puede estar vacía.")

        repos = None
        if opciones["repos"] is not None:
            repos = list(Repositorio.objects.filter(
                nombre_completo__in=opciones["repos"]))
            faltan = set(opciones["repos"]) - {r.nombre_completo for r in repos}
            if faltan:
                raise CommandError(
                    f"Repositorios no registrados: {', '.join(sorted(faltan))}")

        with transaction.atomic():
            usuario, creado = modelo.objects.get_or_create(username=nombre)
            if clave is not None:
                usuario.set_password(clave)
            es_admin = rol == "administrador"
            usuario.is_superuser = es_admin
            usuario.is_staff = es_admin
            usuario.save()
            usuario.groups.set([Group.objects.get_or_create(name=rol)[0]])
            if repos is not None:
                AccesoRepositorio.objects.filter(usuario=usuario).exclude(
                    repositorio__in=repos).delete()
                for repo in repos:
                    AccesoRepositorio.objects.get_or_create(
                        usuario=usuario, repositorio=repo)

        asignados = AccesoRepositorio.objects.filter(
            usuario=usuario).count()
        self.stdout.write(self.style.SUCCESS(
            f"Usuario {nombre} {'creado' if creado else 'actualizado'}: rol "
            f"{rol}, {asignados} repositorio(s) asignado(s)"
            f"{', superusuario' if usuario.is_superuser else ''}."))
