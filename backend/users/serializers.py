from rest_framework import serializers
from djoser.serializers import UserSerializer
from users.models import CustomUser
from drf_extra_fields.fields import Base64ImageField


class CustomUserSerializer(UserSerializer):
    """Сериализатор для отображения данных пользователя."""

    avatar = Base64ImageField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'avatar',
            'is_subscribed',
        )
        read_only_fields = fields

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.subscriptions.filter(user=request.user).exists()
        return False


class AvatarSerializer(UserSerializer):
    """Сериализатор отдельно для фото профиля (обновление)."""

    avatar = Base64ImageField()

    class Meta:
        model = CustomUser
        fields = ('avatar',)