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
    
    def find_content_sections(self):
        """페이지에서 콘텐츠 섹션 찾기"""
        try:
            time.sleep(2)  # 추가 대기
            
            # 검색 페이지에서 모든 콘텐츠 섹션 가져오기
            sections = self.driver.find_elements(By.CSS_SELECTOR, "div.api_subject_bx")
            
            logger.info(f"총 {len(sections)}개의 콘텐츠 섹션 발견")
            return sections
        
        except Exception as e:
            logger.error(f"콘텐츠 섹션 검색 중 오류 발생: {e}")
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
                        logger.info(f"인기 콘텐츠 섹션 발견: '{section_title}'")
                        popular_section = section
                        popular_section_title = section_title
                        break
            
            except (NoSuchElementException, Exception) as e:
                continue
        
        if popular_section:
            return True, popular_section, popular_section_title
        else:
            logger.info("인기글/브랜드 콘텐츠 섹션을 찾을 수 없습니다.")
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
                logger.warning("섹션에서 콘텐츠 항목을 찾을 수 없습니다.")
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
                
                results.append({
                    "순번": idx,
                    "컨텐츠 유형": content_type,
                    "제목": title,
                    "URL": url
                })
            
            logger.info(f"총 {len(results)}개의 콘텐츠 정보 추출 성공")
            return results
            
        except Exception as e:
            logger.error(f"콘텐츠 분석 중 오류 발생: {e}")
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
            # 파일 확장자 확인
            file_ext = os.path.splitext(input_file)[1].lower()
            
            # 엑셀 또는 CSV 파일 읽기
            if file_ext == '.xlsx' or file_ext == '.xls':
                df = pd.read_excel(input_file)
            elif file_ext == '.csv':
                df = pd.read_csv(input_file, encoding='utf-8')
            else:
                raise ValueError("지원하지 않는 파일 형식입니다. .xlsx, .xls, .csv 형식만 지원합니다.")
            
            # 키워드 열 확인
            if 'keyword' not in df.columns and '키워드' not in df.columns:
                raise ValueError("파일에 'keyword' 또는 '키워드' 열이 없습니다.")
            
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
                    "인기글_탭_존재": result["인기글_탭_존재"],
                    "인기글_탭_제목": result["인기글_탭_제목"]
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
            else:
                # 빈 컨텐츠인 경우도 엑셀 파일 저장
                with pd.ExcelWriter(f"{output_base}.xlsx") as writer:
                    all_df.to_excel(writer, sheet_name='탭 요약', index=False)
                    pd.DataFrame(columns=["키워드", "순번", "컨텐츠_유형", "제목", "URL"]).to_excel(writer, sheet_name='인기글 컨텐츠', index=False)
            
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
    parser.add_argument('--input', '-i', type=str, required=True, help='키워드 목록이 있는 파일 경로 (.xlsx, .xls, .csv)')
    parser.add_argument('--output', '-o', type=str, default='naver_search_results', help='결과를 저장할 파일 경로 (확장자 제외)')
    parser.add_argument('--visible', '-v', action='store_true', help='브라우저를 화면에 표시합니다')
    
    args = parser.parse_args()
    
    crawler = NaverSearchCrawler(headless=not args.visible)
    crawler.process_keyword_list(args.input, args.output)

if __name__ == "__main__":
    main() 