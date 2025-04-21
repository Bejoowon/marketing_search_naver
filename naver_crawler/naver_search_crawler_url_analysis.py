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
import urllib.parse

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
        encoded_keyword = urllib.parse.quote(keyword)
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
    
    def get_section_title(self, section):
        """섹션의 제목 추출"""
        try:
            section_title_element = section.find_element(By.CSS_SELECTOR, "h3, h2, strong.tit, span.title_area, div.title_area")
            if section_title_element:
                return section_title_element.text.strip()
        except (NoSuchElementException, Exception):
            pass
        return ""
    
    def get_all_section_titles(self, sections):
        """모든 섹션의 제목 추출"""
        section_titles = []
        for section in sections:
            title = self.get_section_title(section)
            if title:
                section_titles.append(title)
        return section_titles
    
    def find_popular_content_sections(self, sections):
        """인기글이 포함된 모든 섹션 찾기"""
        popular_sections = []
        
        for section in sections:
            try:
                # 섹션 제목 가져오기
                section_title = self.get_section_title(section)
                
                # "인기글"이 포함된 모든 섹션 찾기 (예: 패션·미용 인기글, 건강·의학 인기글 등)
                if section_title and ("인기글" in section_title or "브랜드 콘텐츠" in section_title):
                    logger.info(f"인기 콘텐츠 섹션 발견: '{section_title}'")
                    popular_sections.append((section, section_title))
            
            except (NoSuchElementException, Exception) as e:
                continue
        
        if popular_sections:
            logger.info(f"총 {len(popular_sections)}개의 인기글 섹션을 찾았습니다.")
            return True, popular_sections
        else:
            logger.info("인기글/브랜드 콘텐츠 섹션을 찾을 수 없습니다.")
            return False, []
    
    def find_first_topic_section(self, sections):
        """인기글이 없을 때 첫 번째 주제 섹션 찾기"""
        if not sections:
            return None, ""
        
        # 첫 번째 의미 있는 섹션 찾기
        for section in sections:
            try:
                section_title = self.get_section_title(section)
                if section_title and not any(exclude in section_title for exclude in ["VIEW", "검색결과", "오타체크"]):
                    logger.info(f"첫 번째 주제 섹션: '{section_title}'")
                    return section, section_title
            except Exception:
                continue
        
        return None, ""
    
    def extract_domain_from_url(self, url):
        """
        URL에서 도메인 추출
        
        Args:
            url (str): URL
            
        Returns:
            str: 도메인 이름
        """
        try:
            from urllib.parse import urlparse
            
            # URL 파싱
            parsed_url = urlparse(url)
            
            # 네트워크 위치(호스트명) 추출
            hostname = parsed_url.netloc
            
            # www. 제거
            if hostname.startswith('www.'):
                hostname = hostname[4:]
                
            # 도메인의 첫 부분만 추출 (예: naver.com -> naver)
            domain_parts = hostname.split('.')
            if len(domain_parts) > 0:
                return domain_parts[0]
            
            return hostname
        except Exception as e:
            self.logger.error(f"도메인 추출 오류: {e}")
            return ""
    
    def extract_blog_name(self, url, html_content=""):
        """
        블로그 URL에서 블로그 이름 추출
        
        Args:
            url (str): 블로그 URL
            html_content (str): HTML 콘텐츠
            
        Returns:
            str: 블로그 이름
        """
        if not url or url == '링크 없음':
            return "알 수 없는 블로그"
        
        try:
            # HTML에서 블로그 이름 찾기 시도
            soup = BeautifulSoup(html_content, 'html.parser')
            name_element = soup.select_one("a.name")
            if name_element and name_element.text.strip():
                return name_element.text.strip()
            
            # 네이버 블로그
            if "blog.naver.com" in url:
                # URL에서 블로그 ID 추출 시도
                match = re.search(r'blog\.naver\.com/([^/?&#]+)', url)
                if match:
                    return f"네이버 블로그"
                
            # 티스토리
            elif "tistory.com" in url:
                # 티스토리 블로그 이름 추출
                match = re.search(r'//([^.]+)\.tistory\.com', url)
                if match:
                    return f"티스토리"
            
            # 기타 블로그
            domain = self.extract_domain_from_url(url)
            if domain:
                return f"{domain} 블로그"
            
            return "알 수 없는 블로그"
        except:
            return "알 수 없는 블로그"
    
    def extract_blog_id(self, url):
        """블로그 URL에서 아이디 추출"""
        if not url or url == '링크 없음':
            return ""
        
        try:
            # 네이버 블로그 ID 추출
            if "blog.naver.com" in url:
                match = re.search(r'blog\.naver\.com/([^/?&#]+)', url)
                if match:
                    return match.group(1)
            
            # 티스토리 ID 추출
            elif "tistory.com" in url:
                match = re.search(r'//([^.]+)\.tistory\.com', url)
                if match:
                    return match.group(1)
            
            return ""
        except:
            return ""
    
    def extract_cafe_name(self, url, html_content=""):
        """
        카페 URL에서 카페 이름 추출
        
        Args:
            url (str): 카페 URL
            html_content (str): HTML 콘텐츠
            
        Returns:
            str: 카페 이름
        """
        if not url or url == '링크 없음':
            return "알 수 없는 카페"
        
        try:
            # HTML에서 카페 이름 찾기 시도
            soup = BeautifulSoup(html_content, 'html.parser')
            name_element = soup.select_one("a.name")
            if name_element and name_element.text.strip():
                return name_element.text.strip()
            
            # 네이버 카페
            if "cafe.naver.com" in url:
                # URL에서 카페 ID 추출 시도
                match = re.search(r'cafe\.naver\.com/([^/?&#]+)', url)
                if match:
                    return f"네이버 카페"
            
            # 다음 카페
            elif "cafe.daum.net" in url:
                match = re.search(r'cafe\.daum\.net/([^/?&#]+)', url)
                if match:
                    return f"다음 카페"
            
            # 기타 카페
            domain = self.extract_domain_from_url(url)
            if domain:
                return f"{domain} 카페"
            
            return "알 수 없는 카페"
        except:
            return "알 수 없는 카페"

    def extract_cafe_id(self, url):
        """카페 URL에서 아이디 추출"""
        if not url or url == '링크 없음':
            return ""
        
        try:
            # 네이버 카페 ID 추출
            if "cafe.naver.com" in url:
                match = re.search(r'cafe\.naver\.com/([^/?&#]+)', url)
                if match:
                    return match.group(1)
            
            # 다음 카페 ID 추출
            elif "cafe.daum.net" in url:
                match = re.search(r'cafe\.daum\.net/([^/?&#]+)', url)
                if match:
                    return match.group(1)
            
            return ""
        except:
            return ""
    
    def extract_detailed_cafe_info(self, url):
        """
        네이버 카페 URL에 접속하여 닉네임과 조회수 정보 추출
        
        Args:
            url (str): 카페 글 URL
            
        Returns:
            tuple: (닉네임, 조회수)
        """
        if not url or url == '링크 없음' or "cafe.naver.com" not in url:
            return "", ""
        
        try:
            # 현재 창 핸들 저장
            current_window = self.driver.current_window_handle
            
            # 새 탭에서 URL 열기
            self.driver.execute_script("window.open('');")
            self.driver.switch_to.window(self.driver.window_handles[-1])
            
            # URL 로드
            self.driver.get(url)
            time.sleep(2)  # 페이지 로딩 대기
            
            nickname = ""
            view_count = ""
            
            try:
                # iframe으로 전환 시도
                iframe = self.driver.find_element(By.ID, "cafe_main")
                self.driver.switch_to.frame(iframe)
                
                # 닉네임 추출 시도
                nickname_elements = self.driver.find_elements(By.CSS_SELECTOR, "button.nickname")
                if nickname_elements:
                    nickname = nickname_elements[0].text.strip()
                
                # 조회수 추출 시도
                view_elements = self.driver.find_elements(By.CSS_SELECTOR, "span.count")
                for elem in view_elements:
                    text = elem.text.strip()
                    if "조회" in text:
                        view_count = text.replace("조회", "").strip()
                        break
            
            except Exception as e:
                logger.warning(f"카페 상세 정보 추출 중 오류: {e}")
            
            # 원래 탭으로 돌아가기
            self.driver.close()
            self.driver.switch_to.window(current_window)
            
            return nickname, view_count
        
        except Exception as e:
            logger.error(f"카페 정보 추출 중 오류 발생: {e}")
            
            # 원래 탭으로 돌아가려고 시도
            try:
                self.driver.switch_to.window(current_window)
            except:
                pass
                
            return "", ""
    
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
    
    def get_author_from_content_type(self, content_type, url, html_content=""):
        """
        콘텐츠 유형에 따라 작성자(출처) 정보 추출
        
        Args:
            content_type (str): 콘텐츠 유형
            url (str): URL
            html_content (str): HTML 콘텐츠
            
        Returns:
            str: 작성자 정보
        """
        # 도메인 추출
        domain = self.extract_domain_from_url(url)
        
        # 블로그 콘텐츠
        if "블로그" in content_type:
            if "naver" in domain:
                return "네이버 블로그"
            elif "tistory" in domain:
                return "티스토리 블로그"
            elif domain:
                return f"{domain} 블로그"
            return content_type
            
        # 카페 콘텐츠
        elif "카페" in content_type:
            if "naver" in domain:
                return "네이버 카페"
            elif "daum" in domain:
                return "다음 카페"
            elif domain:
                return f"{domain} 카페"
            return content_type
            
        # 뉴스 콘텐츠
        elif "뉴스" in content_type or "기사" in content_type:
            if domain:
                return f"{domain} 뉴스"
            return "뉴스 미디어"
            
        # 유튜브 콘텐츠
        elif "유튜브" in content_type:
            return "유튜브"
            
        # 인스타그램 콘텐츠
        elif "인스타그램" in content_type:
            return "인스타그램"
            
        # 네이버 포스트
        elif "포스트" in content_type:
            return "네이버 포스트"
            
        # 지식iN
        elif "지식iN" in content_type:
            return "네이버 지식iN"
            
        # 쇼핑몰 콘텐츠
        elif "쇼핑" in content_type:
            if domain:
                return f"{domain} 쇼핑"
            return "쇼핑몰"
            
        # 웹사이트 및 기타 콘텐츠
        else:
            if domain:
                return domain
            return content_type
    
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
                
                # 게시처와 아이디 정보 추출
                # 게시처(작성자) 추출 시도 (a.name 요소)
                publisher_element = item.select_one("a.name")
                publisher_from_html = publisher_element.text.strip() if publisher_element else ""
                
                # 아이디 추출 (span.sub에서 찾기)
                user_id = ""
                sub_elements = item.select("span.sub")
                for sub in sub_elements:
                    text = sub.text.strip()
                    # id가 포함된 텍스트 패턴 찾기
                    if "@" in text or "by " in text.lower():
                        user_id = text
                        break
                
                # 작성일 추출 시도 - 더 많은 선택자 추가 및 span.sub 내부 확인
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
                    for sub in sub_elements:
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
                content_type = self.analyze_url_for_content_type(url)
                
                # 게시처 정보 가져오기
                publisher = publisher_from_html if publisher_from_html else self.get_author_from_content_type(content_type, url, str(item))
                
                # 아이디 정보 추출
                if not user_id:
                    if "블로그" in content_type:
                        user_id = self.extract_blog_id(url)
                    elif "카페" in content_type:
                        user_id = self.extract_cafe_id(url)
                
                # 네이버 카페 게시물인 경우 닉네임과 조회수 추출 시도
                if "네이버 카페" in content_type and url and url != "링크 없음":
                    nickname, cafe_view_count = self.extract_detailed_cafe_info(url)
                    if nickname:
                        user_id = nickname
                    if cafe_view_count:
                        view_count = cafe_view_count
                
                # 웹사이트의 경우 URL 확인 및 수정
                if content_type == "웹사이트" and (url == "링크 없음" or not url):
                    # 다시 한번 URL 찾기 시도
                    all_links = item.select("a")
                    if all_links:
                        for link in all_links:
                            link_url = link.get('href')
                            if link_url and link_url != "#" and not link_url.startswith("javascript:"):
                                url = link_url
                                break
                
                results.append({
                    "순번": idx,
                    "컨텐츠_유형": content_type,
                    "제목": title,
                    "게시처": publisher,
                    "아이디": user_id,
                    "작성일": date,
                    "조회수": view_count,
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
            "검색_URL": f"https://search.naver.com/search.naver?query={urllib.parse.quote(keyword)}",
            "인기글_탭_존재": False,
            "인기글_탭_제목": [],
            "인기글_컨텐츠": [],
            "첫번째_섹션": "",
            "모든_섹션": []
        }
        
        try:
            self.search_keyword(keyword)
            
            # 모든 콘텐츠 섹션 찾기
            sections = self.find_content_sections()
            
            # 모든 섹션 제목 가져오기
            all_section_titles = self.get_all_section_titles(sections)
            result["모든_섹션"] = all_section_titles
            
            # 인기글/브랜드 콘텐츠 섹션 찾기
            popular_exists, popular_sections = self.find_popular_content_sections(sections)
            
            result["인기글_탭_존재"] = popular_exists
            
            # 인기글 콘텐츠 분석
            if popular_exists and popular_sections:
                # 인기글 탭 제목 추가
                result["인기글_탭_제목"] = [title for _, title in popular_sections]
                
                # 모든 인기글 섹션에서 콘텐츠 추출
                all_contents = []
                
                for section, title in popular_sections:
                    logger.info(f"'{title}' 섹션에서 콘텐츠 추출 중...")
                    section_contents = self.extract_content_info_from_section(section)
                    
                    # 섹션별 메타데이터 추가
                    for content in section_contents:
                        content["섹션"] = title
                    
                    all_contents.extend(section_contents)
                
                result["인기글_컨텐츠"] = all_contents
            else:
                # 인기글이 없는 경우 첫 번째 주제 섹션 정보 추출
                first_section, first_title = self.find_first_topic_section(sections)
                result["첫번째_섹션"] = first_title
            
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
            
            all_results = []        # 요약 정보
            content_results = []    # 인기글 컨텐츠 정보
            section_results = []    # 섹션 정보
            
            # 각 키워드에 대해 검색 결과 분석
            for keyword in keywords:
                if not isinstance(keyword, str):
                    keyword = str(keyword)
                
                logger.info(f"\n{'='*50}\n검색 키워드: {keyword}\n{'='*50}")
                
                result = self.analyze_search_result(keyword)
                
                # 키워드별 인기글 탭 존재 여부 저장
                all_results.append({
                    "키워드": keyword,
                    "검색_URL": result["검색_URL"],
                    "인기글_탭_존재": result["인기글_탭_존재"],
                    "인기글_탭_제목": ", ".join(result["인기글_탭_제목"]) if result["인기글_탭_제목"] else "",
                    "첫번째_섹션": result["첫번째_섹션"] if not result["인기글_탭_존재"] else ""
                })
                
                # 키워드별 모든 섹션 정보 저장
                section_row = {"키워드": keyword}
                for idx, section in enumerate(result["모든_섹션"][:10], 1):  # 최대 10개 섹션까지만
                    section_row[f"{idx}순위"] = section
                section_results.append(section_row)
                
                # 인기글 컨텐츠 정보 저장
                for content in result["인기글_컨텐츠"]:
                    content_results.append({
                        "키워드": keyword,
                        "검색_URL": result["검색_URL"],
                        "섹션": content.get("섹션", ""),
                        "순번": content["순번"],
                        "컨텐츠_유형": content["컨텐츠_유형"],
                        "제목": content["제목"],
                        "게시처": content.get("게시처", ""),
                        "아이디": content.get("아이디", ""),
                        "작성일": content.get("작성일", ""),
                        "조회수": content.get("조회수", ""),
                        "URL": content["URL"]
                    })
            
            # 결과를 데이터프레임으로 변환
            all_df = pd.DataFrame(all_results)
            content_df = pd.DataFrame(content_results)
            section_df = pd.DataFrame(section_results)
            
            # 결과 저장
            output_base = os.path.splitext(output_file)[0]
            
            # 탭 존재 여부 파일
            all_df.to_csv(f"{output_base}_summary.csv", index=False, encoding='utf-8-sig')
            
            # 섹션 정보 파일
            section_df.to_csv(f"{output_base}_sections.csv", index=False, encoding='utf-8-sig')
            
            # 컨텐츠 유형 통계 계산
            if not content_df.empty:
                # 컨텐츠 유형별 카운트
                type_counts = content_df['컨텐츠_유형'].value_counts().reset_index()
                type_counts.columns = ['컨텐츠_유형', '개수']
                
                # 섹션별 카운트
                section_counts = content_df['섹션'].value_counts().reset_index()
                section_counts.columns = ['섹션', '개수']
                
                # 인기글 컨텐츠 파일 저장
                content_df.to_csv(f"{output_base}_contents.csv", index=False, encoding='utf-8-sig')
                
                # 엑셀 파일로도 저장
                with pd.ExcelWriter(f"{output_base}.xlsx") as writer:
                    all_df.to_excel(writer, sheet_name='탭 요약', index=False)
                    section_df.to_excel(writer, sheet_name='섹션 정보', index=False)
                    content_df.to_excel(writer, sheet_name='인기글 컨텐츠', index=False)
                    type_counts.to_excel(writer, sheet_name='컨텐츠 유형 통계', index=False)
                    section_counts.to_excel(writer, sheet_name='섹션 통계', index=False)
            else:
                # 빈 컨텐츠인 경우도 엑셀 파일 저장
                with pd.ExcelWriter(f"{output_base}.xlsx") as writer:
                    all_df.to_excel(writer, sheet_name='탭 요약', index=False)
                    section_df.to_excel(writer, sheet_name='섹션 정보', index=False)
                    pd.DataFrame(columns=["키워드", "검색_URL", "섹션", "순번", "컨텐츠_유형", "제목", "게시처", "아이디", "작성일", "조회수", "URL"]).to_excel(writer, sheet_name='인기글 컨텐츠', index=False)
            
            logger.info(f"결과가 {output_base}_summary.csv, {output_base}_sections.csv, {output_base}_contents.csv, {output_base}.xlsx에 저장되었습니다.")
            
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
    parser = argparse.ArgumentParser(description='네이버 검색 결과 크롤러 (URL 분석 기능 추가)')
    parser.add_argument('--input', '-i', type=str, required=True, help='키워드 목록이 있는 파일 경로 (.xlsx, .xls, .csv)')
    parser.add_argument('--output', '-o', type=str, default='naver_search_results', help='결과를 저장할 파일 경로 (확장자 제외)')
    parser.add_argument('--visible', '-v', action='store_true', help='브라우저를 화면에 표시합니다')
    
    args = parser.parse_args()
    
    crawler = NaverSearchCrawler(headless=not args.visible)
    crawler.process_keyword_list(args.input, args.output)

if __name__ == "__main__":
    main() 