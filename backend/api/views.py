from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from recipes.models import (Favorite, Ingredient, IngredientInRecipe, Recipe,
                            ShoppingCart, Tag, User)
from users.models import Subscribe

from .filters import IngredientSearchFilter, RecipeFilter
from .pagination import CustomPagination
from .permissions import IsAuthorOrAdmin
from .serializers import (IngredientSerializer, ProfileSerializer,
                          RecipeListSerializer, RecipeSerializer,
                          SubscribeListSerializer, SubscribeRecipeSerializer,
                          TagSerializer)


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    permission_classes = (AllowAny, )
    serializer_class = IngredientSerializer
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientSearchFilter


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    permission_classes = (AllowAny, )
    serializer_class = TagSerializer


class RecipeViewSet(ModelViewSet):
    permission_classes = (IsAuthenticatedOrReadOnly,
                          IsAuthorOrAdmin,)
    filter_backends = (DjangoFilterBackend, )
    filterset_class = RecipeFilter
    pagination_class = CustomPagination

    def get_queryset(self):
        queryset = Recipe.objects.all().select_related(
            'author').prefetch_related(
            'ingredients', 'tags'
        ).order_by('-id')
        return queryset

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeListSerializer
        return RecipeSerializer

    def add_to(self, model, user, pk):
        if model.objects.filter(user=user, recipe__id=pk).exists():
            return Response(
                {'errors': 'Этот рецепт уже добавлен!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        recipe = get_object_or_404(Recipe, id=pk)
        model.objects.create(user=user, recipe=recipe)
        serializer = SubscribeRecipeSerializer(recipe)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete_from(self, model, user, pk):
        obj = model.objects.filter(user=user, recipe__id=pk)
        if obj.exists():
            obj.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'errors': 'Этот рецепт уже удален!'},
            status=status.HTTP_400_BAD_REQUEST
        )

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        permission_classes=(IsAuthenticated, )
    )
    def favorite(self, request, pk):
        try:
            pk = int(pk)
        except ValueError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if self.request.method == 'POST':
            return self.add_to(Favorite, request.user, pk)
        return self.delete_from(Favorite, request.user, pk)

    @action(
        methods=['POST', 'DELETE'],
        detail=True,
        permission_classes=(IsAuthenticated, )
    )
    def shopping_cart(self, request, pk):
        try:
            pk = int(pk)
        except ValueError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if self.request.method == 'POST':
            return self.add_to(ShoppingCart, request.user, pk)
        return self.delete_from(ShoppingCart, request.user, pk)

    @action(
        methods=['GET'],
        detail=False,
        permission_classes=(IsAuthenticated, )
    )
    def download_shopping_cart(self, request):
        ingredient_list = 'Cписок покупок:'

        ingredients = IngredientInRecipe.objects.filter(
            recipe__shopping_cart__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(amount=Sum('amount'))

        for ingredient in ingredients:
            ingredient_name = ingredient['ingredient__name']
            measurement_unit = ingredient['ingredient__measurement_unit']
            amount = ingredient['amount']
            ingredient_list += (
                f'\n{ingredient_name} - {amount} {measurement_unit}'
            )

        file = 'shopping_list'
        response = HttpResponse(ingredient_list, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="{file}.txt"'

        return response


class CustomUserViewSet(UserViewSet):
    queryset = User.objects.all()
    serializer_class = ProfileSerializer
    pagination_class = CustomPagination

    @action(
        detail=False,
        permission_classes=(IsAuthenticated, ),
        methods=['GET']
    )
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(
        detail=True,
        methods=['POST', 'DELETE'],
        permission_classes=(IsAuthenticated, )
    )
    def subscribe(self, request, **kwargs):
        user = request.user
        author_id = self.kwargs.get('id')
        try:
            author_id = int(author_id)
        except ValueError:
            return Response(status=status.HTTP_404_NOT_FOUND)

        author = get_object_or_404(User, id=author_id)

        if request.method == 'POST':
            serializer = SubscribeListSerializer(
                author, data=request.data, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            Subscribe.objects.create(user=user, author=author)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        subscription = Subscribe.objects.filter(
            user=user, author=author
        ).first()
        if not subscription:
            return Response(
                {'error': 'Вы не подписаны на этого пользователя!'},
                status=status.HTTP_400_BAD_REQUEST
            )
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        permission_classes=(IsAuthenticated, ),
        methods=['GET']
    )
    def subscriptions(self, request):
        user = request.user
        queryset = User.objects.filter(following__user=user)
        pages = self.paginate_queryset(queryset)
        serializer = SubscribeListSerializer(
            pages, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)
