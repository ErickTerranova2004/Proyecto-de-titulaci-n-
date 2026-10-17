"""Etiqueta una ejecución real con la regla de fase2_variable_objetivo.md.

Usa el resultado exacto de cada paso que devuelve la API de jobs de GitHub:
- despliegue_completado (y = 0): workflow exitoso y algún paso de
  despliegue terminó en success.
- despliegue_no_completado (y = 1): el workflow falló y
    · antes_del_despliegue: ningún paso de despliegue terminó bien;
    · en_paso_de_despliegue: el paso que falló es de despliegue;
    · posterior_mismo_job: falló un paso posterior a un despliegue exitoso
      dentro del mismo job.
- excluida_sin_intento: workflow exitoso sin paso de despliegue exitoso.
- excluida_ambigua: falló otro job y el despliegue terminó bien.
- excluida_otro_resultado: cancelada, omitida, pendiente de aprobación…

"en_paso_de_despliegue" es el único caso con evidencia directa de un fallo
durante el despliegue; las demás son "despliegue no completado".
"""

import re


def _pasos_ordenados(jobs):
    ordenados = sorted(jobs, key=lambda j: (j.get("started_at") or "",
                                            j.get("id") or 0))
    for job in ordenados:
        for paso in sorted(job.get("steps") or [],
                           key=lambda p: p.get("number") or 0):
            yield job, paso


def etiquetar_ejecucion(conclusion, jobs, patron):
    regex = re.compile(patron)
    pasos = list(_pasos_ordenados(jobs))
    despliegues_ok = [(j, p) for j, p in pasos
                      if regex.search(p.get("name") or "")
                      and p.get("conclusion") == "success"]
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
        resultado["etiqueta"] = ("despliegue_completado" if despliegues_ok
                                 else "excluida_sin_intento")
        return resultado
    if conclusion != "failure":
        resultado["etiqueta"] = "excluida_otro_resultado"
        return resultado

    if fallido and regex.search(fallido[1].get("name") or ""):
        subtipo = "en_paso_de_despliegue"
    elif fallido and any(
            j.get("id") == fallido[0].get("id")
            and (p.get("number") or 0) < (fallido[1].get("number") or 0)
            for j, p in despliegues_ok):
        subtipo = "posterior_mismo_job"
    elif despliegues_ok:
        resultado["etiqueta"] = "excluida_ambigua"
        return resultado
    else:
        subtipo = "antes_del_despliegue"
    resultado["etiqueta"] = "despliegue_no_completado"
    resultado["subtipo_etiqueta"] = subtipo
    return resultado
