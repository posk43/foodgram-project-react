from django.contrib import admin

from .models import CustomUser, Subscribe


@admin.register(CustomUser)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'username', 'first_name',
                    'last_name', 'password')
    list_filter = ('email', 'username')
    empty_value_display = '-пусто-'
    search_fields = ('email', 'username')


@admin.register(Subscribe)
class SubscribeAdmin(admin.ModelAdmin):
    list_display = ('user', 'author')
