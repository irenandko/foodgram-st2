from django.db import models
from django.core.validators import (MinValueValidator,
                                    MaxValueValidator)
from users.models import CustomUser
from api.constants import (MIN_COOK_TIME,
                           MAX_COOK_TIME,
                           MAX_NAME_LEN,
                           MEANSUREMENT_UNIT,
                           MIN_AMOUNT,
                           MAX_AMOUNT)


class Ingredient(models.Model):
    """Модель, содержащая информацию о конкретном ингридиенте."""

    name: models.CharField = models.CharField(
        max_length=MAX_NAME_LEN,
        verbose_name='Название ингредиента')
    measurement_unit: models.CharField = models.CharField(
        max_length=MEANSUREMENT_UNIT,
        verbose_name='Единица измерения')

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель, содержащая информацию о конкретном рецепте."""

    image = models.ImageField(
        upload_to='recipes_images/',
        verbose_name='Фото блюда')
    author: models.ForeignKey = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
        related_name='recipes',
    )
    name: models.CharField = models.CharField(
        max_length=256,
        verbose_name='Название рецепта')
    cooking_time: models.PositiveSmallIntegerField = (
        models.PositiveSmallIntegerField(
            verbose_name='Время приготовления',
            validators=[
                MinValueValidator(MIN_COOK_TIME),
                MaxValueValidator(MAX_COOK_TIME)
            ],
        )
    )
    ingredients: models.ManyToManyField = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        related_name='recipes',
        verbose_name='Ингридиенты'
    )
    text: models.TextField = models.TextField(verbose_name='Описание рецепта')
    pub_date: models.DateTimeField = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата публикации')

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['-pub_date',]

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    """Модель связи ингридиентов и рецептов."""

    recipe: models.ForeignKey = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredients_in_recipe',
        verbose_name='Рецепт')
    ingredient: models.ForeignKey = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredients_in_recipe',
        verbose_name='Ингредиент')
    amount: models.PositiveSmallIntegerField = (
        models.PositiveSmallIntegerField(
            validators=[MinValueValidator(MIN_AMOUNT),
                        MaxValueValidator(MAX_AMOUNT)],
            verbose_name='Количество',
        )
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'
        ordering = ('ingredient__name',)

    def __str__(self):
        return (
            f"{self.recipe.name}: "
            f"{self.ingredient.name} - "
            f"{self.amount} "
            f"{self.ingredient.measurement_unit}"
        )


class ShoppingCart(models.Model):
    """Модель списка покупок (корзины) для пользователя."""

    user: models.ForeignKey = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='shopping_carts'
    )
    recipe: models.ForeignKey = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='in_shopping_carts'
    )

    class Meta:
        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзины покупок'
        ordering = ('user__username',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]

    def __str__(self):
        return f"Корзина {self.user.username}: {self.recipe.name}"


class Favorites(models.Model):
    """Модель избранных рецептов пользователя."""

    user: models.ForeignKey = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='favorites'
    )
    recipe: models.ForeignKey = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
        related_name='in_favorites'
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранные рецепты'
        ordering = ('user__username',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]

    def __str__(self):
        return f"Избранное {self.user.username}: {self.recipe.name}"
