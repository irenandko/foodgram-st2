from django.urls import include, path
from rest_framework import routers
from .views import (UserProfileViewSet,
                    RecipeViewSet,
                    IngredientViewSet,)

router = routers.DefaultRouter()

router.register("users", UserProfileViewSet, basename="users")
router.register("ingredients", IngredientViewSet, basename="ingredients")
router.register("recipes", RecipeViewSet, basename="recipes")

urlpatterns = [
    path("", include(router.urls)),
    path("auth/", include("djoser.urls.authtoken")),
]
