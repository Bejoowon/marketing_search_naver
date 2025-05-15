# 네이버 통합 크롤러

## 개요
네이버 통합 크롤러는 다양한 네이버 서비스에서 정보를 수집하고 분석하는 도구입니다. 모듈식 구조로 설계되어 여러 기능을 쉽게 추가하고 확장할 수 있습니다.

현재 지원하는 기능:
- **네이버 검색 크롤러**: 네이버 검색 결과에서 인기글/브랜드 콘텐츠 정보 수집
- **네이버 구매평 크롤러**: 네이버 쇼핑몰 상품의 구매평 정보 수집
- **구매평 감성 분석**: 수집된 구매평에 대한 긍정/부정 감성 분석
- **워드클라우드 생성**: 긍정/부정 키워드 기반 시각화

## 설치 방법

### 요구사항
- Python 3.8 이상
- 필요한 패키지: requirements.txt 참조

### 설치 과정
1. 리포지토리 복제
```
git clone https://github.com/your-username/naver-crawler.git
cd naver-crawler
```

2. 가상환경 생성 및 활성화 (선택사항)
```
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. 필요 패키지 설치
```
pip install -r requirements.txt
```

4. 브라우저 드라이버 설치 (자동으로 설치됨)
```
playwright install chromium
```

5. 한글 폰트 설치 (워드클라우드 생성 시 필요)
```
# Windows/macOS: 나눔고딕 폰트 설치 후 data 디렉토리로 복사
mkdir -p data
cp [나눔고딕 폰트 경로]/NanumGothic.ttf data/
```

## 사용 방법

### GUI 애플리케이션 실행
GUI 인터페이스를 사용하여 쉽게 크롤링 및 분석 작업을 수행할 수 있습니다.

```
python main_gui.py
```

#### GUI 기능
- **구매평 수집 탭**: 단일 URL 또는 URL 목록에서 구매평 수집
- **감성 분석 탭**: 수집된 구매평에 대한 긍정/부정 감성 분석
- **워드클라우드 탭**: 감성 분석 결과를 기반으로 한 워드클라우드 생성 및 저장

### 명령행 인터페이스 실행 (CLI)
터미널에서 명령줄 인터페이스를 통해 실행할 수도 있습니다.

```
python main.py --module [모듈이름] [옵션]
```

### 모듈 목록 확인
```
python main.py
```

### 네이버 검색 크롤러 사용
키워드 목록을 파일로 입력받아 인기글/브랜드 콘텐츠 정보를 수집합니다.

```
python main.py --module search --input keywords.xlsx --output results.xlsx [--headless]
```

- `--input`: 키워드 목록 파일 경로 (Excel 또는 CSV)
- `--output`: 결과 저장 파일 경로
- `--headless`: 브라우저를 화면에 표시하지 않고 실행 (선택사항)

### 네이버 구매평 크롤러 사용
네이버 쇼핑몰 상품 페이지에서 구매평 정보를 수집합니다.

#### 단일 상품 URL 처리
```
python main.py --module review --url [상품URL] --output reviews.xlsx [--headless]
```

#### 상품 URL 목록 처리
```
python main.py --module review --input product_urls.xlsx --output reviews.xlsx [--headless]
```

- `--url`: 단일 상품 URL (단일 상품 처리 시)
- `--input`: 상품 URL 목록 파일 경로 (URL 목록 처리 시)
- `--output`: 결과 저장 파일 경로
- `--headless`: 브라우저를 화면에 표시하지 않고 실행 (선택사항)

## 모듈 직접 실행
각 모듈은 독립적으로도 실행 가능합니다.

### 네이버 검색 크롤러
```
python modules/search_crawler/naver_search_crawler.py --input keywords.xlsx --output results.xlsx [--headless]
```

### 네이버 구매평 크롤러
```
python modules/review_crawler/naver_review_crawler.py --url [상품URL] --output reviews.xlsx [--headless]
```
또는
```
python modules/review_crawler/naver_review_crawler.py --input product_urls.xlsx --output reviews.xlsx [--headless]
```

### 감성 분석기 실행
```
python modules/review_crawler/review_analyzer.py
```

## 감성 분석 및 워드클라우드 기능
구매평 데이터에 대한 감성 분석 및 워드클라우드 시각화를 제공합니다:

- **감성 분석**: 구매평 텍스트에서 긍정적/부정적 표현을 분석
- **키워드 추출**: 형태소 분석을 통한 주요 키워드 추출
- **워드클라우드 생성**: 빈도수에 따라 크기가 조정된 워드클라우드 시각화

## 프로젝트 구조
```
naver_crawler/
├── main.py                     # 메인 CLI 프로그램
├── main_gui.py                 # 메인 GUI 프로그램
├── modules/                    # 크롤러 모듈 디렉토리
│   ├── __init__.py             # 패키지 초기화 파일
│   ├── search_crawler/         # 검색 크롤러 모듈
│   │   ├── __init__.py
│   │   └── naver_search_crawler.py
│   ├── review_crawler/         # 구매평 크롤러 모듈
│   │   ├── __init__.py
│   │   ├── naver_review_crawler.py
│   │   └── review_analyzer.py  # 감성 분석 모듈
│   └── gui/                    # GUI 모듈
│       ├── __init__.py
│       ├── app.py              # GUI 메인 애플리케이션
│       ├── review_tab.py       # 구매평 수집 탭
│       ├── analysis_tab.py     # 감성 분석 탭
│       └── wordcloud_tab.py    # 워드클라우드 탭
├── data/                       # 감성 사전 및 폰트 데이터
│   ├── positive_words_ko.txt   # 긍정 단어 사전
│   ├── negative_words_ko.txt   # 부정 단어 사전
│   └── NanumGothic.ttf         # 워드클라우드용 폰트
├── logs/                       # 로그 파일 디렉토리
├── results/                    # 결과 저장 디렉토리
│   ├── reviews/                # 구매평 결과 디렉토리
│   └── analysis/               # 분석 결과 디렉토리
├── requirements.txt            # 패키지 의존성 파일
└── README.md                   # 프로젝트 설명서
```

## 주의사항
- 네이버의 로봇 정책을 준수하여 사용하세요
- 개인 정보 수집에 주의하세요
- 무분별한 요청은 IP 차단의 원인이 될 수 있습니다
- 워드클라우드 생성 시 한글 폰트가 필요합니다

## 라이센스
이 프로젝트는 MIT 라이센스를 따릅니다. 