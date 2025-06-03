# CrawlerApp/management/commands/crawl_news.py
import re, time, feedparser
from collections import Counter
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import IntegrityError
from CrawlerApp.models import NewsArticle

STOPWORDS = {"기사","사진","영상","단독","속보","전체","보기","또","그리고","하지만"}

def pick_top_word(title: str) -> str:
    words = re.findall(r"[가-힣A-Za-z0-9]{2,}", title)
    words = [w for w in words if w not in STOPWORDS]
    return Counter(words).most_common(1)[0][0] if words else ""

class Command(BaseCommand):
    help = "Fetch news via RSS and insert into CrawlerApp_newsarticle (SQLite)."

    def add_arguments(self, p):
        p.add_argument("--limit", type=int, default=50)
        p.add_argument("--feeds", type=str, default="")
        p.add_argument("--sleep", type=float, default=0.5)

    def handle(self, *args, **o):
        feeds = []
        if o["feeds"]:
            with open(o["feeds"], "r", encoding="utf-8") as f:
                feeds = [ln.strip() for ln in f if ln.strip() and not ln.startswith("#")]
        if not feeds:
            feeds = ["https://news.google.com/rss?hl=ko&gl=KR&ceid=KR:ko"]

        inserted = 0
        for url in feeds:
            d = feedparser.parse(url)
            for e in d.entries:
                title = getattr(e, "title", "").strip()
                link  = getattr(e, "link", "").strip()
                if not title or not link:
                    continue
                # 중복 방지
                if NewsArticle.objects.filter(link=link).exists():
                    continue

                try:
                    NewsArticle.objects.create(
                        title=title,
                        link=link,
                        extracted_words=title,   # 필요하면 실제 토큰으로 변경
                        top_words=pick_top_word(title),
                        created_at=timezone.now(),  # DateTimeField(null=True)와 매핑
                    )
                    inserted += 1
                except IntegrityError:
                    # UNIQUE 인덱스 있는 경우 안전하게 스킵
                    continue

                if inserted >= o["limit"]:
                    break
            if inserted >= o["limit"]:
                break
            time.sleep(o["sleep"])

        self.stdout.write(self.style.SUCCESS(f"Inserted {inserted} new items"))