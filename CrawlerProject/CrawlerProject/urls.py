# CrawlerProject/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('CrawlerApp.urls')),  # 메인 라우터에 앱 연결
]