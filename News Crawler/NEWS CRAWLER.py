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
from wordcloud import WordCloud
import matplotlib.pyplot as plt

# KoNLPy의 형태소 분석기 초기화
okt = Okt()

# 추가로 제거할 불용어 추가
custom_stopwords = ["뉴스", "기사", "제목", "…", "“", "”", ":", "-", "...", "외", "총", "일보", "특집", "되다", "보다", "높이다", "나서다", "하다", "막다", "열다", "이기다", "노리다", "달다",
                    "이끌다", "지나치다", "강화하다", "억", "조", "뚝", "감", "은", "는", "이", "가"]  # 필요한 만큼 추가

# 쌍따옴표를 제외한 나머지 문자를 제거하는 정규식 패턴
pattern = r'[^가-힣a-zA-Z]'  # 한글과 영문을 제외한 모든 문자

# Chrome WebDriver 설정
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

# 네이버 뉴스 페이지 열기
driver.get("https://news.naver.com/main/main.naver?mode=LSD&mid=shm&sid1=105")

# 뉴스 더보기 버튼 클릭하여 추가 기사 로드
more_button = driver.find_element("css selector", "a.section_more_inner._CONTENT_LIST_LOAD_MORE_BUTTON")
more_button.click()
time.sleep(2)  # 클릭 후 잠시 대기

# 추가 기사 로드 후 뉴스 더보기 버튼을 4번 더 누르기
for _ in range(4):
    more_button.click()
    time.sleep(2)  # 클릭 후 잠시 대기

# 페이지 소스 가져오기
page_source = driver.page_source

# BeautifulSoup으로 페이지 파싱
soup = BeautifulSoup(page_source, "html.parser")

# 일반 뉴스 제목과 링크 추출
normal_news_items = soup.find_all("li", class_="sa_item _LAZY_LOADING_WRAP")

# NLTK에서 영어 불용어 다운로드
stop_words = set(stopwords.words('english'))

# 데이터를 담을 리스트 초기화
data = []

# 제목과 링크 정보를 담을 리스트 초기화
titles = []
links = []

for item in normal_news_items:
    title = item.find("strong", class_="sa_text_strong").get_text(strip=True)
    link = item.find("a")["href"]
    
    # KoNLPy를 사용하여 형태소 분석 수행
    tokens = okt.pos(title, stem=True)
  
    # 명사만 추출
    filtered_title = [word for word, pos in tokens if pos in ['Noun']]
    
    # 불용어 제거
    filtered_title = [word for word in filtered_title if word not in stop_words]
    
    # 추가로 제거할 불용어 제거
    filtered_title = [word for word in filtered_title if word not in custom_stopwords]
    
    # 특수문자 제거
    filtered_title = [re.sub(r"[^\w\s]", '', word) for word in filtered_title]
    
    # 쌍따옴표와 숫자를 제외시키고 남은 문자열만 추출
    filtered_title = [re.sub(pattern, '', word) for word in filtered_title]
    
    # 공백 제거
    filtered_title = list(filter(None, filtered_title))
    
    # 데이터 리스트에 추가
    data.append(' '.join(filtered_title))
    
    # 제목과 링크 정보를 각각 리스트에 추가
    titles.append(title)
    links.append(link)

# TF-IDF 벡터화
vectorizer = TfidfVectorizer(max_features=20)
X = vectorizer.fit_transform(data)

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

# 상위 20개 단어를 텍스트로 변환
wordcloud_text = ' '.join(list(word_freq_data.keys())[:20])

# 워드클라우드 생성
wordcloud = WordCloud(font_path='NanumGothic', background_color='white', width=800, height=400).generate(wordcloud_text)

# 워드클라우드를 이미지로 저장
wordcloud.to_file('wordcloud_image.png')

# WebDriver 종료
driver.quit()