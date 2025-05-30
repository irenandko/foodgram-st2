from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse
from api.permissions import IsAuthorOrReadOnly

from recipes.filters import RecipeFilter
from recipes.serializers import (
    RecipeDetailSerializer,
    RecipeCreateUpdateSerializer,
    RecipeIngredientSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer
)
from recipes.models import Recipe, Ingredient, Favorites, ShoppingCart
from recipes.shopping_list import deliver_shopping_list


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = RecipeIngredientSerializer
    pagination_class = None
    permission_classes = [AllowAny]

    def get_queryset(self):
        search_term = self.request.query_params.get('name', '')
        if search_term:
            return self.queryset.filter(name__icontains=search_term)
        return self.queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthorOrReadOnly]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateUpdateSerializer
        return RecipeDetailSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def _handle_relation(self, request,
                         recipe_id, serializer_class, operation):
        recipe = get_object_or_404(Recipe, id=recipe_id)
        context = {'request': request}

        if operation == 'add':
            data = {'user': request.user.id, 'recipe': recipe.id}
            serializer = serializer_class(data=data, context=context)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif operation == 'remove':
            if serializer_class == FavoriteSerializer:
                model = Favorites
            else:
                ShoppingCart
            relation = model.objects.filter(user=request.user, recipe=recipe)
            if not relation.exists():
                return Response(
                    {'errors': 'Рецепт не найден в списке.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            relation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        methods=['get'],
        permission_classes=[IsAuthenticated],
        detail=False
    )
    def download_shopping_cart(self, request):
        return deliver_shopping_list(request.user)

    @action(
        methods=['get'],
        url_path='get-link',
        detail=True
    )
    def get_short_link(self, request, pk=None):
        relative_path = reverse('recipes:recipe_short_link', args=[pk])
        full_url = request.build_absolute_uri(relative_path)
        return Response({'short-link': full_url})

    @action(
        methods=['post'],
        detail=True,
        url_path='favorite'
    )
    def add_favorite(self, request, pk):
        return self._handle_relation(
            request,
            pk,
            FavoriteSerializer,
            'add'
        )

    @action(
        methods=['post'],
        detail=True,
        url_path='shopping_cart'
    )
    def add_shopping_cart(self, request, pk):
        return self._handle_relation(
            request,
            pk,
            ShoppingCartSerializer,
            'add'
        )

    @add_favorite.mapping.delete
    def delete_favorite(self, request, pk):
        return self._handle_relation(
            request,
            pk,
            FavoriteSerializer,
            'remove'
        )

    @add_shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        return self._handle_relation(
            request,
            pk,
            ShoppingCartSerializer,
            'remove'
        )


def copy_short_link(request, pk):
    recipe = get_object_or_404(Recipe, id=pk)
    return redirect(f'/recipes/{recipe.id}/')
