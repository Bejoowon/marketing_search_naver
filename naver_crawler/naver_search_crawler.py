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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('naver_crawler.log')
    ]
)
logger = logging.getLogger(__name__)

class NaverSearchCrawler:
    def __init__(self, headless=True):
        """
        네이버 검색 결과 크롤러 초기화
        
        Args:
            headless (bool): 브라우저를 헤드리스 모드로 실행할지 여부
        """
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
        logger.info(f"검색 URL: {url}")
        
        self.driver.get(url)
        time.sleep(3)  # 페이지 로딩 대기
    
    def check_popular_tab_exists(self):
        """인기글 탭이 있는지 확인"""
        try:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.tabs_content")))
            tabs = self.driver.find_elements(By.CSS_SELECTOR, "ul.tabs_content li")
            
            for tab in tabs:
                tab_text = tab.text.strip()
                if "인기글" in tab_text:
                    logger.info("인기글 탭 발견")
                    return True, tab
            
            logger.info("인기글 탭을 찾을 수 없습니다.")
            return False, None
        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"탭 확인 중 오류 발생: {e}")
            return False, None
    
    def click_popular_tab(self, tab_element):
        """인기글 탭 클릭"""
        try:
            tab_element.click()
            time.sleep(2)  # 탭 로딩 대기
            logger.info("인기글 탭 클릭 성공")
            return True
        except Exception as e:
            logger.error(f"인기글 탭 클릭 중 오류 발생: {e}")
            return False
    
    def extract_content_info(self):
        """인기글 탭의 컨텐츠 정보 추출"""
        results = []
        
        try:
            # 현재 페이지의 HTML 가져오기
            html = self.driver.page_source
            soup = BeautifulSoup(html, 'html.parser')
            
            # 컨텐츠 항목들 찾기 (여러 형태의 컨텐츠 선택자 시도)
            content_items = soup.select("li.bx")
            
            if not content_items:
                content_items = soup.select("div.total_wrap ul > li")
            
            if not content_items:
                content_items = soup.select("div.view_cont div.api_subject_bx")
            
            if not content_items:
                logger.warning("인기글 컨텐츠를 찾을 수 없습니다.")
                return results
            
            # 각 컨텐츠 항목에서 정보 추출
            for idx, item in enumerate(content_items[:20], 1):  # 최대 20개까지만 추출
                content_type = "알 수 없음"
                
                # 컨텐츠 유형 추출 시도
                type_element = item.select_one("a.sub_txt") or item.select_one("span.sub_txt") or item.select_one("span.source")
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
                title_element = item.select_one("a.title_link") or item.select_one("div.title_area") or item.select_one("div.title")
                title = title_element.text.strip() if title_element else "제목 없음"
                
                # URL 추출
                url_element = item.select_one("a.title_link") or item.select_one("a.api_txt_lines")
                url = url_element.get('href', '링크 없음') if url_element else '링크 없음'
                
                results.append({
                    "순번": idx,
                    "컨텐츠 유형": content_type,
                    "제목": title,
                    "URL": url
                })
            
            logger.info(f"총 {len(results)}개의 인기글 컨텐츠 정보 추출 성공")
            return results
        
        except Exception as e:
            logger.error(f"인기글 컨텐츠 분석 중 오류 발생: {e}")
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
            "인기글_컨텐츠": []
        }
        
        try:
            self.search_keyword(keyword)
            
            # 인기글 탭 확인
            popular_tab_exists, tab_element = self.check_popular_tab_exists()
            result["인기글_탭_존재"] = popular_tab_exists
            
            # 인기글 탭이 있으면 클릭하고 컨텐츠 분석
            if popular_tab_exists and tab_element:
                if self.click_popular_tab(tab_element):
                    result["인기글_컨텐츠"] = self.extract_content_info()
            
            return result
        
        except Exception as e:
            logger.error(f"검색 결과 분석 중 오류 발생: {str(e)}")
            return result
    
    def process_keyword_list(self, input_file, output_file):
        """
        엑셀 파일에서 키워드 목록을 읽어 처리하고 결과를 CSV로 저장
        
        Args:
            input_file (str): 키워드 목록이 있는 엑셀 파일 경로
            output_file (str): 결과를 저장할 CSV 파일 경로
        """
        try:
            # 엑셀 파일 읽기
            df = pd.read_excel(input_file)
            
            if 'keyword' not in df.columns and '키워드' not in df.columns:
                raise ValueError("엑셀 파일에 'keyword' 또는 '키워드' 열이 없습니다.")
            
            keyword_col = 'keyword' if 'keyword' in df.columns else '키워드'
            keywords = df[keyword_col].tolist()
            
            all_results = []
            content_results = []
            
            # 각 키워드에 대해 검색 결과 분석
            for keyword in keywords:
                logger.info(f"\n{'='*50}\n검색 키워드: {keyword}\n{'='*50}")
                
                result = self.analyze_search_result(keyword)
                
                # 키워드별 인기글 탭 존재 여부 저장
                all_results.append({
                    "키워드": keyword,
                    "인기글_탭_존재": result["인기글_탭_존재"]
                })
                
                # 인기글 컨텐츠 정보 저장
                for content in result["인기글_컨텐츠"]:
                    content_results.append({
                        "키워드": keyword,
                        "순번": content["순번"],
                        "컨텐츠_유형": content["컨텐츠 유형"],
                        "제목": content["제목"],
                        "URL": content["URL"]
                    })
            
            # 결과를 데이터프레임으로 변환
            all_df = pd.DataFrame(all_results)
            content_df = pd.DataFrame(content_results)
            
            # 결과 저장
            output_base = os.path.splitext(output_file)[0]
            
            # 탭 존재 여부 파일
            all_df.to_csv(f"{output_base}_summary.csv", index=False, encoding='utf-8-sig')
            
            # 인기글 컨텐츠 파일 (컨텐츠가 있는 경우만)
            if not content_df.empty:
                content_df.to_csv(f"{output_base}_contents.csv", index=False, encoding='utf-8-sig')
                
                # 엑셀 파일로도 저장
                with pd.ExcelWriter(f"{output_base}.xlsx") as writer:
                    all_df.to_excel(writer, sheet_name='탭 요약', index=False)
                    content_df.to_excel(writer, sheet_name='인기글 컨텐츠', index=False)
            
            logger.info(f"결과가 {output_base}_summary.csv, {output_base}_contents.csv, {output_base}.xlsx에 저장되었습니다.")
            
        except Exception as e:
            logger.error(f"키워드 처리 중 오류 발생: {str(e)}")
        finally:
            self.close()
    
    def close(self):
        """드라이버 종료"""
        if hasattr(self, 'driver'):
            self.driver.quit()
            logger.info("웹드라이버가 종료되었습니다.")

def main():
    parser = argparse.ArgumentParser(description='네이버 검색 결과 크롤러')
    parser.add_argument('--input', '-i', type=str, required=True, help='키워드 목록이 있는 엑셀 파일 경로')
    parser.add_argument('--output', '-o', type=str, default='naver_search_results', help='결과를 저장할 파일 경로 (확장자 제외)')
    parser.add_argument('--visible', '-v', action='store_true', help='브라우저를 화면에 표시합니다')
    
    args = parser.parse_args()
    
    crawler = NaverSearchCrawler(headless=not args.visible)
    crawler.process_keyword_list(args.input, args.output)

if __name__ == "__main__":
    main() 