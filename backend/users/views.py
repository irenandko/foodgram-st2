from rest_framework import status
from djoser.views import UserViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.shortcuts import get_object_or_404
from users.models import CustomUser, Subscription
from users.serializers import (
    AvatarUpdateSerializer,
    SubscribeActionSerializer,
    AuthorDetailSerializer,
)


class UserProfileViewSet(UserViewSet):

    lookup_field = 'id'
    lookup_url_kwarg = 'id'

    def get_permissions(self):
        protected_actions = [
            'me',
            'update_profile_avatar',
            'get_subscribed_authors_list',
            'manage_subscription'
        ]
        if self.action in protected_actions:
            return [IsAuthenticated()]

        if self.action == 'create':
            return [AllowAny()]
        return [AllowAny()]

    def perform_create(self, serializer):
        user = serializer.save()
        return Response({
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
        }, status=status.HTTP_201_CREATED)

    @action(methods=['get'],
            detail=False,
            url_path='me',
            url_name='get_user_info')
    def get_user_info(self, request):
        """Отображает личные данные текущего пользователя."""
        if not request.user.is_authenticated:
            return Response(status=status.HTTP_401_UNAUTHORIZED)
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
                data=request.data,
                partial=True
            )
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
            subscribers__user=request.user)
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
            if request.user == author:
                return Response(
                    {'error': 'Нельзя подписаться на себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = SubscribeActionSerializer(
                data={'user': request.user.id, 'author': author.id},
                context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        deleted, _ = Subscription.objects.filter(
            user=request.user,
            author=author
        ).delete()

        if not deleted:
            return Response(
                {'error': 'Подписка не найдена'},
                status=status.HTTP_404_NOT_FOUND
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(methods=['post', 'delete'],
            detail=True,
            url_path='subscribe',
            url_name='subscription')
    def manage_subscription(self, request, id=None):
        """Управляет подпиской на автора."""
        action = 'subscribe' if request.method == 'POST' else 'unsubscribe'
        return self._handle_subscription(request, id, action)
