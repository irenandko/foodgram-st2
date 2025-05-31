from django.db import models
from django.core.validators import MinValueValidator
from users.models import CustomUser


class Ingredient(models.Model):
    """Модель, содержащая информацию о конкретном ингридиенте."""

    name: models.CharField = models.CharField(
        max_length=128,
        verbose_name='Название ингредиента')
    measurement_unit: models.CharField = models.CharField(
        max_length=32,
        verbose_name='Единица измерения')

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name',]

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
    cooking_time: models.IntegerField = (
        models.IntegerField(
            verbose_name='Время приготовления',
            validators=[
                MinValueValidator(1),
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
    amount: models.IntegerField = (
        models.IntegerField(
            validators=[MinValueValidator(1),],
            verbose_name='Количество',
        )
    )

    class Meta:
        verbose_name = 'Ингредиент в рецепте'
        verbose_name_plural = 'Ингредиенты в рецептах'


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
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]


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
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_favorite'
            )
        ]
