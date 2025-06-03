from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from api.constants import MAX_EMAIL_LEN, MAX_USERNAME_LEN


class CustomUser(AbstractUser):
    """Класс пользователя."""

    first_name = models.CharField(
        max_length=MAX_USERNAME_LEN,
        verbose_name='Имя')
    last_name = models.CharField(
        max_length=MAX_USERNAME_LEN,
        verbose_name='Фамилия',
    )
    email = models.EmailField(
        max_length=MAX_EMAIL_LEN,
        unique=True,
        verbose_name='Электронная почта'
    )
    username = models.CharField(
        max_length=MAX_USERNAME_LEN,
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
        default_related_name = 'users'
        ordering = ('username',)

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
        verbose_name_plural = 'Подписки'
        ordering = ('author',)
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author',],
                name='unique_subscription'
            )
        ]

    def __str__(self):
        return f'{self.user} подписан(-а) на {self.author}'
