from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from rest_framework.pagination import PageNumberPagination
from users.models import CustomUser, Subscription
from users.serializers import (
    UserProfileSerializer,
    AvatarUpdateSerializer,
    SubscribeActionSerializer,
    AuthorDetailSerializer,
)
from django.db import IntegrityError


class UserProfileViewSet(viewsets.GenericViewSet,
                         mixins.RetrieveModelMixin,
                         mixins.ListModelMixin):
    """Набор представлений для профилей пользователей."""

    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustomUser.objects.all()

    @action(methods=['get'],
            detail=False,
            url_path='me',
            url_name='get_personal_info')
    def get_personal_info(self, request):
        """Отображает личные данные текущего пользователя."""
        current_user_info = UserProfileSerializer(
            request.user,
            context={'request': request})
        return Response(current_user_info.data,
                        status=status.HTTP_200_OK)

    @action(methods=['put', 'delete'],
            detail=False,
            url_path='me/avatar',
            url_name='manage_profile_avatar')
    def manage_profile_avatar(self, request):
        """Реализует обновление и удаление аватара пользователя."""
        active_profile = request.user

        if request.method == 'PUT':

            profile_serializer = AvatarUpdateSerializer(
                active_profile,
                data=request.data,
                partial=True)
            profile_serializer.is_valid(raise_exception=True)
            profile_serializer.save()
            return Response(profile_serializer.data, status=status.HTTP_200_OK)

        try:
            active_profile.avatar.delete(save=True)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            return Response({"error": str(e)},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    class AuthorPagination(PageNumberPagination):
        page_size = 9

    @action(detail=False,
            url_path='subscriptions',
            url_name='get_subscribed_authors')
    def get_subscribed_authors_list(self, request):
        """Получает список авторов, на которых подписан пользователь."""
        subscribed_list = CustomUser.objects.filter(
            subscribers__user=request.user
        )
        paginator = self.AuthorPagination()
        paginated_result = paginator.paginate_queryset(subscribed_list,
                                                       request)
        author_serializer = AuthorDetailSerializer(
            paginated_result,
            many=True,
            context={'request': request})
        return paginator.get_paginated_response(author_serializer.data)

    def perform_subscription(self, request,
                             author_id, action_type='subscribe'):
        """Выполняет действие подписки или отписки."""

        try:
            author = get_object_or_404(CustomUser, pk=author_id)
            if action_type == 'subscribe':
                related_serializer = SubscribeActionSerializer(
                    data={'user': request.user.id, 'author': author.id},
                    context={'request': request})
                related_serializer.is_valid(raise_exception=True)
                related_serializer.save()
                return Response(related_serializer.data,
                                status=status.HTTP_201_CREATED)
            elif action_type == 'unsubscribe':
                deletion_result = Subscription.objects.filter(
                    user=request.user,
                    author=author).delete()
                if deletion_result[0] == 0:
                    return Response({'error': 'Подписка не найдена.'},
                                    status=status.HTTP_404_NOT_FOUND)
                return Response(status=status.HTTP_204_NO_CONTENT)
            else:
                return Response({'error': 'Недопустимый action_type.'},
                                status=status.HTTP_400_BAD_REQUEST)
        except ObjectDoesNotExist:
            return Response({'error': 'Автор не найден.'},
                            status=status.HTTP_404_NOT_FOUND)
        except IntegrityError:
            return Response({'error': 'Вы уже подписаны на этого автора.'},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(methods=['post'],
            detail=True,
            url_path='subscribe',
            url_name='add_subscription')
    def subscribe_to_profile(self, request, pk=None):
        return self.perform_subscription(request, pk,
                                         action_type='subscribe')

    @action(methods=['delete'],
            detail=True,
            url_path='subscribe',
            url_name='remove_profile_subscription')
    def unsubscribe_from_profile(self, request, pk=None):
        return self.perform_subscription(request, pk,
                                         action_type='unsubscribe')
