from datetime import timedelta
from io import StringIO

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from riesgo.models import (AccesoRepositorio, Commit, EjecucionWorkflow,
                           Prediccion, Repositorio, VersionModelo, Workflow)


class ModeloDatosTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("registrar_modelo", stdout=StringIO())
        cls.usuario = User.objects.create_user("dev", password="x")
        cls.repo = Repositorio.objects.create(
            nombre_completo="acme/tienda", propietario="acme", nombre="tienda")
        cls.otro_repo = Repositorio.objects.create(
            nombre_completo="acme/otro", propietario="acme", nombre="otro")
        cls.workflow = Workflow.objects.create(
            repositorio=cls.repo, path=".github/workflows/deploy.yml",
            despliegue_validado=True, evidencia_validacion="prueba")
        cls.otro_workflow = Workflow.objects.create(
            repositorio=cls.repo, path=".github/workflows/otro.yml")
        cls.commit = Commit.objects.create(repositorio=cls.repo, sha="a" * 40)
        cls.otro_commit = Commit.objects.create(repositorio=cls.repo,
                                                sha="b" * 40)

    def ejecucion(self, run_id, intento=1, workflow=None, commit=None,
                  inicio=None):
        return EjecucionWorkflow.objects.create(
            workflow=workflow or self.workflow, commit=commit or self.commit,
            run_id=run_id, run_attempt=intento, iniciada_en=inicio,
            extraida_en=timezone.now())

    def prediccion(self):
        return Prediccion.objects.create(
            usuario=self.usuario, workflow=self.workflow, commit=self.commit,
            version_modelo=VersionModelo.objects.get(), evento="push",
            variables={}, probabilidad=0.1, nivel="bajo", factores=[],
            recomendaciones=[], datos_github_extraidos_en=timezone.now())

    def test_cada_intento_es_una_fila(self):
        self.ejecucion(1, 1)
        self.ejecucion(1, 2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.ejecucion(1, 2)

    def test_acceso_unico_por_par(self):
        AccesoRepositorio.objects.create(usuario=self.usuario,
                                         repositorio=self.repo)
        AccesoRepositorio.objects.create(usuario=self.usuario,
                                         repositorio=self.otro_repo)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AccesoRepositorio.objects.create(usuario=self.usuario,
                                             repositorio=self.repo)

    def test_workflow_unico_por_repositorio(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Workflow.objects.create(repositorio=self.repo,
                                    path=".github/workflows/deploy.yml")

    def test_workflow_validado_exige_evidencia(self):
        w = Workflow(repositorio=self.repo, path=".github/workflows/x.yml",
                     despliegue_validado=True)
        with self.assertRaises(ValidationError):
            w.full_clean()

    def test_ejecucion_real_valida(self):
        p = self.prediccion()
        p.ejecucion_real = self.ejecucion(
            10, inicio=p.creada_en + timedelta(minutes=5))
        p.clean()

    def test_ejecucion_real_rechaza_otro_workflow_commit_o_anterior(self):
        p = self.prediccion()
        despues = p.creada_en + timedelta(minutes=5)
        casos = [
            self.ejecucion(20, workflow=self.otro_workflow, inicio=despues),
            self.ejecucion(21, commit=self.otro_commit, inicio=despues),
            self.ejecucion(22, inicio=p.creada_en - timedelta(minutes=5)),
        ]
        for ejecucion in casos:
            p.ejecucion_real = ejecucion
            with self.assertRaises(ValidationError):
                p.clean()
