from rest_framework import serializers
from drf_extra_fields.fields import Base64ImageField
from rest_framework.exceptions import ValidationError
from recipes.models import (Ingredient,
                            Recipe,
                            IngredientInRecipe,
                            Favorites,
                            ShoppingCart)
from users.serializers import UserProfileSerializer, ShortRecipeSerializer


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для представления данных ингредиента."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингридиентов в рецепте."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    name = serializers.StringRelatedField(source='ingredient.name')
    measurement_unit = serializers.StringRelatedField(
        source='ingredient.measurement_unit'
    )
    amount = serializers.IntegerField(
        min_value=1,
        max_value=100
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'amount', 'measurement_unit')


class RecipeDetailSerializer(serializers.ModelSerializer):
    """Сериализатор для детального представления рецепта."""

    author = UserProfileSerializer(read_only=True)
    image = Base64ImageField()
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'name', 'image', 'author', 'text', 'cooking_time',
            'ingredients', 'is_favorited', 'is_in_shopping_cart'
        )
        read_only_fields = fields

    def get_ingredients(self, recipe):
        return [
            {
                'id': item.ingredient.id,
                'name': item.ingredient.name,
                'amount': item.amount,
                'measurement_unit': item.ingredient.measurement_unit
            }
            for item in recipe.ingredients_in_recipe.select_related(
                'ingredient'
            )
        ]

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
        min_value=1,
        max_value=2880
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

    def _update_ingredients(self, recipe, ingredients_data):
        recipe.ingredients_in_recipe.all().delete()
        IngredientInRecipe.objects.bulk_create([
            IngredientInRecipe(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ])

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        self._update_ingredients(recipe, ingredients_data)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', None)
        instance = super().update(instance, validated_data)
        if ingredients_data is not None:
            self._update_ingredients(instance, ingredients_data)
        return instance

    def to_representation(self, instance):
        return RecipeDetailSerializer(
            instance,
            context=self.context
        ).data


class UserRecipeActionSerializer(serializers.ModelSerializer):
    """Базовый сериализатор для действий с рецептами."""

    class Meta:
        abstract = True
        validators = [
            serializers.UniqueTogetherValidator(
                queryset=None,
                fields=('user', 'recipe'),
                message='Действие уже выполнено'
            )
        ]

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

    class Meta(UserRecipeActionSerializer.Meta):
        model = Favorites
        fields = ('user', 'recipe')
        validators = [UserRecipeActionSerializer.Meta.validators[0].__class__(
            queryset=Favorites.objects.all(),
            fields=('user', 'recipe'),
            message='Рецепт уже в избранном'
        )]


class ShoppingCartSerializer(UserRecipeActionSerializer):
    """Сериализатор для списка покупок."""

    class Meta(UserRecipeActionSerializer.Meta):
        model = ShoppingCart
        fields = ('user', 'recipe')
        validators = [UserRecipeActionSerializer.Meta.validators[0].__class__(
            queryset=ShoppingCart.objects.all(),
            fields=('user', 'recipe'),
            message='Рецепт уже в корзине'
        )]
