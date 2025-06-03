from django.urls import path
from . import views
urlpatterns = [
    path('', views.index, name='index'),
    path('api/articles', views.api_articles, name='api_articles'),
    path('api/topwords', views.api_topwords, name='api_topwords'),
]