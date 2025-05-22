from rest_framework.routers import DefaultRouter
from api.views import GithubViewSet


router = DefaultRouter()
router.register('management', GithubViewSet, basename='management')


urlpatterns = router.urls