from django.urls import path
from recipes.views import copy_short_link

app_name = 'recipes'

urlpatterns = [
    path('s/<int:pk>/', copy_short_link, name='recipe_short_link')
]