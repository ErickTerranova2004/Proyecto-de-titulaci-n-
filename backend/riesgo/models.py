from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from riesgo.auditoria import Auditoria, AuditoriaQuerySet

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


class Repositorio(Auditoria):
    """Repositorio de GitHub. github_id no cambia aunque se renombre."""

    id = models.BigAutoField(primary_key=True, db_column="id_repositorio")
    github_id = models.BigIntegerField(unique=True, null=True, blank=True,
                                       db_column="cod_github")
    nombre_completo = models.CharField(max_length=200, unique=True,
                                       db_column="nom_completo")
    propietario = models.CharField(max_length=100,
                                   db_column="nom_propietario")
    nombre = models.CharField(max_length=100,
                              db_column="nom_repositorio")
    creado_en = models.DateTimeField(auto_now_add=True,
                                     db_column="fec_creacion")
    # Repositorio creado para demostrar la plataforma (ejecuciones provocadas a
    # propósito). Sus resultados no son validación del modelo.
    es_demostracion = models.BooleanField(default=False)
    # Repositorio de los casos de prueba de registro de workflows
    # (datos_prueba/casos_prueba_30.json): igual que la demostración, queda
    # fuera de las métricas y los dashboards.
    es_prueba = models.BooleanField(default=False)
    # est_registro (Auditoria): A = activo; I = inactivo (se conserva con su
    # historial, pero no se ofrece para nuevos análisis ni en los selectores).
    fec_creacion = None  # creado_en

    class Meta:
        db_table = "mae_repositorio"
        ordering = ["nombre_completo"]

    def __str__(self):
        return self.nombre_completo


class AccesoRepositorio(Auditoria):
    """Repositorios que puede consultar cada desarrollador o líder."""

    id = models.BigAutoField(primary_key=True,
                              db_column="id_acceso_repositorio")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.CASCADE,
                                related_name="accesos",
                                db_column="id_usuario")
    repositorio = models.ForeignKey(Repositorio, on_delete=models.CASCADE,
                                    related_name="accesos",
                                    db_column="id_repositorio")
    asignado_por = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="+",
                                     db_column="id_usuario_asigna")
    asignado_en = models.DateTimeField(auto_now_add=True,
                                       db_column="fec_asignacion")

    class Meta:
        db_table = "int_acceso_repositorio"
        constraints = [models.UniqueConstraint(
            fields=["usuario", "repositorio"],
            name="uk_int_acceso_repositorio_id_usuario_id_repositorio")]

    def __str__(self):
        return f"{self.usuario} → {self.repositorio}"


class Workflow(Auditoria):
    """Workflow de GitHub Actions. Solo los validados admiten predicciones."""

    id = models.BigAutoField(primary_key=True, db_column="id_workflow")
    repositorio = models.ForeignKey(Repositorio, on_delete=models.PROTECT,
                                    related_name="workflows",
                                    db_column="id_repositorio")
    path = models.CharField(max_length=255,
                            db_column="rut_archivo")
    nombre = models.CharField(max_length=200, blank=True,
                              db_column="nom_workflow")
    github_id = models.BigIntegerField(unique=True, null=True, blank=True,
                                       db_column="cod_github")
    despliegue_validado = models.BooleanField(
        default=False, db_column="es_despliegue_validado")
    evidencia_validacion = models.TextField(
        blank=True, db_column="des_evidencia_validacion")
    validado_por = models.ForeignKey(settings.AUTH_USER_MODEL,
                                     on_delete=models.SET_NULL, null=True,
                                     blank=True, related_name="+",
                                     db_column="id_usuario_valida")
    validado_en = models.DateTimeField(null=True, blank=True,
                                       db_column="fec_validacion")
    patron_paso_despliegue = models.CharField(
        max_length=500, default=PATRON_DESPLIEGUE,
        db_column="des_patron_paso_despliegue")
    # El archivo del workflow puede haberse renombrado o eliminado después de
    # los datos de GHALogs. Se conserva el registro (trazabilidad), pero deja
    # de ofrecerse para nuevos análisis.
    disponible_github = models.BooleanField(default=True,
                                            db_column="es_disponible_github")
    verificado_github_en = models.DateTimeField(
        null=True, blank=True, db_column="fec_verificacion_github")

    class Meta:
        db_table = "mae_workflow"
        ordering = ["repositorio", "path"]
        constraints = [models.UniqueConstraint(
            fields=["repositorio", "path"],
            name="uk_mae_workflow_id_repositorio_rut_archivo")]

    def clean(self):
        if self.despliegue_validado and not self.evidencia_validacion.strip():
            raise ValidationError({"evidencia_validacion": (
                "Un workflow validado debe documentar la evidencia.")})

    def __str__(self):
        return f"{self.repositorio}:{self.path}"


class Commit(Auditoria):
    id = models.BigAutoField(primary_key=True, db_column="id_commit")
    repositorio = models.ForeignKey(Repositorio, on_delete=models.PROTECT,
                                    related_name="commits",
                                    db_column="id_repositorio")
    sha = models.CharField(max_length=40,
                           db_column="cod_sha")
    fecha = models.DateTimeField(null=True, blank=True,
                                 db_column="fec_commit")
    autor_hash = models.CharField(max_length=12, blank=True,
                                  db_column="hsh_autor")
    mensaje_resumen = models.CharField(max_length=200, blank=True,
                                       db_column="des_mensaje_resumen")
    # Métricas del cambio de código (GitHub: stats y files del commit).
    # Se recopilan y guardan; el modelo v1.1 no las usa como variables.
    archivos_modificados = models.PositiveIntegerField(
        null=True, blank=True, db_column="num_archivos_modificados")
    adiciones = models.PositiveIntegerField(null=True, blank=True,
                                            db_column="num_adiciones")
    eliminaciones = models.PositiveIntegerField(null=True, blank=True,
                                                db_column="num_eliminaciones")

    class Meta:
        db_table = "trx_commit"
        constraints = [models.UniqueConstraint(
            fields=["repositorio", "sha"],
            name="uk_trx_commit_id_repositorio_cod_sha")]

    def __str__(self):
        return f"{self.repositorio}@{self.sha[:7]}"


class DatosModeloQuerySet(AuditoriaQuerySet):
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


class EjecucionWorkflow(Auditoria):
    """Un intento (run_id + run_attempt) de un workflow en GitHub Actions."""

    id = models.BigAutoField(primary_key=True,
                              db_column="id_ejecucion_workflow")
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
                                 related_name="ejecuciones",
                                 db_column="id_workflow")
    commit = models.ForeignKey(Commit, on_delete=models.PROTECT, null=True,
                               blank=True, related_name="ejecuciones",
                               db_column="id_commit")
    run_id = models.BigIntegerField(db_column="cod_run")
    run_attempt = models.PositiveIntegerField(default=1,
                                              db_column="num_intento")
    evento = models.CharField(max_length=50, blank=True,
                              db_column="tip_evento")
    rama = models.CharField(max_length=255, blank=True,
                            db_column="nom_rama")
    estado = models.CharField(max_length=30, blank=True,
                              db_column="est_ejecucion")
    conclusion = models.CharField(max_length=30, blank=True,
                                  db_column="est_conclusion")
    iniciada_en = models.DateTimeField(null=True, blank=True,
                                       db_column="fec_inicio")
    actualizada_en = models.DateTimeField(null=True, blank=True,
                                          db_column="fec_actualizacion")
    extraida_en = models.DateTimeField(db_column="fec_extraccion")
    # Resultado según la regla de informes/fase2_variable_objetivo.md
    # (solo se calcula al verificar una predicción con la API de jobs).
    despliegue_ejecutado = models.BooleanField(
        null=True, blank=True, db_column="es_despliegue_ejecutado")
    paso_fallido = models.CharField(max_length=300, blank=True,
                                    db_column="des_paso_fallido")
    etiqueta = models.CharField(max_length=30, choices=ETIQUETAS, blank=True,
                                db_column="tip_etiqueta")
    subtipo_etiqueta = models.CharField(max_length=30, choices=SUBTIPOS,
                                        blank=True,
                                        db_column="tip_subetiqueta")
    etiquetada_en = models.DateTimeField(null=True, blank=True,
                                         db_column="fec_etiquetado")

    class Meta:
        db_table = "trx_ejecucion_workflow"
        ordering = ["-iniciada_en"]
        constraints = [models.UniqueConstraint(
            fields=["run_id", "run_attempt"],
            name="uk_trx_ejecucion_workflow_cod_run_num_intento")]

    @property
    def y(self):
        return {"despliegue_completado": 0,
                "despliegue_no_completado": 1}.get(self.etiqueta)

    def __str__(self):
        return f"run {self.run_id} intento {self.run_attempt}"


class VersionModelo(Auditoria):
    """Modelo entrenado registrado en la plataforma, con sus métricas."""

    id = models.BigAutoField(primary_key=True, db_column="id_version_modelo")
    version = models.CharField(max_length=20, unique=True,
                               db_column="cod_version")
    nombre_modelo = models.CharField(max_length=100,
                                     db_column="nom_modelo")
    archivo = models.CharField(max_length=255,
                               db_column="rut_archivo")
    archivo_explicacion = models.CharField(max_length=255,
                                           db_column="rut_archivo_explicacion")
    metadatos = models.JSONField(db_column="jsn_metadatos")
    activo = models.BooleanField(default=False,
                                 db_column="es_vigente")
    registrado_en = models.DateTimeField(auto_now_add=True,
                                         db_column="fec_creacion")
    fec_creacion = None  # registrado_en

    class Meta:
        db_table = "mae_version_modelo"
        ordering = ["-registrado_en"]

    def __str__(self):
        return f"{self.version} ({self.nombre_modelo})"


class Prediccion(Auditoria):
    """Análisis de riesgo de un despliegue con trazabilidad completa."""

    id = models.BigAutoField(primary_key=True, db_column="id_prediccion")
    objects = DatosModeloQuerySet.as_manager()

    NIVELES = [("bajo", "Bajo"), ("medio", "Medio"), ("alto", "Alto")]
    # Recomendación automática según el nivel (predictor.recomendacion_de).
    RECOMENDACIONES = [("permitir", "Permitir el despliegue"),
                       ("solicitar_revision", "Solicitar revisión previa")]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.PROTECT,
                                related_name="predicciones",
                                db_column="id_usuario")
    workflow = models.ForeignKey(Workflow, on_delete=models.PROTECT,
                                 related_name="predicciones",
                                 db_column="id_workflow")
    commit = models.ForeignKey(Commit, on_delete=models.PROTECT,
                               related_name="predicciones",
                               db_column="id_commit")
    version_modelo = models.ForeignKey(VersionModelo,
                                       on_delete=models.PROTECT,
                                       related_name="predicciones",
                                       db_column="id_version_modelo")
    rama = models.CharField(max_length=255, blank=True,
                            db_column="nom_rama")
    evento = models.CharField(max_length=50,
                              db_column="tip_evento")
    variables = models.JSONField(db_column="jsn_variables")
    probabilidad = models.FloatField(db_column="val_probabilidad")
    nivel = models.CharField(max_length=10, choices=NIVELES,
                             db_column="tip_nivel_riesgo")
    factores = models.JSONField(db_column="jsn_factores")
    # Vacía en las predicciones anteriores a la recomendación automática.
    recomendacion = models.CharField(max_length=20, choices=RECOMENDACIONES,
                                     blank=True,
                                     db_column="tip_recomendacion")
    # Lista de {"codigo", "variable", "texto"}.
    recomendaciones = models.JSONField(db_column="jsn_recomendaciones")
    # {"origen": "ia"|"reglas", "modelo", "resumen", "error"}; nulo en
    # predicciones anteriores al análisis con IA.
    analisis_ia = models.JSONField(null=True, blank=True,
                                   db_column="jsn_analisis_ia")
    ejecuciones_previas = models.ManyToManyField(
        EjecucionWorkflow, blank=True, related_name="predicciones_que_la_usan",
        through="PrediccionEjecucion")
    ejecucion_real = models.ForeignKey(
        EjecucionWorkflow, on_delete=models.PROTECT, null=True, blank=True,
        related_name="predicciones_verificadas",
        db_column="id_ejecucion_real")
    verificada_en = models.DateTimeField(null=True, blank=True,
                                         db_column="fec_verificacion")
    datos_github_extraidos_en = models.DateTimeField(
        db_column="fec_extraccion_github")
    creada_en = models.DateTimeField(auto_now_add=True,
                                     db_column="fec_creacion")
    fec_creacion = None  # creada_en
    # «interactivo»: análisis pedido en la plataforma antes de desplegar.
    # «lote»: análisis de una ejecución ya ocurrida (validación prospectiva
    # de v2), con las variables calculadas en el momento en que empezó
    # (momento_variables) y solo con lo que existía antes de ese momento.
    ORIGENES = [("interactivo", "Análisis en la plataforma"),
                ("lote", "Análisis en lote de una ejecución posterior")]
    origen = models.CharField(max_length=12, choices=ORIGENES,
                              default="interactivo",
                              db_column="tip_origen")
    momento_variables = models.DateTimeField(null=True, blank=True,
                                             db_column="fec_momento_variables")

    class Meta:
        db_table = "trx_prediccion"
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


class PrediccionEjecucion(Auditoria):
    """Ejecuciones previas del workflow usadas como historial de una
    predicción (tabla intermedia N:M)."""

    id = models.BigAutoField(primary_key=True,
                              db_column="id_prediccion_ejecucion")
    prediccion = models.ForeignKey(Prediccion, on_delete=models.CASCADE,
                                   db_column="id_prediccion")
    ejecucion_workflow = models.ForeignKey(EjecucionWorkflow,
                                           on_delete=models.CASCADE,
                                           db_column="id_ejecucion_workflow")

    class Meta:
        db_table = "int_prediccion_ejecucion"
        constraints = [models.UniqueConstraint(
            fields=["prediccion", "ejecucion_workflow"],
            name="uk_int_prediccion_ejecucion_id_prediccion_id_ejecucion_workflow")]

    def __str__(self):
        return f"{self.prediccion_id} ← {self.ejecucion_workflow_id}"


class DecisionDespliegue(Auditoria):
    """Decisión del líder técnico sobre una predicción (historial completo)."""

    id = models.BigAutoField(primary_key=True,
                              db_column="id_decision_despliegue")
    DECISIONES = [
        ("autorizar", "Autorizar el despliegue"),
        ("posponer", "Posponer el despliegue"),
        ("solicitar_revision", "Solicitar revisión previa del cambio"),
    ]

    prediccion = models.ForeignKey(Prediccion, on_delete=models.CASCADE,
                                   related_name="decisiones",
                                   db_column="id_prediccion")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL,
                                on_delete=models.PROTECT,
                                related_name="decisiones",
                                db_column="id_usuario")
    # Decisión que coincide con cada recomendación automática.
    SEGUN_RECOMENDACION = {"permitir": "autorizar",
                           "solicitar_revision": "solicitar_revision"}

    decision = models.CharField(max_length=20, choices=DECISIONES,
                                db_column="tip_decision")
    # Recomendación vigente al decidir y si el líder la aceptó (nulo si la
    # predicción no tenía recomendación).
    recomendacion = models.CharField(max_length=20, blank=True,
                                     choices=Prediccion.RECOMENDACIONES,
                                     db_column="tip_recomendacion")
    acepta_recomendacion = models.BooleanField(
        null=True, blank=True, db_column="es_acepta_recomendacion")
    comentario = models.TextField(blank=True, max_length=1000,
                                  db_column="des_comentario")
    creada_en = models.DateTimeField(auto_now_add=True,
                                     db_column="fec_creacion")
    fec_creacion = None  # creada_en
    # Asignación al desarrollador dueño de la predicción. Solo cuentan en la
    # última decisión de cada predicción. `decision` y `comentario` no cambian
    # después de creados; estos campos sí.
    fecha_limite = models.DateField(null=True, blank=True,
                                    db_column="fec_limite")
    vista_por_desarrollador_en = models.DateTimeField(
        null=True, blank=True, db_column="fec_vista_desarrollador")
    cumplida_en = models.DateTimeField(null=True, blank=True,
                                       db_column="fec_cumplimiento")
    # Respuesta del desarrollador: el nuevo análisis con el que atendió la
    # decisión (posponer o solicitar revisión) y qué cambió.
    prediccion_respuesta = models.ForeignKey(
        Prediccion, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="responde_a",
        db_column="id_prediccion_respuesta")
    respuesta_desarrollador = models.TextField(
        blank=True, max_length=1000, db_column="des_respuesta_desarrollador")

    class Meta:
        db_table = "trx_decision_despliegue"
        ordering = ["-creada_en"]

    def __str__(self):
        return f"{self.prediccion_id}: {self.decision}"


class SeguimientoLote(Auditoria):
    """Estado del análisis en lote de un workflow entre pasadas.

    Cada pasada lista solo las ejecuciones creadas desde `listado_hasta`
    menos 48 h (no desde la fecha de corte) y consulta una a una las que
    quedaron `pendientes` (sin terminar) en la pasada anterior. `etag` es el
    de la primera página del listado: si GitHub responde 304 no ha cambiado
    nada y la consulta no gasta cuota.
    """

    id = models.BigAutoField(primary_key=True, db_column="id_seguimiento_lote")
    workflow = models.OneToOneField(Workflow, on_delete=models.CASCADE,
                                    related_name="seguimiento_lote",
                                    db_column="id_workflow")
    listado_hasta = models.DateTimeField(db_column="fec_listado_hasta")
    pendientes = models.JSONField(default=list,
                                  db_column="jsn_pendientes")
    etag = models.CharField(max_length=200, blank=True,
                            db_column="cod_etag")
    etag_params = models.CharField(max_length=200, blank=True,
                                   db_column="des_etag_params")
    actualizado_en = models.DateTimeField(auto_now=True,
                                          db_column="fec_modificacion")
    fec_modificacion = None  # actualizado_en


    class Meta:
        db_table = "trx_seguimiento_lote"

    def __str__(self):
        return f"lote {self.workflow_id} hasta {self.listado_hasta:%Y-%m-%d %H:%M}"


class PendienteDespliegue(Auditoria):
    """Commits de la rama principal aún sin desplegar por un workflow.

    Lo actualiza cada pasada del análisis en lote (peticiones condicionales:
    si nada cambió, no gasta cuota). «Nuevo análisis» lo muestra sin
    consultar GitHub: los repositorios con commits pendientes van primero y
    al elegirlos se rellenan el commit (cabeza de la rama principal), la rama
    y el evento con el que despliega.
    """

    id = models.BigAutoField(primary_key=True,
                              db_column="id_pendiente_despliegue")
    workflow = models.OneToOneField(Workflow, on_delete=models.CASCADE,
                                    related_name="pendiente_despliegue",
                                    db_column="id_workflow")
    rama_principal = models.CharField(max_length=255, blank=True,
                                      db_column="nom_rama_principal")
    sha_cabeza = models.CharField(max_length=40, blank=True,
                                  db_column="cod_sha_cabeza")
    # None: el workflow no tiene ningún despliegue correcto con el que comparar.
    commits_pendientes = models.IntegerField(
        null=True, blank=True, db_column="num_commits_pendientes")
    ultimo_despliegue_sha = models.CharField(
        max_length=40, blank=True, db_column="cod_sha_ultimo_despliegue")
    ultimo_despliegue_en = models.DateTimeField(
        null=True, blank=True, db_column="fec_ultimo_despliegue")
    ultimo_despliegue_evento = models.CharField(
        max_length=50, blank=True, db_column="tip_evento_ultimo_despliegue")
    ultimo_despliegue_rama = models.CharField(
        max_length=255, blank=True, db_column="nom_rama_ultimo_despliegue")
    rama_sugerida = models.CharField(max_length=255, blank=True,
                                     db_column="nom_rama_sugerida")
    etag_despliegues = models.CharField(max_length=200, blank=True,
                                        db_column="cod_etag_despliegues")
    etag_cabeza = models.CharField(max_length=200, blank=True,
                                   db_column="cod_etag_cabeza")
    calculado_en = models.DateTimeField(db_column="fec_calculo")


    class Meta:
        db_table = "trx_pendiente_despliegue"

    def __str__(self):
        return f"{self.workflow}: {self.commits_pendientes} pendientes"
