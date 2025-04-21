#!/usr/bin/env python
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import argparse
from urllib.parse import quote

def check_section_titles(keyword):
    """
    네이버 검색 페이지의 모든 섹션 제목을 확인
    
    Args:
        keyword (str): 검색할 키워드
    """
    # 웹드라이버 설정
    chrome_options = Options()
    # chrome_options.add_argument("--headless")  # 헤드리스 모드는 주석 처리
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 드라이버 초기화
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        # 네이버 검색
        encoded_keyword = quote(keyword)
        url = f"https://search.naver.com/search.naver?query={encoded_keyword}"
        print(f"검색 URL: {url}")
        driver.get(url)
        
        # 페이지 로딩 대기
        time.sleep(5)
        
        # 모든 섹션 찾기
        sections = driver.find_elements(By.CSS_SELECTOR, "div.api_subject_bx")
        
        print(f"\n총 {len(sections)}개의 콘텐츠 섹션 발견\n")
        
        found_popular = False
        
        # 모든 섹션의 제목 요소 검사
        for idx, section in enumerate(sections, 1):
            try:
                # 섹션 HTML 가져오기
                section_html = section.get_attribute('outerHTML')
                soup = BeautifulSoup(section_html, 'html.parser')
                
                # 섹션 클래스 출력
                section_class = section.get_attribute('class')
                print(f"섹션 {idx} 클래스: {section_class}")
                
                # 가능한 제목 요소 찾기
                title_elements = soup.select("h2, h3, h4, strong.tit, span.title_area, div.title_area")
                
                if title_elements:
                    for title_elem in title_elements:
                        title_text = title_elem.text.strip()
                        if title_text:
                            print(f"- 제목요소({title_elem.name}): '{title_text}'")
                            
                            # "브랜드 콘텐츠" 또는 "인기글" 확인
                            if "브랜드 콘텐츠" in title_text or "인기글" in title_text:
                                found_popular = True
                                print(f"  !!! 인기/브랜드 콘텐츠 발견 !!! - '{title_text}'")
                                
                                # 이 섹션 내의 콘텐츠 항목 찾기
                                content_items = soup.select("li, div.content_item")
                                print(f"  콘텐츠 항목 수: {len(content_items)}")
                                
                                # 첫 번째 콘텐츠 항목의 정보 표시
                                if content_items:
                                    first_item = content_items[0]
                                    print(f"  첫 번째 항목 클래스: {first_item.get('class', 'N/A')}")
                                    print(f"  첫 번째 항목 내용: {first_item.text[:100] if len(first_item.text) > 100 else first_item.text}")
                else:
                    print(f"- 제목 요소 없음")
                
                print("\n")
            
            except Exception as e:
                print(f"섹션 {idx} 처리 중 오류: {e}\n")
        
        if not found_popular:
            print("\n어떤 섹션에서도 '브랜드 콘텐츠' 또는 '인기글' 관련 제목을 찾지 못했습니다.")
        
        # 5초 더 대기
        time.sleep(5)
        
    finally:
        # 드라이버 종료
        driver.quit()
        print("\n웹드라이버가 종료되었습니다.")

def main():
    parser = argparse.ArgumentParser(description='네이버 검색 페이지 섹션 제목 확인')
    parser.add_argument('keyword', type=str, help='검색할 키워드')
    
    args = parser.parse_args()
    check_section_titles(args.keyword)

if __name__ == "__main__":
    main() 