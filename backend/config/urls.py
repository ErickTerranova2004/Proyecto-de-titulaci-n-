from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from riesgo import views, views_gestion

router = DefaultRouter()
router.register("predicciones", views.PrediccionViewSet,
                basename="prediccion")
router.register("modelos", views.VersionModeloViewSet, basename="modelo")
router.register("repositorios", views.RepositorioViewSet,
                basename="repositorio")
router.register("asignaciones", views.AsignacionViewSet,
                basename="asignacion")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", obtain_auth_token),
    path("api/yo/", views.yo),
    path("api/integraciones/", views.integraciones),
    path("api/resumen-admin/", views.resumen_admin),
    # Gestión de usuarios, accesos y workflows (solo administrador).
    path("api/gestion/usuarios/", views_gestion.usuarios),
    path("api/gestion/usuarios/<int:pk>/", views_gestion.usuario_detalle),
    path("api/gestion/usuarios/<int:pk>/repositorios/",
         views_gestion.usuario_repositorios),
    path("api/gestion/workflows/", views_gestion.workflows),
    path("api/gestion/workflows/validar/", views_gestion.workflows_validar),
    path("api/gestion/workflows/<int:pk>/", views_gestion.workflow_detalle),
    path("api/gestion/workflows/<int:pk>/comprobar/",
         views_gestion.workflow_comprobar),
    path("api/", include(router.urls)),
]