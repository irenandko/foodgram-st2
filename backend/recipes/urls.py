from django.urls import path
from api.views import copy_short_link

app_name = 'recipes'

urlpatterns = [
    path('recipes/<int:pk>/', copy_short_link, name='recipe_short_link')
]
