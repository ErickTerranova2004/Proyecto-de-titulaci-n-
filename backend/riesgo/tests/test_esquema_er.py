"""El esquema de la base de datos coincide con el diagrama ER
(docs/modelo_er.png), columna por columna y con sus tipos.

ER: lo que dice el diagrama. La base de datos debe tener exactamente
ER − PENDIENTE_ETAPA_2 + EXTRA (lo de la implementación que el diagrama aún
no recoge), con DIFERENCIAS_TIPO como únicas diferencias de tipo.
"""

import re

from django.db import DatabaseError, connection, transaction
from django.test import TestCase

BIGINT, INT, BOOL, TEXT = "bigint", "integer", "boolean", "text"
TS, JSON, FLOAT = "timestamp with time zone", "jsonb", "double precision"


def vc(n):
    return f"character varying({n})"


AUDITORIA = {"est_registro": "character(1)", "usu_creacion": vc(150),
             "fec_creacion": TS, "usu_modificacion": vc(150),
             "fec_modificacion": TS}

ER = {
    # Seguridad (vistas sobre las tablas de usuarios de Django).
    "seg_usuario": {"id_usuario": INT, "nom_usuario": vc(150),
                    "hsh_clave": vc(128), "es_superusuario": BOOL},
    "seg_grupo": {"id_grupo": INT, "nom_grupo": vc(150)},
    "int_usuario_grupo": {"id_usuario_grupo": INT, "id_usuario": INT,
                          "id_grupo": INT},
    "seg_token": {"cod_token": vc(40), "id_usuario": INT},
    # Tablas propias.
    "int_acceso_repositorio": {
        "id_acceso_repositorio": BIGINT, "id_usuario": INT,
        "id_repositorio": BIGINT, "id_usuario_asigna": INT,
        "fec_asignacion": TS},
    "mae_repositorio": {
        "id_repositorio": BIGINT, "cod_github": BIGINT,
        "nom_completo": vc(200), "nom_propietario": vc(100),
        "nom_repositorio": vc(100)},
    "mae_workflow": {
        "id_workflow": BIGINT, "id_repositorio": BIGINT,
        "rut_archivo": vc(255), "nom_workflow": vc(200), "cod_github": BIGINT,
        "es_despliegue_validado": BOOL, "des_evidencia_validacion": TEXT,
        "id_usuario_valida": INT, "fec_validacion": TS,
        "des_patron_paso_despliegue": vc(500), "es_disponible_github": BOOL,
        "fec_verificacion_github": TS},
    "trx_commit": {
        "id_commit": BIGINT, "id_repositorio": BIGINT, "cod_sha": vc(40),
        "fec_commit": TS, "hsh_autor": vc(12), "des_mensaje_resumen": vc(200),
        "num_archivos_modificados": INT, "num_adiciones": INT,
        "num_eliminaciones": INT},
    "mae_version_modelo": {
        "id_version_modelo": BIGINT, "cod_version": vc(20),
        "nom_modelo": vc(100), "rut_archivo": vc(255),
        "rut_archivo_explicacion": vc(255), "jsn_metadatos": JSON,
        "es_vigente": BOOL},
    "trx_ejecucion_workflow": {
        "id_ejecucion_workflow": BIGINT, "id_workflow": BIGINT,
        "id_commit": BIGINT, "cod_run": BIGINT, "num_intento": INT,
        "tip_evento": vc(50), "nom_rama": vc(255), "est_ejecucion": vc(30),
        "est_conclusion": vc(30), "fec_inicio": TS, "fec_actualizacion": TS,
        "fec_extraccion": TS, "es_despliegue_ejecutado": BOOL,
        "des_paso_fallido": vc(300), "tip_etiqueta": vc(30),
        "tip_subetiqueta": vc(30), "fec_etiquetado": TS},
    "trx_prediccion": {
        "id_prediccion": BIGINT, "id_usuario": INT, "id_workflow": BIGINT,
        "id_commit": BIGINT, "id_version_modelo": BIGINT, "nom_rama": vc(255),
        "tip_evento": vc(50), "jsn_variables": JSON, "val_probabilidad": FLOAT,
        "tip_nivel_riesgo": vc(10), "jsn_factores": JSON,
        "jsn_recomendaciones": JSON, "id_ejecucion_real": BIGINT,
        "fec_verificacion": TS, "fec_extraccion_github": TS},
    "trx_decision_despliegue": {
        "id_decision_despliegue": BIGINT, "id_prediccion": BIGINT,
        "id_usuario": INT, "tip_decision": vc(20), "des_comentario": TEXT},
    "int_prediccion_ejecucion": {
        "id_prediccion_ejecucion": BIGINT, "id_prediccion": BIGINT,
        "id_ejecucion_workflow": BIGINT},
}
for _columnas in ER.values():
    _columnas.update(AUDITORIA)

VISTAS = {"seg_usuario", "seg_grupo", "int_usuario_grupo", "seg_token"}
TABLAS_PROPIAS = set(ER) - VISTAS | {"trx_seguimiento_lote",
                                     "trx_pendiente_despliegue"}

# Auditoría del ER que aún no existe (etapa 2). En las vistas seg_* está
# como columnas nulas o derivadas.
_SIN_AUDITORIA = set(AUDITORIA)
PENDIENTE_ETAPA_2 = {
    "int_acceso_repositorio": _SIN_AUDITORIA,
    "mae_repositorio": _SIN_AUDITORIA - {"est_registro", "fec_creacion"},
    "mae_workflow": _SIN_AUDITORIA,
    "trx_commit": _SIN_AUDITORIA,
    "mae_version_modelo": _SIN_AUDITORIA - {"fec_creacion"},
    "trx_ejecucion_workflow": _SIN_AUDITORIA,
    "trx_prediccion": _SIN_AUDITORIA - {"fec_creacion"},
    "trx_decision_despliegue": _SIN_AUDITORIA - {"fec_creacion"},
    "int_prediccion_ejecucion": _SIN_AUDITORIA,
}

# En la implementación y no en el diagrama (hay que añadirlo al ER).
EXTRA = {
    "mae_repositorio": {"es_demostracion": BOOL, "es_prueba": BOOL},
    "trx_prediccion": {"tip_recomendacion": vc(20), "jsn_analisis_ia": JSON,
                       "tip_origen": vc(12), "fec_momento_variables": TS},
    "trx_decision_despliegue": {
        "tip_recomendacion": vc(20), "es_acepta_recomendacion": BOOL,
        "fec_limite": "date", "fec_vista_desarrollador": TS,
        "fec_cumplimiento": TS, "id_prediccion_respuesta": BIGINT,
        "des_respuesta_desarrollador": TEXT},
    "trx_seguimiento_lote": {
        "id_seguimiento_lote": BIGINT, "id_workflow": BIGINT,
        "fec_listado_hasta": TS, "jsn_pendientes": JSON, "cod_etag": vc(200),
        "des_etag_params": vc(200), "fec_actualizacion": TS},
    "trx_pendiente_despliegue": {
        "id_pendiente_despliegue": BIGINT, "id_workflow": BIGINT,
        "nom_rama_principal": vc(255), "cod_sha_cabeza": vc(40),
        "num_commits_pendientes": INT, "cod_sha_ultimo_despliegue": vc(40),
        "fec_ultimo_despliegue": TS, "tip_evento_ultimo_despliegue": vc(50),
        "nom_rama_ultimo_despliegue": vc(255), "nom_rama_sugerida": vc(255),
        "cod_etag_despliegues": vc(200), "cod_etag_cabeza": vc(200),
        "fec_calculo": TS},
}

# Únicas diferencias de tipo con el diagrama: est_registro es char(1) en el
# ER y Django lo guarda como varchar(1).
DIFERENCIAS_TIPO = {("mae_repositorio", "est_registro"): vc(1),
                    # Django crea la tabla intermedia de grupos con bigint.
                    ("int_usuario_grupo", "id_usuario_grupo"): BIGINT}


def esquema_esperado():
    esperado = {}
    for tabla in set(ER) | set(EXTRA):
        columnas = {c: t for c, t in ER.get(tabla, {}).items()
                    if c not in PENDIENTE_ETAPA_2.get(tabla, set())}
        columnas.update(EXTRA.get(tabla, {}))
        for (t, c), tipo in DIFERENCIAS_TIPO.items():
            if t == tabla:
                columnas[c] = tipo
        esperado[tabla] = columnas
    return esperado


def esquema_real(tablas):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod)
              FROM pg_attribute a
              JOIN pg_class c ON c.oid = a.attrelid
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE n.nspname = current_schema() AND c.relname = ANY(%s)
               AND a.attnum > 0 AND NOT a.attisdropped""", [list(tablas)])
        real = {}
        for tabla, columna, tipo in cursor.fetchall():
            real.setdefault(tabla, {})[columna] = tipo
    return real


class EsquemaERTest(TestCase):
    def test_tablas_y_columnas_coinciden_con_el_er(self):
        esperado = esquema_esperado()
        real = esquema_real(esperado)
        self.assertEqual(set(real), set(esperado), "tablas o vistas que faltan")
        for tabla in sorted(esperado):
            with self.subTest(tabla=tabla):
                self.assertEqual(real[tabla], esperado[tabla])

    def test_no_quedan_tablas_con_el_prefijo_antiguo(self):
        with connection.cursor() as cursor:
            cursor.execute("""SELECT relname FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = current_schema() AND relname LIKE 'riesgo%%'
                  AND relkind IN ('r', 'v', 'i', 'S')""")
            self.assertEqual(cursor.fetchall(), [])

    def test_indices_y_restricciones_con_nombres_legibles(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT t.relname, c.conname, c.contype FROM pg_constraint c
                  JOIN pg_class t ON t.oid = c.conrelid
                 WHERE t.relname = ANY(%s)""", [list(TABLAS_PROPIAS)])
            restricciones = cursor.fetchall()
            cursor.execute("""
                SELECT t.relname, i.relname FROM pg_index x
                  JOIN pg_class i ON i.oid = x.indexrelid
                  JOIN pg_class t ON t.oid = x.indrelid
                 WHERE t.relname = ANY(%s)""", [list(TABLAS_PROPIAS)])
            indices = cursor.fetchall()
        prefijo = {"p": "pk", "f": "fk", "u": "uk", "c": "ck"}
        for tabla, nombre, tipo in restricciones:
            self.assertTrue(nombre.startswith(f"{prefijo[tipo]}_{tabla}"),
                            nombre)
        for tabla, nombre in indices:
            self.assertRegex(nombre, rf"^(pk|uk|ix)_{re.escape(tabla)}")
        self.assertIn(("trx_prediccion", "pk_trx_prediccion"), indices)
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_get_serial_sequence('trx_prediccion', "
                           "'id_prediccion')")
            self.assertEqual(cursor.fetchone()[0],
                             "public.sq_trx_prediccion_id_prediccion")
        self.assertIn(("trx_prediccion", "fk_trx_prediccion_id_workflow", "f"),
                      restricciones)

    def test_vistas_seg_de_solo_lectura(self):
        from django.contrib.auth.models import User
        User.objects.create_user("ana", password="x")
        with connection.cursor() as cursor:
            cursor.execute("SELECT nom_usuario, est_registro FROM seg_usuario")
            self.assertEqual(cursor.fetchall(), [("ana", "A")])
            # INSTEAD OF … FOR EACH ROW: falla en cuanto la orden toca filas.
            for sql in ("UPDATE seg_usuario SET nom_usuario = 'otra'",
                        "DELETE FROM seg_usuario",
                        "INSERT INTO seg_grupo (nom_grupo) VALUES ('x')",
                        "INSERT INTO seg_token (cod_token) VALUES ('x')"):
                with self.subTest(sql=sql), self.assertRaises(DatabaseError):
                    with transaction.atomic():
                        cursor.execute(sql)
        self.assertEqual(User.objects.get().username, "ana")
