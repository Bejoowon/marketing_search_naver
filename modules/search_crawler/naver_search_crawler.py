#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import re
import logging
import argparse
import os
from urllib.parse import quote

# 로깅 설정
def get_logger():
    """모듈 로거 설정"""
    logger = logging.getLogger("NaverSearchCrawler")
    
    # 이미 로거가 설정되어 있는 경우 기존 로거 반환
    if logger.handlers:
        return logger
    
    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, "naver_search_crawler.log")
    
    # 로거 설정
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger

class NaverSearchCrawler:
    def __init__(self, headless=True):
        """
        네이버 검색 결과 크롤러 초기화
        
        Args:
            headless (bool): 브라우저를 헤드리스 모드로 실행할지 여부
        """
        self.logger = get_logger()
        self.setup_driver(headless)
        
    def setup_driver(self, headless):
        """셀레니움 웹드라이버 설정"""
        chrome_options = Options()
        if headless:
            chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.wait = WebDriverWait(self.driver, 10)
        
    def search_keyword(self, keyword):
        """
        네이버에서 키워드 검색
        
        Args:
            keyword (str): 검색할 키워드
        """
        encoded_keyword = quote(keyword)
        url = f"https://search.naver.com/search.naver?query={encoded_keyword}"
        self.logger.info(f"검색 URL: {url}")
        
        self.driver.get(url)
        time.sleep(3)  # 페이지 로딩 대기
    
    def find_content_sections(self):
        """페이지에서 콘텐츠 섹션 찾기"""
        try:
            time.sleep(2)  # 추가 대기
            
            # 검색 페이지에서 모든 콘텐츠 섹션 가져오기
            sections = self.driver.find_elements(By.CSS_SELECTOR, "div.api_subject_bx")
            
            self.logger.info(f"총 {len(sections)}개의 콘텐츠 섹션 발견")
            return sections
        
        except Exception as e:
            self.logger.error(f"콘텐츠 섹션 검색 중 오류 발생: {e}")
            return []
    
    def check_popular_content_exists(self, sections):
        """인기글 콘텐츠 섹션 확인"""
        popular_section = None
        popular_section_title = ""
        
        for section in sections:
            try:
                # 섹션 제목 가져오기
                section_title_element = section.find_element(By.CSS_SELECTOR, "h3, h2, strong.tit")
                if section_title_element:
                    section_title = section_title_element.text.strip()
                    
                    # "관련 브랜드 콘텐츠" 또는 "인기글" 텍스트 포함 여부 확인
                    if "인기글" in section_title or "브랜드 콘텐츠" in section_title:
                        self.logger.info(f"인기 콘텐츠 섹션 발견: '{section_title}'")
                        popular_section = section
                        popular_section_title = section_title
                        break
            
            except (NoSuchElementException, Exception) as e:
                continue
        
        if popular_section:
            return True, popular_section, popular_section_title
        else:
            self.logger.info("인기글/브랜드 콘텐츠 섹션을 찾을 수 없습니다.")
            return False, None, ""
    
    def extract_content_info_from_section(self, section):
        """섹션에서 콘텐츠 정보 추출"""
        results = []
        
        try:
            # 섹션 HTML 가져오기
            section_html = section.get_attribute('outerHTML')
            soup = BeautifulSoup(section_html, 'html.parser')
            
            # 콘텐츠 항목 찾기 시도
            content_items = soup.select("li, div.content_item")
            
            if not content_items:
                # 다른 선택자 시도
                content_items = soup.select("div.brand_area, div.content_area")
            
            if not content_items:
                self.logger.warning("섹션에서 콘텐츠 항목을 찾을 수 없습니다.")
                return results
            
            # 각 콘텐츠 항목에서 정보 추출
            for idx, item in enumerate(content_items[:20], 1):  # 최대 20개
                # 콘텐츠 타입 확인 (블로그, 카페 등)
                content_type = "알 수 없음"
                
                # 여러 가능한 선택자 시도
                type_element = (
                    item.select_one("div.detail_box span.etc") or
                    item.select_one("span.source_box") or
                    item.select_one("span.sub_txt") or
                    item.select_one("a.sub_txt") or
                    item.select_one("span.source")
                )
                
                if type_element:
                    content_type_text = type_element.text.strip()
                    if "블로그" in content_type_text:
                        content_type = "블로그"
                    elif "카페" in content_type_text:
                        content_type = "카페"
                    elif "지식iN" in content_type_text:
                        content_type = "지식iN"
                    elif "포스트" in content_type_text:
                        content_type = "포스트"
                    else:
                        content_type = content_type_text
                
                # 제목 추출
                title_element = (
                    item.select_one("a.api_txt_lines") or
                    item.select_one("strong.title") or
                    item.select_one("div.title_area") or
                    item.select_one("div.title") or
                    item.select_one("a.title_link")
                )
                
                title = title_element.text.strip() if title_element else "제목 없음"
                
                # URL 추출
                url_element = (
                    item.select_one("a.api_txt_lines") or
                    item.select_one("a.title_link") or
                    item.select_one("a")
                )
                
                url = url_element.get('href', '링크 없음') if url_element else '링크 없음'
                
                # 작성일 추출 시도
                date = ""
                # 직접적인 작성일 요소 먼저 확인
                date_element = (
                    item.select_one("div.detail_box span.time") or 
                    item.select_one("span.date") or
                    item.select_one("span.time") or
                    item.select_one("div.sub_info") or
                    item.select_one("span.sub_time") or
                    item.select_one("time.sub_time")
                )
                
                if date_element:
                    date = date_element.text.strip()
                else:
                    # span.sub 요소들 중에서 날짜 패턴 찾기
                    for sub in item.select("span.sub"):
                        text = sub.text.strip()
                        # 날짜 패턴 확인 (예: "3주 전", "2022.08.02", "5일 전")
                        if re.search(r'\d+[일주개월년](전|\s?전)|^\d{4}[-\.]\d{1,2}[-\.]\d{1,2}', text) or "전" in text:
                            if "@" not in text and "by " not in text.lower():  # 아이디가 아닌 경우만
                                date = text
                                break
                
                # 조회수 추출 시도
                view_count = ""
                view_count_element = (
                    item.select_one("div.detail_box span.view") or
                    item.select_one("span.view") or
                    item.select_one("em.view") or
                    item.select_one("span.sub_view") or
                    item.select_one("span.count") or
                    item.select_one("div.info span.view_count") or
                    item.select_one("span.hit") or
                    item.select_one("em.hit") or
                    item.select_one("div.user_info span.view") or
                    item.select_one("span.view_num") or
                    item.select_one("div.cont_info span.count")
                )
                
                if view_count_element:
                    view_count_text = view_count_element.text.strip()
                    if "조회" in view_count_text:
                        view_count = view_count_text.replace("조회", "").strip()
                    elif "조회수" in view_count_text:
                        view_count = view_count_text.replace("조회수", "").strip()
                    elif "읽음" in view_count_text:
                        view_count = view_count_text.replace("읽음", "").strip()
                    elif "조회 " in view_count_text:
                        view_count = view_count_text.replace("조회 ", "").strip()
                    else:
                        view_count = view_count_text
                
                # 조회수가 없는 경우, 모든 span 요소 검사
                if not view_count:
                    for span in item.select("span"):
                        text = span.text.strip()
                        if any(keyword in text for keyword in ["조회", "읽음", "view", "hit"]):
                            # 조회수 패턴 추출 (숫자 + 조회|읽음 또는 조회|읽음 + 숫자)
                            view_match = re.search(r'(\d[\d,.]*\s*[만천]?\s*(조회|읽음|view|hit)|(?:조회|읽음|view|hit)\s*\d[\d,.]*\s*[만천]?)', text, re.IGNORECASE)
                            if view_match:
                                view_count = view_match.group(0)
                                # 숫자만 추출
                                view_count = re.sub(r'[^\d,.만천]', '', view_count)
                                break
                
                # URL 분석으로 컨텐츠 유형 결정
                if "blog.naver.com" in url.lower():
                    content_type = "네이버 블로그"
                elif any(domain in url.lower() for domain in ["blog.", "velog.", "tistory.", "brunch."]):
                    content_type = "블로그"
                elif "cafe.naver.com" in url.lower():
                    content_type = "네이버 카페"
                elif "cafe." in url.lower():
                    content_type = "카페"
                elif "post.naver.com" in url.lower():
                    content_type = "네이버 포스트"
                elif any(domain in url.lower() for domain in ["news.", ".co.kr/", ".com/article", "media.", "/news/"]):
                    content_type = "뉴스"
                elif "kin.naver.com" in url.lower():
                    content_type = "지식iN"
                elif "youtube.com" in url.lower() or "youtu.be" in url.lower():
                    content_type = "유튜브"
                
                results.append({
                    "순번": idx,
                    "컨텐츠_유형": content_type,
                    "제목": title,
                    "작성일": date,
                    "조회수": view_count,
                    "URL": url
                })
            
            self.logger.info(f"총 {len(results)}개의 콘텐츠 정보 추출 성공")
            return results
            
        except Exception as e:
            self.logger.error(f"콘텐츠 분석 중 오류 발생: {e}")
            return results
    
    def analyze_search_result(self, keyword):
        """
        키워드 검색 결과 분석
        
        Args:
            keyword (str): 검색 키워드
            
        Returns:
            dict: 분석 결과
        """
        result = {
            "키워드": keyword,
            "인기글_탭_존재": False,
            "인기글_탭_제목": "",
            "인기글_컨텐츠": []
        }
        
        try:
            self.search_keyword(keyword)
            
            # 모든 콘텐츠 섹션 찾기
            sections = self.find_content_sections()
            
            # 인기글/브랜드 콘텐츠 섹션 찾기
            popular_exists, popular_section, section_title = self.check_popular_content_exists(sections)
            
            result["인기글_탭_존재"] = popular_exists
            result["인기글_탭_제목"] = section_title
            
            # 인기글 콘텐츠 분석
            if popular_exists and popular_section:
                result["인기글_컨텐츠"] = self.extract_content_info_from_section(popular_section)
            
            return result
        
        except Exception as e:
            self.logger.error(f"검색 결과 분석 중 오류 발생: {str(e)}")
            return result
    
    def process_keyword_list(self, input_file, output_file):
        """
        엑셀 파일에서 키워드 목록을 읽어 처리하고 결과를 CSV로 저장
        
        Args:
            input_file (str): 키워드 목록이 있는 엑셀 파일 경로
            output_file (str): 결과를 저장할 CSV 파일 경로
        """
        try:
            # 파일 확장자 확인
            file_ext = os.path.splitext(input_file)[1].lower()
            
            # 엑셀 또는 CSV 파일 읽기
            if file_ext == '.xlsx' or file_ext == '.xls':
                df = pd.read_excel(input_file)
            elif file_ext == '.csv':
                df = pd.read_csv(input_file, encoding='utf-8')
            else:
                self.logger.error(f"지원되지 않는 파일 형식: {file_ext}")
                return
            
            # 키워드 컬럼 찾기
            keyword_col = None
            for col in df.columns:
                if '키워드' in col or 'keyword' in col.lower():
                    keyword_col = col
                    break
            
            if not keyword_col:
                if len(df.columns) > 0:
                    # 첫 번째 컬럼을 키워드 컬럼으로 가정
                    keyword_col = df.columns[0]
                    self.logger.warning(f"키워드 컬럼을 명시적으로 찾을 수 없어 첫 번째 컬럼({keyword_col})을 사용합니다.")
                else:
                    self.logger.error("처리할 키워드 컬럼을 찾을 수 없습니다.")
                    return
            
            # 결과 저장을 위한 리스트
            results = []
            
            # 각 키워드 처리
            for idx, row in df.iterrows():
                keyword = str(row[keyword_col]).strip()
                if not keyword or keyword == 'nan':
                    continue
                
                self.logger.info(f"키워드 처리 중: {keyword} ({idx+1}/{len(df)})")
                result = self.analyze_search_result(keyword)
                
                # 결과 데이터 정리
                if result["인기글_컨텐츠"]:
                    for content in result["인기글_컨텐츠"]:
                        results.append({
                            "키워드": keyword,
                            "인기글_탭_존재": result["인기글_탭_존재"],
                            "인기글_탭_제목": result["인기글_탭_제목"],
                            "순번": content["순번"],
                            "컨텐츠_유형": content["컨텐츠_유형"],
                            "제목": content["제목"],
                            "작성일": content["작성일"],
                            "조회수": content["조회수"],
                            "URL": content["URL"]
                        })
                else:
                    # 인기글이 없는 경우에도 기록
                    results.append({
                        "키워드": keyword,
                        "인기글_탭_존재": result["인기글_탭_존재"],
                        "인기글_탭_제목": result["인기글_탭_제목"],
                        "순번": "",
                        "컨텐츠_유형": "",
                        "제목": "",
                        "작성일": "",
                        "조회수": "",
                        "URL": ""
                    })
            
            # 결과를 데이터프레임으로 변환
            result_df = pd.DataFrame(results)
            
            # 출력 파일 확장자 확인 및 저장
            out_ext = os.path.splitext(output_file)[1].lower()
            
            if out_ext == '.xlsx' or out_ext == '.xls':
                result_df.to_excel(output_file, index=False, engine='openpyxl')
                self.logger.info(f"결과가 엑셀 파일로 저장되었습니다: {output_file}")
            else:
                # 기본적으로 CSV로 저장
                result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                self.logger.info(f"결과가 CSV 파일로 저장되었습니다: {output_file}")
            
        except Exception as e:
            self.logger.error(f"키워드 목록 처리 중 오류 발생: {str(e)}")
    
    def close(self):
        """브라우저 닫기"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            self.logger.info("웹드라이버가 종료되었습니다.")

    def analyze_url_for_content_type(self, url):
        """
        URL을 분석하여 콘텐츠 유형 결정
        
        Args:
            url (str): 분석할 URL
            
        Returns:
            str: 콘텐츠 유형 (블로그, 카페, 포스트, 뉴스, 지식iN, 웹사이트 등)
        """
        # URL이 없는 경우
        if not url or url == '링크 없음':
            return "알 수 없음"
        
        # URL 소문자로 변환하여 분석
        url_lower = url.lower()
        
        # 네이버 블로그
        if "blog.naver.com" in url_lower:
            return "네이버 블로그"
        
        # 기타 블로그
        elif any(domain in url_lower for domain in ["blog.", "velog.", "tistory.", "brunch."]):
            return "블로그"
        
        # 네이버 카페
        elif "cafe.naver.com" in url_lower:
            return "네이버 카페"
        
        # 카페
        elif "cafe." in url_lower:
            return "카페"
        
        # 네이버 포스트
        elif "post.naver.com" in url_lower:
            return "네이버 포스트"
        
        # 뉴스
        elif any(domain in url_lower for domain in ["news.", ".co.kr/", ".com/article", "media.", "/news/"]):
            return "뉴스"
        
        # 지식iN
        elif "kin.naver.com" in url_lower:
            return "지식iN"
        
        # 유튜브
        elif "youtube.com" in url_lower or "youtu.be" in url_lower:
            return "유튜브"
        
        # 인스타그램
        elif "instagram.com" in url_lower:
            return "인스타그램"
        
        # 페이스북
        elif "facebook.com" in url_lower:
            return "페이스북"
        
        # 광고(애드크레이딧)
        elif "adcr.naver.com" in url_lower:
            return "광고"
        
        # 쇼핑몰
        elif any(domain in url_lower for domain in ["shop.", "smartstore.", "shopping.", "gmarket.", "auction.", "11st.", "coupang."]):
            return "쇼핑몰"
        
        # 검색 리다이렉트
        elif "search.naver" in url_lower:
            return "검색 결과"
        
        # 기타는 웹사이트로 분류
        return "웹사이트"


# 모듈 직접 실행 시
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="네이버 검색 결과 크롤러")
    parser.add_argument("--input", required=True, help="입력 파일 경로(키워드 목록 엑셀/CSV)")
    parser.add_argument("--output", required=True, help="출력 파일 경로(결과 저장 엑셀/CSV)")
    parser.add_argument("--headless", action="store_true", help="헤드리스 모드로 실행")
    
    args = parser.parse_args()
    
    try:
        crawler = NaverSearchCrawler(headless=args.headless)
        crawler.process_keyword_list(args.input, args.output)
    finally:
        if 'crawler' in locals():
            crawler.close() 