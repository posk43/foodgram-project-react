from django.contrib import admin
from django.contrib.admin import display

from .form import AtLeastOneRequiredInlineFormSet
from .models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                     ShoppingCart, Tag, TagInRecipe)


class IngredientsInLine(admin.TabularInline):
    model = Recipe.ingredients.through
    formset = AtLeastOneRequiredInlineFormSet


class TagsInLine(admin.TabularInline):
    model = Recipe.tags.through
    formset = AtLeastOneRequiredInlineFormSet


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit',)
    list_filter = ('name',)
    search_fields = ('name',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('name', 'color', 'slug',)
    list_filter = ('name', 'slug')
    search_fields = ('name', 'slug')


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'cooking_time',
                    'count_favorites')
    list_display_links = ('name',)
    list_filter = ('author', 'name', 'tags',)
    inlines = (IngredientsInLine, TagsInLine)

    @display(description='Количество в избранных')
    def count_favorites(self, obj):
        return obj.favorites.count()


@admin.register(IngredientInRecipe)
class IngredientInRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'ingredient', 'amount',)


@admin.register(TagInRecipe)
class TagInRecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'recipe', 'tag')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe',)


@admin.register(ShoppingCart)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'recipe',)
