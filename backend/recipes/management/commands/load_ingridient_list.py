import json
from recipes.models import Ingredient
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Загрузка ингредиентов из ingredients.json'

    def handle(self, *args, **kwargs):
        with open('preloading_data/ingredients.json',
                  encoding='utf-8') as file:
            data = json.load(file)
            count = 0
            for item in data:
                obj, created = Ingredient.objects.get_or_create(
                    name=item['name'],
                    measurement_unit=item['measurement_unit']
                )
                if created:
                    count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f'{count} игридентов успешно загружено.'))
