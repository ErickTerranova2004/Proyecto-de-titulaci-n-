"""Nombres del ER (docs/modelo_er.png), segunda parte.

1. Índices y restricciones de las tablas propias con nombres legibles:
   pk_<tabla>, fk_<tabla>_<columna>, uk_<tabla>_<columnas>,
   ck_<tabla>_<columna>, ix_<tabla>_<columnas>[_like] y, para las
   secuencias de las claves primarias, sq_<tabla>_<columna>. Se calculan desde el
   catálogo de PostgreSQL (los nombres automáticos de Django llevan un hash
   y no son iguales en todas las bases). Las restricciones únicas declaradas
   en Meta.constraints ya tienen ese nombre en el modelo, así que no cambian.
2. Vistas de solo lectura con los nombres del ER sobre las tablas de usuarios
   de Django, que se mantienen: seg_usuario (auth_user), seg_grupo
   (auth_group), int_usuario_grupo (auth_user_groups) y seg_token
   (authtoken_token). Las columnas de auditoría que Django no guarda son
   nulas. Un trigger INSTEAD OF rechaza cualquier escritura en ellas.
"""

from django.db import migrations

TABLAS = ["mae_repositorio", "mae_workflow", "mae_version_modelo",
          "trx_commit", "trx_ejecucion_workflow", "trx_prediccion",
          "trx_decision_despliegue", "trx_seguimiento_lote",
          "trx_pendiente_despliegue", "int_acceso_repositorio",
          "int_prediccion_ejecucion"]

RENOMBRAR = """
DO $$
DECLARE
    r record;
    nuevo text;
BEGIN
    -- Restricciones (PK, FK, UNIQUE, CHECK). Renombrar una PK o UNIQUE
    -- renombra también su índice.
    FOR r IN
        SELECT c.conname, c.contype, t.relname AS tabla,
               (SELECT string_agg(a.attname, '_' ORDER BY k.ord)
                  FROM unnest(c.conkey) WITH ORDINALITY AS k(num, ord)
                  JOIN pg_attribute a
                    ON a.attrelid = c.conrelid AND a.attnum = k.num) AS cols
          FROM pg_constraint c
          JOIN pg_class t ON t.oid = c.conrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = current_schema()
           AND t.relname = ANY (%(tablas)s)
           AND c.contype IN ('p', 'f', 'u', 'c')
    LOOP
        nuevo := left(CASE r.contype
            WHEN 'p' THEN 'pk_' || r.tabla
            WHEN 'f' THEN 'fk_' || r.tabla || '_' || r.cols
            WHEN 'u' THEN 'uk_' || r.tabla || '_' || r.cols
            ELSE 'ck_' || r.tabla || '_' || r.cols END, 63);
        IF r.conname <> nuevo THEN
            EXECUTE format('ALTER TABLE %%I RENAME CONSTRAINT %%I TO %%I',
                           r.tabla, r.conname, nuevo);
        END IF;
    END LOOP;
    -- Índices que no pertenecen a una restricción (los de las FK y los
    -- «_like» de los varchar únicos para búsquedas con LIKE).
    FOR r IN
        SELECT i.relname AS indice, t.relname AS tabla,
               (SELECT string_agg(a.attname, '_' ORDER BY k.ord)
                  FROM unnest(x.indkey::int2[]) WITH ORDINALITY AS k(num, ord)
                  JOIN pg_attribute a
                    ON a.attrelid = x.indrelid AND a.attnum = k.num) AS cols,
               EXISTS (SELECT 1 FROM unnest(x.indclass) AS oc(oid)
                         JOIN pg_opclass o ON o.oid = oc.oid
                        WHERE o.opcname LIKE '%%pattern_ops') AS es_like
          FROM pg_index x
          JOIN pg_class i ON i.oid = x.indexrelid
          JOIN pg_class t ON t.oid = x.indrelid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = current_schema()
           AND t.relname = ANY (%(tablas)s)
           AND NOT EXISTS (SELECT 1 FROM pg_constraint c
                            WHERE c.conindid = x.indexrelid)
    LOOP
        nuevo := left('ix_' || r.tabla || '_' || r.cols
                      || CASE WHEN r.es_like THEN '_like' ELSE '' END, 63);
        IF r.indice <> nuevo THEN
            EXECUTE format('ALTER INDEX %%I RENAME TO %%I', r.indice, nuevo);
        END IF;
    END LOOP;
    -- Secuencias de las claves primarias (identity): sq_<tabla>_<columna>.
    FOR r IN
        SELECT s.relname AS secuencia, t.relname AS tabla, a.attname AS col
          FROM pg_depend d
          JOIN pg_class s ON s.oid = d.objid AND s.relkind = 'S'
          JOIN pg_class t ON t.oid = d.refobjid
          JOIN pg_attribute a
            ON a.attrelid = t.oid AND a.attnum = d.refobjsubid
          JOIN pg_namespace n ON n.oid = t.relnamespace
         WHERE n.nspname = current_schema()
           AND t.relname = ANY (%(tablas)s)
           AND d.deptype IN ('a', 'i')
    LOOP
        nuevo := left('sq_' || r.tabla || '_' || r.col, 63);
        IF r.secuencia <> nuevo THEN
            EXECUTE format('ALTER SEQUENCE %%I RENAME TO %%I',
                           r.secuencia, nuevo);
        END IF;
    END LOOP;
END
$$;
""".replace("%(tablas)s", "ARRAY[" + ", ".join(f"'{t}'" for t in TABLAS) + "]") \
   .replace("%%", "%")

VISTAS = """
CREATE VIEW seg_usuario AS
SELECT id AS id_usuario,
       username AS nom_usuario,
       password AS hsh_clave,
       is_superuser AS es_superusuario,
       (CASE WHEN is_active THEN 'A' ELSE 'I' END)::char(1) AS est_registro,
       NULL::varchar(150) AS usu_creacion,
       date_joined AS fec_creacion,
       NULL::varchar(150) AS usu_modificacion,
       NULL::timestamptz AS fec_modificacion
  FROM auth_user;

CREATE VIEW seg_grupo AS
SELECT id AS id_grupo,
       name AS nom_grupo,
       'A'::char(1) AS est_registro,
       NULL::varchar(150) AS usu_creacion,
       NULL::timestamptz AS fec_creacion,
       NULL::varchar(150) AS usu_modificacion,
       NULL::timestamptz AS fec_modificacion
  FROM auth_group;

CREATE VIEW int_usuario_grupo AS
SELECT id AS id_usuario_grupo,
       user_id AS id_usuario,
       group_id AS id_grupo,
       'A'::char(1) AS est_registro,
       NULL::varchar(150) AS usu_creacion,
       NULL::timestamptz AS fec_creacion,
       NULL::varchar(150) AS usu_modificacion,
       NULL::timestamptz AS fec_modificacion
  FROM auth_user_groups;

CREATE VIEW seg_token AS
SELECT key AS cod_token,
       user_id AS id_usuario,
       'A'::char(1) AS est_registro,
       NULL::varchar(150) AS usu_creacion,
       created AS fec_creacion,
       NULL::varchar(150) AS usu_modificacion,
       NULL::timestamptz AS fec_modificacion
  FROM authtoken_token;

CREATE FUNCTION seg_solo_lectura() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'La vista % es de solo lectura: los usuarios, grupos y '
                    'tokens se gestionan en las tablas de Django (auth_*, '
                    'authtoken_token).', TG_TABLE_NAME;
END
$$;

CREATE TRIGGER seg_usuario_solo_lectura INSTEAD OF INSERT OR UPDATE OR DELETE
    ON seg_usuario FOR EACH ROW EXECUTE FUNCTION seg_solo_lectura();
CREATE TRIGGER seg_grupo_solo_lectura INSTEAD OF INSERT OR UPDATE OR DELETE
    ON seg_grupo FOR EACH ROW EXECUTE FUNCTION seg_solo_lectura();
CREATE TRIGGER int_usuario_grupo_solo_lectura INSTEAD OF INSERT OR UPDATE OR
    DELETE ON int_usuario_grupo FOR EACH ROW EXECUTE FUNCTION seg_solo_lectura();
CREATE TRIGGER seg_token_solo_lectura INSTEAD OF INSERT OR UPDATE OR DELETE
    ON seg_token FOR EACH ROW EXECUTE FUNCTION seg_solo_lectura();
"""

QUITAR_VISTAS = """
DROP VIEW IF EXISTS seg_token, int_usuario_grupo, seg_grupo, seg_usuario;
DROP FUNCTION IF EXISTS seg_solo_lectura();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("riesgo", "0017_nombres_er"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("authtoken", "0004_alter_tokenproxy_options"),
    ]

    operations = [
        # Al revertir, los nombres legibles no estorban: Django busca índices
        # y restricciones por columnas, no por nombre.
        migrations.RunSQL(RENOMBRAR, migrations.RunSQL.noop),
        migrations.RunSQL(VISTAS, QUITAR_VISTAS),
    ]
