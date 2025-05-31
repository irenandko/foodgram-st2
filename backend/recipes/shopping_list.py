from django.db.models import Sum
from django.http import HttpResponse
from recipes.models import IngredientInRecipe


def get_ingredients_for_list(user):
    """Извлекает ингредиенты, необходимые для покупок пользователю."""
    purchase_items = (
        IngredientInRecipe.objects
        .filter(recipe__in_shopping_carts__user__pk=user.pk)
        .values('ingredient__name', 'ingredient__measurement_unit')
        .annotate(total_quantity=Sum('amount'))
    )
    return purchase_items


def create_shopping_list_text(items):
    """Составляет текст списка покупок на основе предоставленных данных."""
    lines = []
    for item in items:
        name = item['ingredient__name']
        quantity = item['total_quantity']
        unit = item['ingredient__measurement_unit']
        lines.append(f"{name} - {quantity} {unit}\n")
    return "".join(lines)


def deliver_shopping_list(user):
    """Создает и отдает HTTP-ответ с файлом списка покупок."""
    needed_items = get_ingredients_for_list(user)
    shopping_text = create_shopping_list_text(needed_items)

    response = HttpResponse(shopping_text,
                            content_type="text/plain; charset=UTF-8")
    response['Content-Disposition'] = (
        'attachment; filename="shopping_list.txt"')
    return response
