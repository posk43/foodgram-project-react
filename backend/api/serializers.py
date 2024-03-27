from django.contrib.auth import get_user_model
from django.core.validators import MaxValueValidator, MinValueValidator
from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from recipes.constant import MIN_VALUE, MAX_VALUE
from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag, TagInRecipe)
from users.models import Subscribe


User = get_user_model()


class CustomUserCreateSerializer(UserCreateSerializer):
    """Сериализатор для регистрации пользователя."""

    class Meta:
        model = User
        fields = ('email', 'username', 'first_name',
                  'last_name', 'password')


class ProfileSerializer(UserSerializer):
    """Сериализатор для отображения пользователя."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'id'
        )

    def get_is_subscribed(self, obj):
        user = self.context.get('request').user
        if user and not user.is_anonymous:
            return Subscribe.objects.filter(
                user=user,
                author=obj
            ).exists()
        return False


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ингредиентов."""

    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class IngredientAmountSerializer(serializers.ModelSerializer):
    """Сериализатор для связанной модели ингредиентов и рецептов."""

    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'name', 'measurement_unit', 'amount')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для модели тегов"""

    class Meta:
        model = Tag
        fields = ('id', 'name', 'color', 'slug')


class RecipeListSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения рецепта."""

    author = ProfileSerializer(read_only=True)
    ingredients = IngredientAmountSerializer(
        many=True, source='recipe_ingredients'
    )
    tags = TagSerializer(many=True, read_only=True)
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients', 'is_favorited',
            'is_in_shopping_cart', 'name', 'image', 'text', 'cooking_time',
        )

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        return (
            user.is_authenticated
            and ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        )


class AddIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для добавления ингредиентов."""

    id = serializers.PrimaryKeyRelatedField(queryset=Ingredient.objects.all())
    amount = serializers.IntegerField(
        validators=(
            MinValueValidator(
                limit_value=MIN_VALUE,
                message=f'Количество ингредиента меньше {MIN_VALUE}!'
            ),
            MaxValueValidator(
                limit_value=MAX_VALUE,
                message=f'Количество ингредиента больше {MAX_VALUE}!'
            )
        )
    )

    class Meta:
        model = IngredientInRecipe
        fields = ('id', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для создания рецепта."""

    author = ProfileSerializer(read_only=True)
    image = Base64ImageField()
    ingredients = AddIngredientSerializer(many=True)
    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True
    )
    cooking_time = serializers.IntegerField(
        validators=(
            MinValueValidator(
                limit_value=MIN_VALUE,
                message=f'Время приготовления меньше {MIN_VALUE} минуты!'
            ),
            MaxValueValidator(
                limit_value=MAX_VALUE,
                message=f'Время приготовления больше {MAX_VALUE} минут!'
            )
        )
    )

    class Meta:
        model = Recipe
        fields = (
            'id', 'author', 'tags', 'ingredients',
            'image', 'text', 'name', 'cooking_time',
        )

    def validate_ingredients(self, ingredients):
        if len(ingredients) < 1:
            raise serializers.ValidationError(
                {'ingredients': 'Нужно выбрать хотя бы один ингредиент!'}
            )
        unique_ingredient_id = set()
        for ingredient in ingredients:
            ingredient_id = ingredient['id']
            if ingredient_id in unique_ingredient_id:
                raise serializers.ValidationError(
                    {'ingredients': 'Ингредиенты должны быть уникальными!'}
                )
            unique_ingredient_id.add(ingredient_id)
        return ingredients

    def validate_tags(self, tags):
        if len(tags) < 1:
            raise serializers.ValidationError(
                {'tags': 'Нужно выбрать хотя бы один тег!'}
            )

        if len(tags) != len(set(tags)):
            raise serializers.ValidationError(
                {'tags': 'Теги не уникальны!'}
            )

        return tags

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                {'image': 'Вставьте изображение!'}
            )
        return value

    @staticmethod
    def create_ingredients(ingredients, recipe):
        ingredients_list = [
            IngredientInRecipe(
                recipe=recipe,
                ingredient=ingredient['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        ]
        IngredientInRecipe.objects.bulk_create(ingredients_list)

    @staticmethod
    def create_tags(tags, recipe):
        tags_list = [
            TagInRecipe(
                recipe=recipe,
                tag=tag,
            ) for tag in tags
        ]
        TagInRecipe.objects.bulk_create(tags_list)

    def create(self, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(**validated_data)
        self.create_ingredients(ingredients, recipe)
        self.create_tags(tags, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance.ingredients.clear()
        self.create_ingredients(ingredients, instance)
        instance.tags.clear()
        self.create_tags(tags, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeListSerializer(
            instance, context={'request': self.context.get('request')}
        ).data


class SubscribeRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для отображения краткой информации рецептов."""

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')


class SubscribeListSerializer(ProfileSerializer):
    """Сериализатор для отображения подписок пользователя."""

    recipes_count = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()

    class Meta(ProfileSerializer.Meta):
        fields = ProfileSerializer.Meta.fields + (
            'recipes_count', 'recipes'
        )
        read_only_fields = ('email', 'username',
                            'first_name', 'last_name')

    def validate(self, data):
        author = self.instance
        user = self.context.get('request').user
        if Subscribe.objects.filter(author=author, user=user).exists():
            raise ValidationError(
                'Подписка уже оформлена!',
            )
        if user == author:
            raise ValidationError(
                'Нельзя подписаться на самого себя!',
            )
        return data

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.GET.get('recipes_limit')
        recipes = obj.recipes.all()
        if limit:
            recipes = recipes[: int(limit)]
        serializer = SubscribeRecipeSerializer(
            recipes, many=True, read_only=True
        )
        return serializer.data

    def get_recipes_count(self, obj):
        return obj.recipes.count()
