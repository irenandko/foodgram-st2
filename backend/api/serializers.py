from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from djoser.serializers import UserSerializer
from rest_framework.exceptions import ValidationError
from users.models import CustomUser, Subscription
from recipes.models import (Ingredient,
                            Recipe,
                            IngredientInRecipe,
                            Favorites,
                            ShoppingCart)
from .constants import (MAX_AMOUNT,
                        MIN_AMOUNT,
                        MIN_COOK_TIME,
                        MAX_COOK_TIME)


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
            return instance.subscribers.filter(user=request.user).exists()
        return False


class AvatarUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления аватара пользователя."""

    avatar = Base64ImageField()

    class Meta:
        model = CustomUser
        fields = ('avatar',)


class SubscribeActionSerializer(serializers.Serializer):
    """Сериализатор работы с подписками."""

    user = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all())
    author = serializers.PrimaryKeyRelatedField(
        queryset=CustomUser.objects.all())

    class Meta:
        model = Subscription
        fields = ('author',)
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Subscription.objects.all(),
                fields=('user', 'author'),
                message='Вы уже подписаны на этого пользователя'
            )
        ]

    def validate(self, attrs):
        if attrs['user'] == attrs['author']:
            raise serializers.ValidationError(
                {'author': 'Нельзя подписаться на себя.'}
            )
        return attrs

    def create(self, validated_data):
        user = validated_data['user']
        author = validated_data['author']
        Subscription.objects.create(user=user, author=author)
        return validated_data


class AuthorDetailSerializer(UserProfileSerializer):
    """Сериализатор для отображения автора с рецептами."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = UserProfileSerializer.Meta.fields + (
            'recipes', 'recipes_count'
        )

    def get_recipes(self, author):
        request = self.context.get('request')
        recipes = author.recipes.all()

        if limit := request.query_params.get('recipes_limit'):
            try:
                recipes = recipes[:int(limit)]
            except ValueError:
                pass
        return ShortRecipeSerializer(recipes,
                                     many=True,
                                     context=self.context).data

    def get_recipes_count(self, obj):
        if hasattr(obj, 'recipes_count'):
            return obj.recipes_count
        return obj.recipes.count()


class ShortRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для краткого представления рецепта."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для представления данных ингредиента."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингридиентов в рецепте."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    name = serializers.CharField(source='ingredient.name', read_only=True)
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit', read_only=True
    )
    amount = serializers.IntegerField(
        min_value=MIN_AMOUNT,
        max_value=MAX_AMOUNT
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'amount', 'measurement_unit')


class RecipeDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детального представления рецепта."""

    author = UserProfileSerializer(read_only=True)
    image = Base64ImageField()
    ingredients = RecipeIngredientSerializer(many=True,
                                             source='ingredients_in_recipe')
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'author', 'text', 'cooking_time',
            'ingredients', 'is_favorited', 'is_in_shopping_cart'
        )
        read_only_fields = fields

    def _check_relation(self, obj, relation_field):
        user = self.context['request'].user
        return user.is_authenticated and getattr(
            obj, relation_field
        ).filter(user=user).exists()

    def get_is_favorited(self, obj):
        return self._check_relation(obj, 'in_favorites')

    def get_is_in_shopping_cart(self, obj):
        return self._check_relation(obj, 'in_shopping_carts')


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания и обновления рецептов."""

    image = Base64ImageField()
    cooking_time = serializers.IntegerField(
        min_value=MIN_COOK_TIME,
        max_value=MAX_COOK_TIME
    )
    ingredients = RecipeIngredientSerializer(many=True)

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time', 'text', 'ingredients')

    def _validate_ingredients(self, ingredients):
        if not ingredients:
            raise ValidationError(
                {'ingredients': ['Необходим хотя бы один ингредиент']}
            )

        ids = [ing['id'] for ing in ingredients]
        if len(ids) != len(set(ids)):
            raise ValidationError(
                {'ingredients': ['Ингредиенты должны быть уникальными']}
            )

    def validate(self, data):
        ingredients = self.initial_data.get('ingredients', [])
        self._validate_ingredients(ingredients)

        image = data.get('image')
        if image is None or image == '':
            raise serializers.ValidationError(
                {'image': 'Поле "Фото рецепта" не может быть пустым.'})

        return data

    def _set_recipe_ingredients(self, recipe, ingredients_data):
        recipe.ingredients_in_recipe.all().delete()
        IngredientInRecipe.objects.bulk_create([
            IngredientInRecipe(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ])

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = super().create(validated_data)
        self._set_recipe_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        instance = super().update(instance, validated_data)
        if ingredients_data is not None:
            self._set_recipe_ingredients(instance, ingredients_data)
        return instance

    def to_representation(self, instance):
        return RecipeDetailSerializer(
            instance,
            context=self.context
        ).data


class UserRecipeActionSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для действий с рецептами."""

    def validate(self, data):
        if data['user'] == data['recipe'].author:
            raise serializers.ValidationError(
                'Собственный рецепт нельзя обрабатывать'
            )
        return data

    def to_representation(self, instance):
        return ShortRecipeSerializer(
            instance.recipe,
            context=self.context
        ).data


class FavoriteSerializer(UserRecipeActionSerializer):
    """Сериализатор для избранных рецептов."""

    class Meta:
        model = Favorites
        fields = ('user', 'recipe')
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=Favorites.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в избранном'
            )
        ]


class ShoppingCartSerializer(serializers.ModelSerializer):
    """Сериализатор для списка покупок."""

    class Meta:
        model = ShoppingCart
        fields = ('user', 'recipe')
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=ShoppingCart.objects.all(),
                fields=('user', 'recipe'),
                message='Рецепт уже в корзине'
            )
        ]
