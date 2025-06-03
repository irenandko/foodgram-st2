from rest_framework import status, viewsets
from djoser.views import UserViewSet
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404, redirect
from django_filters.rest_framework import DjangoFilterBackend
from django.urls import reverse
from users.models import CustomUser, Subscription
from recipes.models import Recipe, Ingredient, Favorites, ShoppingCart
from .serializers import (
    AvatarUpdateSerializer,
    SubscribeActionSerializer,
    AuthorDetailSerializer,
    RecipeDetailSerializer,
    RecipeCreateUpdateSerializer,
    IngredientSerializer,
    FavoriteSerializer,
    ShoppingCartSerializer,
    ShortRecipeSerializer
)
from recipes.shopping_list import deliver_shopping_list
from .permissions import IsAuthorOrReadOnly
from .filters import RecipeFilter
from .constants import MAX_PAGE, PAGE_SIZE


class UserPagination(PageNumberPagination):
    page_size = PAGE_SIZE
    page_size_query_param = 'limit'
    max_page_size = MAX_PAGE

    def get_ordering(self, request, queryset, view):
        return ['id']


class UserProfileViewSet(UserViewSet):

    queryset = CustomUser.objects.all().order_by('id')
    lookup_field = 'id'
    lookup_url_kwarg = 'id'
    pagination_class = UserPagination

    def get_permissions(self):
        protected_actions = [
            'me',
            'update_profile_avatar',
            'get_subscribed_authors_list',
            'manage_subscription',
            'get_user_info',
        ]
        if self.action in protected_actions:
            return [IsAuthenticated()]

        if self.action == 'create':
            return [AllowAny()]
        return [AllowAny()]

    def perform_create(self, serializer):
        serializer.save()
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED)

    @action(methods=['get'],
            detail=False,
            url_path='me',
            url_name='get_user_info',)
    def get_user_info(self, request):
        """Отображает личные данные текущего пользователя."""
        serializer = self.get_serializer(request.user,
                                         context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=['put', 'delete'],
            detail=False,
            url_path='me/avatar',)
    def update_profile_avatar(self, request):
        """Реализует обновление и удаление аватара пользователя."""
        user = request.user

        if request.method == 'PUT':
            serializer = AvatarUpdateSerializer(
                user,
                data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)

        if user.avatar:
            user.avatar.delete(save=True)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False,
            url_path='subscriptions',
            url_name='get_subscribed_authors')
    def get_subscribed_authors_list(self, request):
        """Получает список авторов, на которых подписан пользователь."""
        authors = CustomUser.objects.filter(
            authors__user=request.user).order_by('id')
        page = self.paginate_queryset(authors)
        serializer = AuthorDetailSerializer(
            page,
            many=True,
            context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    def _handle_subscription(self, request, author_id, action):
        """Обрабатывает подписку/отписку."""
        author = get_object_or_404(CustomUser, pk=author_id)

        if action == 'subscribe':
            serializer = SubscribeActionSerializer(
                data={'user': request.user.id, 'author': author.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            author_serializer = AuthorDetailSerializer(
                author, context={'request': request})
            return Response(author_serializer.data,
                            status=status.HTTP_201_CREATED)

        try:
            subscription = request.user.subscribers.get(author=author)
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Subscription.DoesNotExist:
            return Response(
                {'error': 'Подписка не найдена'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(methods=['post', 'delete'],
            detail=True,
            url_path='subscribe',
            url_name='subscription')
    def manage_subscription(self, request, id=None):
        """Управляет подпиской на автора."""
        action = 'subscribe' if request.method == 'POST' else 'unsubscribe'
        return self._handle_subscription(request, id, action)


class RecipePagination(PageNumberPagination):
    page_size = PAGE_SIZE
    page_size_query_param = 'limit'


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    filter_backends = (DjangoFilterBackend, )
    filterset_fields = ('name',)

    def get_queryset(self):
        search_field = self.request.query_params.get('name', '')
        if search_field:
            return self.queryset.filter(name__icontains=search_field)
        return self.queryset


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthorOrReadOnly]
    filterset_class = RecipeFilter
    pagination_class = RecipePagination

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
            recipe_serializer = ShortRecipeSerializer(recipe, context=context)
            return Response(recipe_serializer.data,
                            status=status.HTTP_201_CREATED)

        if operation == 'remove':
            if serializer_class == FavoriteSerializer:
                model = Favorites
            else:
                model = ShoppingCart
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
    return redirect(reverse('api:recipe_detail', kwargs={'pk': recipe.id}))
