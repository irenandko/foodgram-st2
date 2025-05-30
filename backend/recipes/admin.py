from django.contrib import admin
from .models import (
    Ingredient, Recipe, IngredientInRecipe, Favorites, ShoppingCart
)
from django.db.models import Count


class RecipeIngredientTab(admin.TabularInline):
    model = IngredientInRecipe
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'favorites_count')
    list_filter = ('author', 'name')
    search_fields = ('name', 'author__username')
    inlines = (RecipeIngredientTab,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            total_favorites=Count('favorites')
        )

    @admin.display(description="В избранном")
    def favorites_count(self, obj):
        return obj.total_favorites


@admin.register(Favorites)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe')
    search_fields = ('user__username', 'recipe__name')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
