from django_filters import rest_framework as filters
from recipes.models import Recipe


class RecipeFilter(filters.FilterSet):
    """Класс для фильтрации рецептов."""

    is_favorited = filters.BooleanFilter(method='filter_by_favorite')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_by_shopping_cart')
    author = filters.NumberFilter(field_name='author')

    class Meta:
        model = Recipe
        fields = ['author',]

    def filter_by_favorite(self, queryset, name, value):
        """Фильтрация рецептов по избранному."""
        current_user = self.request.user
        if value and current_user.is_authenticated:
            return queryset.filter(favorites__user=current_user)
        return queryset

    def filter_by_shopping_cart(self, queryset, name, value):
        """Фильтрация рецептов по списку покупок."""
        current_user = self.request.user
        if value and current_user.is_authenticated:
            return queryset.filter(shopping_carts__user=current_user)
        return queryset
