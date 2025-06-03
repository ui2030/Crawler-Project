from django.contrib import admin
from .models import NewsArticle

@admin.register(NewsArticle)
class NewsArticleAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "top_words")
    search_fields = ("title", "extracted_words", "top_words")