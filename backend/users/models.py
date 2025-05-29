from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator


class CustomUser(AbstractUser):
    """Класс пользователя."""

    first_name = models.CharField(
        max_length=128,
        verbose_name='Имя')
    last_name = models.CharField(
        max_length=128,
        verbose_name='Фамилия',
    )
    email = models.EmailField(
        max_length=128,
        unique=True,
        verbose_name='Электронная почта'
    )
    username = models.CharField(
        max_length=50,
        unique=True,
        validators=[
            RegexValidator(
                regex=(r'^[\w.@-]+$'),
                message='Для имени пользователя необходимо использовать'
                'только буквы, цифры и символы "@ . -"')],
        verbose_name='Имя пользователя',
    )
    avatar = models.ImageField(
        upload_to='users_avatars/',
        null=True,
        blank=True,
        verbose_name='Фото профиля'
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',),
        default_related_name = 'users'

    def __str__(self):
        return self.username


class Subscription(models.Model):
    """Класс отображения подписки."""

    user: models.ForeignKey = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Подписчик',
        related_name='subscribers',
    )
    author: models.ForeignKey = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='authors'
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки',
        ordering = ('user',),
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author',],
                name='unique_subscription'
            )
        ]
