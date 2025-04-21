# 네이버 검색 크롤러

네이버 검색 결과에서 인기글을 자동으로 수집하고 분석하는 도구입니다. 이 프로그램은 키워드를 입력하면 네이버 검색 결과에서 '인기글' 탭이 있는지 확인하고, 해당 콘텐츠의 정보를 수집하여 Excel과 CSV 형식으로 저장합니다.

## 🌟 주요 기능

- 네이버 검색 결과에서 인기글 탭 확인
- 인기글 콘텐츠 타입, 순위, 제목, URL 등 상세 정보 수집
- URL 분석을 통한 정확한 콘텐츠 분류
- 결과 파일을 Excel, CSV 형식으로 저장
- 사용자 친화적인 GUI 인터페이스
- 조회수, 제목, 게시처, 작성일 등 상세 정보 제공
- 엑셀에서 키워드 목록 복사/붙여넣기 지원
- 생성시간이 포함된 결과 파일 생성 (자동 파일 관리)

## 📋 요구사항

- Python 3.6 이상
- Chrome 브라우저
- 필요 Python 패키지:
  - selenium
  - pandas
  - beautifulsoup4
  - webdriver-manager
  - tkinter (GUI용)

## 🔧 설치 방법

1. 이 저장소를 클론합니다.
   ```bash
   git clone https://github.com/yourusername/naver-search-crawler.git
   cd naver-search-crawler
   ```

2. 필요한 Python 패키지를 설치합니다.
   ```bash
   pip install -r requirements.txt
   ```

## 🚀 사용 방법

### GUI 모드 실행

```bash
python naver_crawler/run_gui.py
```

1. 키워드를 직접 입력하거나 Excel/CSV 파일에서 키워드를 불러옵니다.
   - 키워드는 쉼표(,) 또는 줄바꿈으로 구분해 직접 입력할 수 있습니다.
   - 엑셀에서 복사한 셀 범위를 그대로 붙여넣을 수 있습니다.

2. 결과 저장 경로를 설정합니다.
   - 기본 저장 위치는 'results' 폴더입니다.
   - 파일명에는 자동으로 생성 시간이 포함됩니다.

3. '크롤링 시작' 버튼을 클릭하여 수집을 시작합니다.

4. 수집이 완료되면 왼쪽 하단의 바로가기 버튼으로 결과 파일에 접근할 수 있습니다.

### 명령줄 모드 실행

```bash
python naver_crawler/naver_search_crawler_url_analysis.py --input keywords.xlsx --output results/naver_search_results
```

## 📊 결과 파일 형식

- `[출력파일명]_[타임스탬프].xlsx`: 모든 결과가 포함된 Excel 파일
- `[출력파일명]_[타임스탬프]_summary.csv`: 키워드별 인기글 탭 존재 여부
- `[출력파일명]_[타임스탬프]_sections.csv`: 키워드별 섹션 정보
- `[출력파일명]_[타임스탬프]_contents.csv`: 인기글 콘텐츠 상세 정보

## 🔍 수집하는 콘텐츠 유형

- 네이버 블로그
- 네이버 카페
- 티스토리 블로그
- 네이버 포스트
- 유튜브
- 인스타그램
- 웹사이트
- 뉴스
- 지식iN
- 쇼핑몰
- 기타 웹사이트

## 🚨 문제 해결

- Chrome 브라우저가 설치되어 있어야 합니다.
- 실행 중 ChromeDriver 관련 오류가 발생하면 `webdriver-manager`가 자동으로 적절한 버전을 설치합니다.
- 네트워크 연결 상태가 좋지 않으면 타임아웃 오류가 발생할 수 있습니다.
- 네이버 검색 HTML 구조 변경 시 크롤링이 제대로 작동하지 않을 수 있습니다.

## 📝 라이선스

MIT 라이선스

## ⚠️ 면책 조항

이 도구는 학습 및 연구 목적으로 제작되었습니다. 크롤링한 데이터는 개인 연구용으로만 사용하시고, 상업적 목적이나 저작권 침해 목적으로 사용하지 마세요. 네이버의 이용약관을 준수하는 방식으로 사용해주세요. 