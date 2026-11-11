"""Etiqueta una ejecución real con la regla de fase2_variable_objetivo.md.

Usa el resultado exacto de cada paso que devuelve la API de jobs de GitHub:
- despliegue_completado (y = 0): workflow exitoso y algún paso de
  despliegue a producción terminó en success.
- despliegue_no_completado (y = 1): el workflow falló y
    · antes_del_despliegue: ningún paso de despliegue terminó bien;
    · en_paso_de_despliegue: el paso que falló es de despliegue;
    · posterior_mismo_job: falló un paso posterior a un despliegue exitoso
      dentro del mismo job.
- excluida_sin_intento: workflow exitoso sin paso de despliegue exitoso.
- excluida_ambigua: falló otro job y el despliegue terminó bien.
- excluida_otro_resultado: cancelada, omitida, pendiente de aprobación…
- excluida_sin_jobs: terminó en failure sin ningún job (startup_failure,
  YAML inválido…): no llegó a arrancar, así que no hubo intento.
- excluida_no_produccion: solo se desplegó (o se intentó desplegar) a un
  entorno no productivo (staging, dev, test, preview, demo, beta…).

Cómo se reconoce un paso de despliegue a producción, por orden de prioridad:
1. El job no está omitido (skipped): sus pasos no cuentan.
2. Entorno: si el job trae `environment` (el script del dataset lo toma del
   YAML), decide si es producción; si no, se usan los nombres del job y del
   paso (PATRON_NO_PRODUCCION).
3. Acción o comando de despliegue conocido en `uses`/`run` del paso
   (también del YAML) o en el nombre por defecto «Run owner/acción@v».
4. Nombre del paso: verbo de despliegue (`patron`) que no sea un paso
   auxiliar (dry-run, versión, URL, instalación, setup, status…).
Las variantes que no despliegan (dry-run, plan, `ansible-playbook
--syntax-check` o `--check`) no cuentan, ni los pasos que GitHub añade
alrededor de una acción sin ejecutarla («Build owner/acción@v» de las
acciones de Docker, «Pre …» y «Post …»).
Si falla un job que declara un entorno no productivo, la ejecución se
excluye como no productiva.
Un despliegue a hosting estático (Cloudflare Pages, Netlify, GitHub Pages,
S3 website, Firebase Hosting, Azure Static Web Apps) no es el despliegue de
una aplicación y no cuenta.

Si el workflow falla antes de cualquier despliegue no se puede saber a qué
entorno iba y se etiqueta como antes_del_despliegue.

"en_paso_de_despliegue" es el único caso con evidencia directa de un fallo
durante el despliegue; las demás son "despliegue no completado".
"""

import re

PATRON_NO_PRODUCCION = (
    r"(?i)demo|stag|\bstg\b|preview|\btest(ing)?\b|\bdev\b|develop|\bqa\b|"
    r"sandbox|\bbeta\b|\buat\b|\bint\b|integration|nightly|canary|playground|"
    # Regla 7: preproducción, aceptación, PR, nombres camelCase
    # («reserveRecAdminTest») y entornos de una sola sigla («at»).
    r"pre-?prod|non-?prod|acceptance|pull.?request|"
    r"(?-i:[a-z](Test|Dev|Stg|Staging|Qa|Uat)\b)|^(at|acc|tst)$"
)
# Acciones (uses) y comandos (run) que despliegan una aplicación.
PATRON_ACCION_DESPLIEGUE = (
    r"(?i)google-github-actions/deploy-(cloudrun|appengine|cloud-functions)|"
    r"aws-actions/amazon-ecs-deploy-task-definition|"
    r"aws-actions/aws-cloudformation-github-deploy|einaregilsson/beanstalk-deploy|"
    r"azure/(webapps-deploy|container-apps-deploy-action|functions-action|"
    r"k8s-deploy|aci-deploy)|akhileshns/heroku-deploy|digitalocean/app_action|"
    r"cloudflare/wrangler-action|easingthemes/ssh-deploy|"
    r"burnett01/rsync-deployments|dawidd6/action-ansible-playbook|"
    r"amondnet/vercel-action|johnbeynon/render-deploy-action|"
    r"\bflyctl deploy\b|\bfly deploy\b|gcloud (run|app|functions) deploy|"
    r"aws ecs update-service|aws lambda update-function-code|\bsam deploy\b|"
    r"\bcdk deploy\b|\b(serverless|sls) deploy\b|\brailway up\b|"
    r"heroku container:release|\bvercel\b[^\n]*(--prod|deploy)|"
    r"\bwrangler (deploy|publish)\b|kubectl (apply|set image|rollout restart)|"
    r"\bhelm (upgrade|install)\b|\bansible-playbook\b|\bterraform apply\b"
)
# Pasos auxiliares que mencionan un despliegue pero no despliegan. «key» es
# auxiliar («Set GitHub Deploy Key»), salvo como medio del despliegue
# («deploy - executing remote ssh commands using ssh key»).
PATRON_AUXILIAR = (
    r"(?i)dry[- ]?run|\bplan\b|status|summary|notif|comment|version|\burl\b|"
    r"set ?up|install|health|validate|check|\bwait|undeploy|"
    r"(?<!using )(?<!using ssh )\bkey\b|"
    r"_env\b|confirm|prepa|login|credential|cache|artifact|lint|"
    r"--help|\bwhoami\b|matrix"
)
# Variantes que no despliegan (Ansible: comprobación de sintaxis o modo check).
PATRON_NO_DESPLIEGA = r"(?i)dry[- ]?run|\bplan\b|--syntax-check|--check\b|--list-(hosts|tasks)"
# Pasos que GitHub añade alrededor de una acción y que no la ejecutan:
# «Build owner/acción@v» construye la imagen de una acción de Docker al
# empezar el job (se ejecuta aunque el paso real se omita con `if:`), y
# «Pre …» / «Post …» son la preparación y la limpieza de otro paso.
PATRON_PASO_DE_GITHUB = r"^(Build \S+/\S+@\S+|Pre |Post )"
# Hosting estático: no es el despliegue de una aplicación.
PATRON_HOSTING_ESTATICO = (
    r"(?i)cloudflare pages|pages deploy|pages-action|netlify|github pages|"
    r"gh-pages|deploy-pages|static (site|web)|\bs3 (sync|bucket|website)\b|"
    r"aws s3 (sync|cp)|firebase[^\n]*hosting|action-hosting-deploy|\bsurge\b|"
    r"static-web-apps-deploy"
)


def _pasos_ordenados(jobs):
    ordenados = sorted(jobs, key=lambda j: (j.get("started_at") or "",
                                            j.get("id") or 0))
    for job in ordenados:
        for paso in sorted(job.get("steps") or [],
                           key=lambda p: p.get("number") or 0):
            yield job, paso


def etiquetar_ejecucion(conclusion, jobs, patron,
                        patron_no_produccion=PATRON_NO_PRODUCCION):
    verbo = re.compile(patron)
    no_produccion = re.compile(patron_no_produccion)
    accion = re.compile(PATRON_ACCION_DESPLIEGUE)
    auxiliar = re.compile(PATRON_AUXILIAR)
    estatico = re.compile(PATRON_HOSTING_ESTATICO)
    pasos = list(_pasos_ordenados(jobs))

    def es_despliegue(job, paso):
        if job.get("conclusion") == "skipped":
            return False
        nombre = paso.get("name") or ""
        if re.match(PATRON_PASO_DE_GITHUB, nombre):
            return False
        codigo = f"{paso.get('uses') or ''}\n{paso.get('run') or ''}"
        # El nombre del job también cuenta («Deploy to Cloudflare Pages» con
        # un paso «Deploy» que usa wrangler-action).
        if estatico.search(f"{job.get('name') or ''}\n{nombre}\n{codigo}"):
            return False
        if accion.search(codigo) or accion.search(nombre):
            return not re.search(PATRON_NO_DESPLIEGA, f"{nombre}\n{codigo}")
        return bool(verbo.search(nombre)) and not auxiliar.search(nombre)

    def a_produccion(job, paso):
        entorno = job.get("environment")
        if entorno:
            return not no_produccion.search(str(entorno))
        return not no_produccion.search(
            f"{job.get('name') or ''} {paso.get('name') or ''}")

    despliegues = [(j, p) for j, p in pasos if es_despliegue(j, p)
                   and p.get("conclusion") in ("success", "failure")]
    despliegues_ok = [(j, p) for j, p in despliegues if a_produccion(j, p)
                      and p.get("conclusion") == "success"]
    a_produccion_ejecutado = any(a_produccion(j, p) for j, p in despliegues)
    solo_no_produccion = bool(despliegues) and not a_produccion_ejecutado
    fallido = next(((j, p) for j, p in pasos
                    if p.get("conclusion") == "failure"), None)
    if fallido:
        paso_fallido = f"{fallido[0].get('name')} / {fallido[1].get('name')}"
    else:
        job_fallido = next((j for j in jobs
                            if j.get("conclusion") == "failure"), None)
        paso_fallido = job_fallido.get("name", "") if job_fallido else ""

    resultado = {"despliegue_ejecutado": bool(despliegues_ok),
                 "paso_fallido": paso_fallido, "subtipo_etiqueta": ""}

    if conclusion == "success":
        resultado["etiqueta"] = (
            "despliegue_completado" if despliegues_ok
            else "excluida_no_produccion" if solo_no_produccion
            else "excluida_sin_intento")
        return resultado
    if conclusion != "failure":
        resultado["etiqueta"] = "excluida_otro_resultado"
        return resultado
    if not jobs:
        resultado["etiqueta"] = "excluida_sin_jobs"
        return resultado

    fallo_en_despliegue = bool(fallido) and es_despliegue(*fallido)
    if fallo_en_despliegue and not a_produccion(*fallido):
        resultado["etiqueta"] = "excluida_no_produccion"
        return resultado
    if fallo_en_despliegue:
        subtipo = "en_paso_de_despliegue"
    elif fallido and any(
            j.get("id") == fallido[0].get("id")
            and (p.get("number") or 0) < (fallido[1].get("number") or 0)
            for j, p in despliegues_ok):
        subtipo = "posterior_mismo_job"
    elif despliegues_ok:
        resultado["etiqueta"] = "excluida_ambigua"
        return resultado
    elif solo_no_produccion:
        resultado["etiqueta"] = "excluida_no_produccion"
        return resultado
    elif fallido and fallido[0].get("environment") and no_produccion.search(
            str(fallido[0]["environment"])):
        # Falló un job que declara un entorno no productivo (p. ej. «Deploy
        # Dev» con environment DEV): el intento iba a ese entorno.
        resultado["etiqueta"] = "excluida_no_produccion"
        return resultado
    else:
        subtipo = "antes_del_despliegue"
    resultado["etiqueta"] = "despliegue_no_completado"
    resultado["subtipo_etiqueta"] = subtipo
    return resultado
