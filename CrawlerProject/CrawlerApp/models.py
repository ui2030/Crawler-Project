from django.db import models

class NewsArticle(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    link = models.URLField()
    extracted_words = models.TextField()
    top_words = models.TextField()
    created_at = models.DateTimeField(null=True)  # ← 앞서 추가한 컬럼과 이름 동일

    class Meta:
        db_table = 'CrawlerApp_newsarticle'
        managed = False

    def __str__(self):
        return self.title[:60]