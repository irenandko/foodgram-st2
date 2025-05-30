from rest_framework import serializers, status
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserSerializer
from users.models import CustomUser, Subscription
from recipes.models import Recipe


class UserProfileSerializer(UserSerializer):
    """Сериализатор для отображения профиля пользователя."""

    avatar = Base64ImageField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = UserSerializer.Meta.fields + ('avatar', 'is_subscribed')

    def get_is_subscribed(self, instance):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return instance.authors.filter(user=request.user).exists()
        return False


class AvatarUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления аватара пользователя."""

    avatar = Base64ImageField()

    class Meta:
        model = CustomUser
        fields = ('avatar',)


class SubscribeActionSerializer(serializers.ModelSerializer):
    """Сериализатор для создания подписки на автора."""

    class Meta:
        model = Subscription
        fields = ('user', 'author',)
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('user', 'author'),
                message='Вы уже подписаны на этого пользователя'
            )
        ]

    def validate(self, attrs):
        if attrs['user'] == attrs['author']:
            raise serializers.ValidationError('Подписка на себя невозможна')
        return attrs

    def to_representation(self, instance):
        return AuthorDetailSerializer(
            instance.author,
            context=self.context
        ).data


class AuthorDetailSerializer(UserProfileSerializer):
    """Сериализатор для отображения автора с рецептами."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(source='recipes.count',
                                             read_only=True)

    class Meta:
        model = CustomUser
        fields = UserProfileSerializer.Meta.fields + (
            'recipes', 'recipes_count'
        )

    def get_recipes(self, author):
        request = self.context.get('request')
        recipes = author.recipes.all()

        if limit := request.query_params.get('recipes_limit'):
            if limit.isdigit():
                recipes = recipes[:int(limit)]

        return ShortRecipeSerializer(
            recipes,
            many=True,
            context=self.context
        ).data


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого представления рецепта."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
