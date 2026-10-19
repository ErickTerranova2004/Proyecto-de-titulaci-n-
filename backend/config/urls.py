from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import DefaultRouter

from riesgo import views

router = DefaultRouter()
router.register("predicciones", views.PrediccionViewSet,
                basename="prediccion")
router.register("modelos", views.VersionModeloViewSet, basename="modelo")
router.register("repositorios", views.RepositorioViewSet,
                basename="repositorio")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", obtain_auth_token),
    path("api/yo/", views.yo),
    path("api/integraciones/", views.integraciones),
    path("api/", include(router.urls)),
]
