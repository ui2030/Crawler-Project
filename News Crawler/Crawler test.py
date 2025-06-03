import mysql.connector
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
from konlpy.tag import Okt
import re
from nltk.corpus import stopwords
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

# KoNLPy의 형태소 분석기 초기화
okt = Okt()

# 추가로 제거할 불용어 추가
custom_stopwords = ["뉴스", "기사", "제목", "…", "“", "”", ":", "-", "...", "외", "총", "일보", "특집", "되다", "보다", "높이다", "나서다", "하다", "막다", "열다", "이기다", "노리다", "달다",
                    "이끌다", "지나치다", "강화하다", "억", "조", "뚝", "감", "은", "는", "이", "가"]  # 필요한 만큼 추가

# 쌍따옴표를 제외한 나머지 문자를 제거하는 정규식 패턴
pattern = r'[^가-힣a-zA-Z]'  # 한글과 영문을 제외한 모든 문자

# 카테고리별 네이버 뉴스 URL
categories = {
    "정치": "100",
    "경제": "101",
    "사회": "102",
    "생활/문화": "103",
    "세계": "104",
    "IT/과학": "105"
}

# Chrome WebDriver 설정
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

# MySQL에 연결
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="123qwe",  # 설정한 비밀번호로 변경하세요
    database="news_db"
)

cursor = db.cursor()

# NLTK에서 영어 불용어 다운로드
stop_words = set(stopwords.words('english'))

print("Starting to scrape news data...")

# 각 카테고리별로 크롤링 및 데이터 저장
for category, code in categories.items():
    print(f"Scraping category: {category}")
    
    # 네이버 뉴스 페이지 열기
    url = f"https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1={code}"
    driver.get(url)
    
    # 뉴스 더보기 버튼 클릭하여 추가 기사 로드
    more_button = driver.find_element("css selector", "a.section_more_inner._CONTENT_LIST_LOAD_MORE_BUTTON")
    more_button.click()
    time.sleep(2)  # 클릭 후 잠시 대기

    # 추가 기사 로드 후 뉴스 더보기 버튼을 8번 더 누르기
    for _ in range(8):
        more_button.click()
        time.sleep(2)  # 클릭 후 잠시 대기

    # 페이지 소스 가져오기
    page_source = driver.page_source

    # BeautifulSoup으로 페이지 파싱
    soup = BeautifulSoup(page_source, "html.parser")

    # 일반 뉴스 제목, 링크 추출
    normal_news_items = soup.find_all("li", class_="sa_item _LAZY_LOADING_WRAP")

    for item in normal_news_items:
        title = item.find("strong", class_="sa_text_strong").get_text(strip=True)
        link = item.find("a")["href"]
        
        # 데이터베이스에 저장
        cursor.execute("INSERT INTO news_data (title, link, category) VALUES (%s, %s, %s)", (title, link, category))

db.commit()

print("Finished scraping news data.")

# 단어 추출 및 TF-IDF 계산 함수
def tokenize_and_filter(text):
    tokens = okt.pos(text, stem=True)
    filtered_title = [word for word, pos in tokens if pos in ['Noun']]
    filtered_title = [word for word in filtered_title if word not in stop_words]
    filtered_title = [word for word in filtered_title if word not in custom_stopwords]
    filtered_title = [re.sub(r"[^\w\s]", '', word) for word in filtered_title]
    filtered_title = [re.sub(pattern, '', word) for word in filtered_title]
    filtered_title = list(filter(None, filtered_title))
    return ' '.join(filtered_title)

# 카테고리별 상위 20개 단어 추출 및 관련 기사 링크 저장
for category in categories.keys():
    print(f"Processing category: {category}")
    
    # 저장된 데이터로부터 해당 카테고리의 제목 추출
    cursor.execute("SELECT title FROM news_data WHERE category = %s", (category,))
    titles_from_db = cursor.fetchall()
    
    # 단어 추출 및 TF-IDF 계산
    all_titles = [title[0] for title in titles_from_db]
    
    # KoNLPy를 사용하여 형태소 분석 및 불용어 제거
    filtered_titles = [tokenize_and_filter(title) for title in all_titles]
    
    print(f"Completed filtering titles for category: {category}")

    # TF-IDF 벡터화
    vectorizer = TfidfVectorizer(max_features=20)
    X = vectorizer.fit_transform(filtered_titles)
    
    # TF-IDF 벡터화된 단어 추출
    feature_names = vectorizer.get_feature_names_out()
    
    # 각 단어의 TF-IDF 가중치 추출
    tfidf = X.toarray()
    
    # 각 단어의 TF-IDF 가중치 합산
    tfidf_sum = np.sum(tfidf, axis=0)
    
    # 단어와 가중치를 딕셔너리로 묶음
    word_freq_data = dict(zip(feature_names, tfidf_sum))
    
    # 가중치를 기준으로 내림차순으로 정렬
    word_freq_data = dict(sorted(word_freq_data.items(), key=lambda item: item[1], reverse=True))
    
    # 상위 20개 단어 추출
    top_words = list(word_freq_data.keys())[:20]
    
    print(f"Top 20 words for category {category}: {top_words}")

    # 상위 20개 단어와 관련된 모든 뉴스 링크 및 카테고리 저장
    for word in top_words:
        cursor.execute("SELECT link FROM news_data WHERE category = %s AND title LIKE %s", (category, f"%{word}%"))
        link_results = cursor.fetchall()
        for link in link_results:
            cursor.execute("INSERT INTO keywords_links (keyword, link, category) VALUES (%s, %s, %s)", (word, link[0], category))
    
    db.commit()

print("Top 20 words and related links saved to database.")

# MySQL 연결 종료
db.close()

# WebDriver 종료
driver.quit()

print("Web scraping completed successfully.")