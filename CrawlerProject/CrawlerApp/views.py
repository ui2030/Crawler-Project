# CrawlerApp/views.py
from datetime import timedelta
from collections import Counter
from urllib.parse import quote_plus
import re
import feedparser

from django.db.models import Q, Count
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from .models import NewsArticle

# 초기 화면용 "최근 N일" 기준
RECENT_DAYS = 3

# -------------------- helpers --------------------
STOPWORDS = {
    "기사","사진","영상","단독","속보","전체","보기","그리고","그러나","하지만",
}

def _expand_terms(q: str):
    ql = (q or "").strip().lower()
    if not ql:
        return []
    SYN = {
        "it": ["it","아이티","tech","테크","기술","디지털","sw","소프트웨어",
               "하드웨어","모바일","전자","반도체","클라우드","ai","인공지능"],
        "ai": ["ai","인공지능","딥러닝","머신러닝","챗봇","생성형"],
        "반도체": ["반도체","칩","칩셋","파운드리","메모리","dram","낸드"],
        "모바일": ["모바일","스마트폰","휴대폰","갤럭시","아이폰"],
        "게임": ["게임","엔씨","넥슨","크래프톤","콘솔"],
    }
    terms = {ql}
    for k, vals in SYN.items():
        if ql == k or ql in vals:
            terms.update(vals)
    return list(terms)

def _tokenize(title: str):
    # 한글/영문/숫자 2글자 이상 토큰화 + 소문자 + 불용어 제거
    toks = [w.lower() for w in re.findall(r"[가-힣A-Za-z0-9]{2,}", title)]
    return [w for w in toks if w not in STOPWORDS]

def _pick_top_word(title: str):
    c = Counter(_tokenize(title))
    return c.most_common(1)[0][0] if c else ""

def _fetch_live_from_google_news(q: str, limit: int = 50):
    """
    검색 키워드로 Google News RSS를 즉시 조회해서
    [{'title':..., 'link':..., 'tokens':[...]}] 리스트를 반환
    """
    url = f"https://news.google.com/rss/search?q={quote_plus(q)}&hl=ko&gl=KR&ceid=KR:ko"
    d = feedparser.parse(url)
    items = []
    for e in (d.entries or [])[:limit]:
        title = getattr(e, "title", "").strip()
        link = getattr(e, "link", "").strip()
        if not title or not link:
            continue
        items.append({"title": title, "link": link, "tokens": _tokenize(title)})
    return items
# -------------------------------------------------


def index(request):
    """초기 화면: 최근 N일 기사 20개 + 상위 단어 20개(로컬 DB 기준)"""
    since = timezone.now() - timedelta(days=RECENT_DAYS)

    articles = (
        NewsArticle.objects
        .filter(Q(created_at__gte=since) | Q(created_at__isnull=True))
        .order_by("-created_at", "-id")[:20]
    )

    top20 = (
        NewsArticle.objects
        .filter(Q(created_at__gte=since) | Q(created_at__isnull=True))
        .values("top_words")
        .annotate(cnt=Count("id"))
        .order_by("-cnt")[:20]
    )

    return render(request, "index.html", {"articles": articles, "top20": top20})


def api_articles(request):
    """
    기사 리스트 API
    - q 없음: 최근 N일 로컬 DB에서 최신 20
    - q 있음: (1) 로컬 DB 전체에서 매칭 + (2) Google News RSS 실시간 조회
              → 링크로 중복 제거 후 최신순 상위 N개 반환
              → 동시에 DB에 없는 실시간 결과는 INSERT(옵션)해 DB도 최신화
    """
    q = (request.GET.get("q") or "").strip()
    try:
        limit = int(request.GET.get("limit", 20))
    except ValueError:
        limit = 20

    # 1) 기본 쿼리셋
    qs = NewsArticle.objects.all()

    results = []
    seen_links = set()

    if not q:
        # 초기: 최근 N일만
        since = timezone.now() - timedelta(days=RECENT_DAYS)
        qs = qs.filter(Q(created_at__gte=since) | Q(created_at__isnull=True))
        for row in qs.order_by("-created_at", "-id")[:limit].values("title", "link"):
            results.append({"title": row["title"], "link": row["link"]})
        return JsonResponse(results, safe=False)

    # q가 있을 때 → DB에서 먼저 긁고
    terms = _expand_terms(q)
    cond = Q()
    for t in terms:
        cond |= (Q(title__icontains=t) |
                 Q(extracted_words__icontains=t) |
                 Q(top_words__icontains=t))
    for row in qs.filter(cond).order_by("-created_at", "-id")[:limit*2].values("title", "link"):
        if row["link"] not in seen_links:
            seen_links.add(row["link"])
            results.append({"title": row["title"], "link": row["link"]})

    # 부족하면 실시간으로 보강
    if len(results) < limit:
        live = _fetch_live_from_google_news(q, limit=limit*2)
        now = timezone.now()
        for item in live:
            if item["link"] in seen_links:
                continue
            seen_links.add(item["link"])
            results.append({"title": item["title"], "link": item["link"]})

            # (옵션) DB에 즉시 반영해서 다음 검색/초기화 때도 최신 유지
            try:
                NewsArticle.objects.create(
                    title=item["title"],
                    link=item["link"],
                    extracted_words=" ".join(item["tokens"]),
                    top_words=_pick_top_word(item["title"]),
                    created_at=now,
                )
            except Exception:
                # UNIQUE 제약 등 중복일 수 있으니 조용히 스킵
                pass

    # 최신 먼저 보여주기: 방금 넣은 실시간 결과에 현재시간을 부여했으므로
    return JsonResponse(results[:limit], safe=False)


def api_topwords(request):
    """
    상위 단어 TOP20 API
    - q 없음: 최근 N일 로컬 DB 집계
    - q 있음: DB 매칭 + 실시간 결과(구글 뉴스)까지 합쳐 제목 토큰으로 집계
    - days=0 쿼리로 들어오면 날짜 제한 없이 DB를 조회
    """
    q = (request.GET.get("q") or "").strip()
    try:
        days = int(request.GET.get("days", RECENT_DAYS))
    except ValueError:
        days = RECENT_DAYS

    # q가 없으면 기존처럼 DB 집계
    if not q:
        qs = NewsArticle.objects.all()
        if days > 0:
            since = timezone.now() - timedelta(days=days)
            qs = qs.filter(Q(created_at__gte=since) | Q(created_at__isnull=True))
        agg = (
            qs.values("top_words")
              .annotate(cnt=Count("id"))
              .order_by("-cnt")[:20]
        )
        return JsonResponse([[row["top_words"], row["cnt"]] for row in agg], safe=False)

    # q가 있으면: DB 매칭 + 실시간 결과 합쳐서 토큰 기준으로 집계
    terms = _expand_terms(q)
    cond = Q()
    for t in terms:
        cond |= (Q(title__icontains=t) |
                 Q(extracted_words__icontains=t) |
                 Q(top_words__icontains=t))

    tokens = []
    qs = NewsArticle.objects.all()
    if days > 0:
        since = timezone.now() - timedelta(days=days)
        qs = qs.filter(Q(created_at__gte=since) | Q(created_at__isnull=True))
    for row in qs.filter(cond).values_list("title", flat=True)[:1000]:
        tokens.extend(_tokenize(row))

    # 실시간도 합치기
    live = _fetch_live_from_google_news(q, limit=100)
    for item in live:
        tokens.extend(item["tokens"])

    counter = Counter(tokens)
    top = counter.most_common(20)
    return JsonResponse([[w, int(n)] for w, n in top], safe=False)