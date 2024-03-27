from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, RegexValidator
from django.db import models

from .constant import LENTH_COLOR, MAX_LENGTH

User = get_user_model()


class Ingredient(models.Model):
    """Модель ингредиентов."""

    name = models.CharField(
        max_length=MAX_LENGTH,
        verbose_name='Название'
    )
    measurement_unit = models.CharField(
        max_length=MAX_LENGTH,
        verbose_name='Единица измерения'
    )

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ('name',)
        unique_together = ('name', 'measurement_unit')

    def __str__(self):
        return f'{self.name} {self.measurement_unit}'


class Tag(models.Model):
    """Модель тегов."""

    name = models.CharField(
        max_length=MAX_LENGTH,
        verbose_name='Название'
    )
    slug = models.SlugField(unique=True)
    color = models.CharField(
        unique=True,
        max_length=LENTH_COLOR,
        verbose_name='Цветовой код',
        validators=(RegexValidator(regex='^#([A-Fa-f0-9]{6})$'),)
    )

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Теги'

    def clean(self):
        if Tag.objects.filter(
            color__iexact=self.color
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                'Тег с таким цветом уже существует.'
            )

    def __str__(self):
        return self.name


class Recipe(models.Model):
    """Модель рецептов."""

    name = models.CharField(
        max_length=MAX_LENGTH,
        verbose_name='Название рецепта'
    )
    image = models.ImageField(
        verbose_name='Картинка',
        upload_to='recipes/images'
    )
    text = models.TextField(
        'Описание рецепта'
    )
    cooking_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления (в минутах)',
        validators=[MinValueValidator(1)]
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='recipes'
    )
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientInRecipe',
        related_name='recipes'
    )
    tags = models.ManyToManyField(
        Tag,
        through='TagInRecipe',
        verbose_name='Теги',
        related_name='recipes'
    )

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'

    def __str__(self):
        return self.name


class IngredientInRecipe(models.Model):
    """Модель для связи ингредиента и рецепта."""

    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='recipe_ingredients')
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(1)],
        null=True
    )

    class Meta:
        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'
        constraints = (
            models.UniqueConstraint(
                fields=('ingredient', 'recipe'),
                name='unique_ingredient_in_recipe'
            ),
        )

    def __str__(self):
        return f'{self.ingredient} - {self.amount}'


class TagInRecipe(models.Model):
    """Модель для связи тега и рецепта."""

    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Тег рецепта'
        verbose_name_plural = 'Теги рецепта'
        constraints = (
            models.UniqueConstraint(
                fields=('tag', 'recipe'),
                name='unique_tag_in_recipe'
            ),
        )

    def __str__(self):
        return self.tag.name


class Favorite(models.Model):
    """Модель для отображения избранного."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'user'),
                name='unique_favourite'
            ),
        )

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в избранное'


class ShoppingCart(models.Model):
    """Модель для отображения списка покупок."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Рецепт'
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'user'),
                name='unique_shopping_cart'
            ),
        )

    def __str__(self):
        return f'{self.user} добавил {self.recipe} в список покупок'
