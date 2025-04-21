#!/usr/bin/env python
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import argparse
import os

def save_page_source(keyword, output_dir='.'):
    """
    네이버 검색 페이지의 HTML 소스를 저장
    
    Args:
        keyword (str): 검색할 키워드
        output_dir (str): 출력 디렉토리
    """
    # 출력 디렉토리 생성
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
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
        url = f"https://search.naver.com/search.naver?query={keyword}"
        print(f"검색 URL: {url}")
        driver.get(url)
        
        # 페이지 로딩 대기
        time.sleep(5)
        
        # HTML 소스 저장
        html_path = os.path.join(output_dir, f'naver_search_{keyword.replace(" ", "_")}.html')
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        print(f"HTML 소스가 저장되었습니다: {html_path}")
        
        # 스크린샷 저장
        screenshot_path = os.path.join(output_dir, f'naver_search_{keyword.replace(" ", "_")}.png')
        driver.save_screenshot(screenshot_path)
        print(f"스크린샷이 저장되었습니다: {screenshot_path}")
        
        # 현재 페이지에서 사용 가능한 탭 정보 출력
        print("\n현재 페이지의 탭 정보:")
        tabs = driver.find_elements("css selector", "ul.tabs_content li, ul.tab_list li, div.api_more_wrap ul li")
        
        if tabs:
            for idx, tab in enumerate(tabs, 1):
                try:
                    print(f"탭 {idx}: {tab.text} (클래스: {tab.get_attribute('class')})")
                except:
                    print(f"탭 {idx}: [텍스트 추출 실패]")
        else:
            print("페이지에서 탭을 찾을 수 없습니다.")
        
        # 인기컨텐츠 영역 확인
        print("\n인기컨텐츠 영역 확인:")
        popular_sections = driver.find_elements("css selector", "div.popular_area, div.api_subject_bx, div.content_area")
        
        if popular_sections:
            for idx, section in enumerate(popular_sections, 1):
                try:
                    print(f"섹션 {idx}: (클래스: {section.get_attribute('class')})")
                    print(f"내용 일부: {section.text[:100]}...\n")
                except:
                    print(f"섹션 {idx}: [정보 추출 실패]")
        else:
            print("페이지에서 인기컨텐츠 영역을 찾을 수 없습니다.")
        
        # 5초 더 대기
        time.sleep(5)
        
    finally:
        # 드라이버 종료
        driver.quit()
        print("웹드라이버가 종료되었습니다.")

def main():
    parser = argparse.ArgumentParser(description='네이버 검색 페이지 HTML 구조 확인')
    parser.add_argument('keyword', type=str, help='검색할 키워드')
    parser.add_argument('--output', '-o', type=str, default='naver_data', help='출력 디렉토리')
    
    args = parser.parse_args()
    save_page_source(args.keyword, args.output)

if __name__ == "__main__":
    main() 