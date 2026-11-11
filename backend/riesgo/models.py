from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

ROLES = ("desarrollador", "lider_tecnico", "administrador")

# Expresión regular por defecto para reconocer pasos de despliegue por su
# nombre en la API de jobs de GitHub. El administrador puede ajustarla por
# workflow.
# Verbos de despliegue en el nombre del paso (señal de menor prioridad; ver
# riesgo/services/etiquetado.py). No incluye nombres de herramientas: «Compute
# App Engine version tag», «Install Vercel CLI» o «Select Cypress specs»
# contaban como despliegue con el patrón anterior. «deployment(s)» es un
# sustantivo, no el verbo: «Read deployment resource metadata» o «Deployment
# Report» no despliegan (2026-11-11).
PATRON_DESPLIEGUE = (
    r"(?i)\bdeploy(?!ments?\b)|despliegue|despleg|\brollout\b|\bpromote\b|"
    r"helm (upgrade|install)|kubectl (apply|set image|rollout)|"
    r"terraform apply|wrangler-action"
)


class Repositorio(models.Model):
    """Repositorio de GitHub. github_id no cambia aunque se renombre."""

    github_id = models.BigIntegerField(unique=True, null=True, blank=True)
    nombre_completo = models.CharField(max_length=200, unique=True)
    propietario = models.CharField(max_length=100)
    nombre = models.CharField(max_length=100)
    creado_en = models.DateTimeField(auto_now_add=True)
    # Repositorio creado para demostrar la plataforma (ejecuciones provocadas a
    # propósito). Sus resultados no son validación del modelo.
    es_demostracion = models.BooleanField(default=False)
    # Repositorio de los casos de prueba de registro de workflows
    # (datos_prueba/casos_prueba_30.json): igual que la demostración, queda
    # fuera de las métricas y los dashboards.
    es_prueba = models.BooleanField(default=False)
    # A = activo; I = inactivo (se conserva con su historial, pero no se
    # ofrece para nuevos análisis ni en los selectores).
    ESTADOS = [("A", "Activo"), ("I", "Inactivo")]
    est_registro = models.CharField(max_length=1, choices=ESTADOS,
                                    default="A")

    class Meta:
        ordering = ["nombre_completo"]

    def __str__(self):
        return self.nombre_completo


class AccesoRepositorio(models.Model):
    """Repositorios que puede consultar cada desarrollador o líder."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name="accesos")
    repositorio = models.ForeignKey(Repositorio, on_delete=models.CASCADE,
                                    related_name="accesos")
    asignado_por = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="+")
    asignado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["usuario", "repositorio"],
            name="acceso_unico_usuario_repositorio")]

    def __str__(self):
        return f"{self.usuario} → {self.repositorio}"


class Workflow(models.Model):
    """Workflow de GitHub Actions. Solo los validados admiten predicciones."""

    repositorio = models.ForeignKey(Repositorio, on_delete=models.PROTECT,
                                    related_name="workflows")
    path = models.CharField(max_length=255)
    nombre = models.CharField(max_length=200, blank=True)
    github_id = models.BigIntegerField(unique=True, null=True, blank=True)
    despliegue_validado = models.BooleanField(default=False)
    evidencia_validacion = models.TextField(blank=True)
    validado_por = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="+")
    validado_en = models.DateTimeField(null=True, blank=True)
    patron_paso_despliegue = models.CharField(max_length=500,
                                              default=PATRON_DESPLIEGUE)
    # El archivo del workflow puede haberse renombrado o eliminado después de
    # los datos de GHALogs. Se conserva el registro (trazabilidad), pero deja
    # de ofrecerse para nuevos análisis.
    disponible_github = models.BooleanField(default=True)
    verificado_github_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["repositorio", "path"]
        constraints = [models.UniqueConstraint(
            fields=["repositorio", "path"],
            name="workflow_unico_por_repositorio")]

    def clean(self):
        if self.despliegue_validado and not self.evidencia_validacion.strip():
            raise ValidationError({"evidencia_validacion": (
                "Un workflow validado debe documentar la evidencia.")})

    def __str__(self):
        return f"{self.repositorio}:{self.path}"


class Commit(models.Model):
    repositorio = models.ForeignKey(Repositorio, on_delete=models.PROTECT,
                                    related_name="commits")
    sha = models.CharField(max_length=40)
    fecha = models.DateTimeField(null=True, blank=True)
    autor_hash = models.CharField(max_length=12, blank=True)
    mensaje_resumen = models.CharField(max_length=200, blank=True)
    # Métricas del cambio de código (GitHub: stats y files del commit).
    # Se recopilan y guardan; el modelo v1.1 no las usa como variables.
    archivos_modificados = models.PositiveIntegerField(null=True, blank=True)
    adiciones = models.PositiveIntegerField(null=True, blank=True)
    eliminaciones = models.PositiveIntegerField(null=True, blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["repositorio", "sha"], name="commit_unico_por_repositorio")]

    def __str__(self):
        return f"{self.repositorio}@{self.sha[:7]}"


class DatosModeloQuerySet(models.QuerySet):
    """Filas que pueden usarse para entrenar, evaluar o supervisar el modelo.

    Los repositorios de demostración (Repositorio.es_demostracion) y los de
    los casos de prueba (Repositorio.es_prueba) quedan fuera: no son datos
    del modelo. Toda exportación a entrenamiento, métrica o dashboard debe
    partir de para_modelo()."""

    campo_repositorio = "workflow__repositorio"

    def para_modelo(self):
        r = self.campo_repositorio
        return self.exclude(**{f"{r}__es_demostracion": True}).exclude(
            **{f"{r}__es_prueba": True})

    def de_demostracion(self):
        return self.filter(**{f"{self.campo_repositorio}__es_demostracion": True})

    def de_prueba(self):
        return self.filter(**{f"{self.campo_repositorio}__es_prueba": True})


class EjecucionWorkflow(models.Model):
    """Un intento (run_id + run_attempt) de un workflow en GitHub Actions."""

    objects = DatosModeloQuerySet.as_manager()

    ETIQUETAS = [
        ("despliegue_completado", "Despliegue completado (y = 0)"),
        ("despliegue_no_completado", "Despliegue no completado (y = 1)"),
        ("excluida_sin_intento", "Excluida: sin intento de despliegue"),
        ("excluida_ambigua", "Excluida: fallo en otro job con el despliegue "
                             "completado"),
        ("excluida_otro_resultado", "Excluida: cancelada, omitida u otro"),
        ("excluida_sin_jobs", "Excluida: el workflow no arrancó (sin jobs)"),
        ("excluida_no_produccion",
         "Excluida: despliegue a un entorno no productivo"),
    ]
    SUBTIPOS = [
        ("antes_del_despliegue", "Falló antes de llegar al despliegue"),
        ("en_paso_de_despliegue", "Falló en el paso de despliegue"),
        ("posterior_mismo_job", "Falló en un paso posterior del mismo job"),
    ]

    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT,
                                 related_name="ejecuciones")
    commit = models.ForeignKey(Commit, on_delete=models.PROTECT, null=True,
                               blank=True, related_name="ejecuciones")
    run_id = models.BigIntegerField()
    run_attempt = models.PositiveIntegerField(default=1)
    evento = models.CharField(max_length=50, blank=True)
    rama = models.CharField(max_length=255, blank=True)
    estado = models.CharField(max_length=30, blank=True)
    conclusion = models.CharField(max_length=30, blank=True)
    iniciada_en = models.DateTimeField(null=True, blank=True)
    actualizada_en = models.DateTimeField(null=True, blank=True)
    extraida_en = models.DateTimeField()
    # Resultado según la regla de informes/fase2_variable_objetivo.md
    # (solo se calcula al verificar una predicción con la API de jobs).
    despliegue_ejecutado = models.BooleanField(null=True, blank=True)
    paso_fallido = models.CharField(max_length=300, blank=True)
    etiqueta = models.CharField(max_length=30, choices=ETIQUETAS, blank=True)
    subtipo_etiqueta = models.CharField(max_length=30, choices=SUBTIPOS,
                                        blank=True)
    etiquetada_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-iniciada_en"]
        constraints = [models.UniqueConstraint(
            fields=["run_id", "run_attempt"], name="intento_unico")]

    @property
    def y(self):
        return {"despliegue_completado": 0,
                "despliegue_no_completado": 1}.get(self.etiqueta)

    def __str__(self):
        return f"run {self.run_id} intento {self.run_attempt}"


class VersionModelo(models.Model):
    """Modelo entrenado registrado en la plataforma, con sus métricas."""

    version = models.CharField(max_length=20, unique=True)
    nombre_modelo = models.CharField(max_length=100)
    archivo = models.CharField(max_length=255)
    archivo_explicacion = models.CharField(max_length=255)
    metadatos = models.JSONField()
    activo = models.BooleanField(default=False)
    registrado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-registrado_en"]

    def __str__(self):
        return f"{self.version} ({self.nombre_modelo})"


class Prediccion(models.Model):
    """Análisis de riesgo de un despliegue con trazabilidad completa."""

    objects = DatosModeloQuerySet.as_manager()

    NIVELES = [("bajo", "Bajo"), ("medio", "Medio"), ("alto", "Alto")]
    # Recomendación automática según el nivel (predictor.recomendacion_de).
    RECOMENDACIONES = [("permitir", "Permitir el despliegue"),
                       ("solicitar_revision", "Solicitar revisión previa")]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.PROTECT,
                                related_name="predicciones")
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT,
                                 related_name="predicciones")
    commit = models.ForeignKey(Commit, on_delete=models.PROTECT,
                               related_name="predicciones")
    version_modelo = models.ForeignKey(VersionModelo,
                                       on_delete=models.PROTECT,
                                       related_name="predicciones")
    rama = models.CharField(max_length=255, blank=True)
    evento = models.CharField(max_length=50)
    variables = models.JSONField()
    probabilidad = models.FloatField()
    nivel = models.CharField(max_length=10, choices=NIVELES)
    factores = models.JSONField()
    # Vacía en las predicciones anteriores a la recomendación automática.
    recomendacion = models.CharField(max_length=20, choices=RECOMENDACIONES,
                                     blank=True)
    # Lista de {"codigo", "variable", "texto"}.
    recomendaciones = models.JSONField()
    # {"origen": "ia"|"reglas", "modelo", "resumen", "error"}; nulo en
    # predicciones anteriores al análisis con IA.
    analisis_ia = models.JSONField(null=True, blank=True)
    ejecuciones_previas = models.ManyToManyField(
        EjecucionWorkflow, blank=True, related_name="predicciones_que_la_usan")
    ejecucion_real = models.ForeignKey(
        EjecucionWorkflow, on_delete=models.PROTECT, null=True, blank=True,
        related_name="predicciones_verificadas")
    verificada_en = models.DateTimeField(null=True, blank=True)
    datos_github_extraidos_en = models.DateTimeField()
    creada_en = models.DateTimeField(auto_now_add=True)
    # «interactivo»: análisis pedido en la plataforma antes de desplegar.
    # «lote»: análisis de una ejecución ya ocurrida (validación prospectiva
    # de v2), con las variables calculadas en el momento en que empezó
    # (momento_variables) y solo con lo que existía antes de ese momento.
    ORIGENES = [("interactivo", "Análisis en la plataforma"),
                ("lote", "Análisis en lote de una ejecución posterior")]
    origen = models.CharField(max_length=12, choices=ORIGENES,
                              default="interactivo")
    momento_variables = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-creada_en"]

    def clean(self):
        errores = {}
        if self.commit.repositorio_id != self.workflow.repositorio_id:
            errores["commit"] = "El commit no pertenece al repositorio del " \
                                "workflow."
        real = self.ejecucion_real
        if real is not None:
            if real.workflow_id != self.workflow_id:
                errores["ejecucion_real"] = "La ejecución es de otro workflow."
            elif real.commit_id != self.commit_id:
                errores["ejecucion_real"] = "La ejecución es de otro commit."
            elif self.origen == "lote":
                # La ejecución evaluada es la que empezó en el momento de
                # las variables.
                if (real.iniciada_en is None
                        or real.iniciada_en != self.momento_variables):
                    errores["ejecucion_real"] = (
                        "En un análisis en lote, la ejecución debe ser la que "
                        "empezó en el momento de las variables.")
            elif (real.iniciada_en is None or self.creada_en is None
                  or real.iniciada_en <= self.creada_en):
                errores["ejecucion_real"] = ("La ejecución debe haber "
                                             "empezado después de la "
                                             "predicción.")
        if errores:
            raise ValidationError(errores)

    def __str__(self):
        return f"{self.workflow}@{self.commit.sha[:7]}: {self.nivel}"


class DecisionDespliegue(models.Model):
    """Decisión del líder técnico sobre una predicción (historial completo)."""

    DECISIONES = [
        ("autorizar", "Autorizar el despliegue"),
        ("posponer", "Posponer el despliegue"),
        ("solicitar_revision", "Solicitar revisión previa del cambio"),
    ]

    prediccion = models.ForeignKey(Prediccion, on_delete=models.CASCADE,
                                   related_name="decisiones")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.PROTECT,
                                related_name="decisiones")
    # Decisión que coincide con cada recomendación automática.
    SEGUN_RECOMENDACION = {"permitir": "autorizar",
                           "solicitar_revision": "solicitar_revision"}

    decision = models.CharField(max_length=20, choices=DECISIONES)
    # Recomendación vigente al decidir y si el líder la aceptó (nulo si la
    # predicción no tenía recomendación).
    recomendacion = models.CharField(max_length=20, blank=True,
                                     choices=Prediccion.RECOMENDACIONES)
    acepta_recomendacion = models.BooleanField(null=True, blank=True)
    comentario = models.TextField(blank=True, max_length=1000)
    creada_en = models.DateTimeField(auto_now_add=True)
    # Asignación al desarrollador dueño de la predicción. Solo cuentan en la
    # última decisión de cada predicción. `decision` y `comentario` no cambian
    # después de creados; estos campos sí.
    fecha_limite = models.DateField(null=True, blank=True)
    vista_por_desarrollador_en = models.DateTimeField(null=True, blank=True)
    cumplida_en = models.DateTimeField(null=True, blank=True)
    # Respuesta del desarrollador: el nuevo análisis con el que atendió la
    # decisión (posponer o solicitar revisión) y qué cambió.
    prediccion_respuesta = models.ForeignKey(
        Prediccion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="responde_a")
    respuesta_desarrollador = models.TextField(blank=True, max_length=1000)

    class Meta:
        ordering = ["-creada_en"]

    def __str__(self):
        return f"{self.prediccion_id}: {self.decision}"
