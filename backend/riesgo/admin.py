from django.contrib import admin
from django.utils import timezone

from riesgo.models import (AccesoRepositorio, Commit, DecisionDespliegue,
                           EjecucionWorkflow,
                           Prediccion, Repositorio, VersionModelo, Workflow)


class AccesoInline(admin.TabularInline):
    model = AccesoRepositorio
    fk_name = "repositorio"
    extra = 0
    autocomplete_fields = ["usuario"]
    readonly_fields = ["asignado_por", "asignado_en"]


@admin.register(Repositorio)
class RepositorioAdmin(admin.ModelAdmin):
    list_display = ["nombre_completo", "github_id"]
    search_fields = ["nombre_completo"]
    inlines = [AccesoInline]

    def save_formset(self, request, form, formset, change):
        for acceso in formset.save(commit=False):
            if acceso.asignado_por_id is None:
                acceso.asignado_por = request.user
            acceso.save()
        formset.save_m2m()
        for eliminado in formset.deleted_objects:
            eliminado.delete()


@admin.register(AccesoRepositorio)
class AccesoRepositorioAdmin(admin.ModelAdmin):
    list_display = ["usuario", "repositorio", "asignado_por", "asignado_en"]
    autocomplete_fields = ["usuario", "repositorio"]
    readonly_fields = ["asignado_por"]

    def save_model(self, request, obj, form, change):
        if obj.asignado_por_id is None:
            obj.asignado_por = request.user
        super().save_model(request, obj, form, change)


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ["repositorio", "path", "despliegue_validado",
                    "disponible_github", "validado_por", "validado_en"]
    list_filter = ["despliegue_validado", "disponible_github"]
    search_fields = ["repositorio__nombre_completo", "path"]
    autocomplete_fields = ["repositorio"]
    readonly_fields = ["validado_por", "validado_en"]

    def save_model(self, request, obj, form, change):
        if obj.despliegue_validado and "despliegue_validado" in \
                form.changed_data:
            obj.validado_por = request.user
            obj.validado_en = timezone.now()
        super().save_model(request, obj, form, change)


@admin.register(Commit)
class CommitAdmin(admin.ModelAdmin):
    list_display = ["repositorio", "sha", "fecha", "archivos_modificados",
                    "adiciones", "eliminaciones"]
    search_fields = ["sha"]


@admin.register(EjecucionWorkflow)
class EjecucionWorkflowAdmin(admin.ModelAdmin):
    list_display = ["run_id", "run_attempt", "workflow", "conclusion",
                    "etiqueta", "subtipo_etiqueta"]
    list_filter = ["etiqueta", "conclusion"]


@admin.register(DecisionDespliegue)
class DecisionDespliegueAdmin(admin.ModelAdmin):
    list_display = ["prediccion", "decision", "usuario", "creada_en"]
    list_filter = ["decision"]
    readonly_fields = ["prediccion", "usuario", "decision", "comentario",
                       "creada_en", "fecha_limite",
                       "vista_por_desarrollador_en", "cumplida_en",
                       "prediccion_respuesta", "respuesta_desarrollador"]


@admin.register(VersionModelo)
class VersionModeloAdmin(admin.ModelAdmin):
    list_display = ["version", "nombre_modelo", "activo", "registrado_en"]


@admin.register(Prediccion)
class PrediccionAdmin(admin.ModelAdmin):
    list_display = ["id", "workflow", "nivel", "probabilidad", "usuario",
                    "creada_en", "ejecucion_real"]
    list_filter = ["nivel", "version_modelo"]
    readonly_fields = [f.name for f in Prediccion._meta.fields]
