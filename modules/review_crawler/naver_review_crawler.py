#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import time
import json
import logging
import argparse
import pandas as pd
from datetime import datetime
from urllib.parse import quote, unquote, urlparse, parse_qs
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


# 로깅 설정
def get_logger():
    """모듈 로거 설정"""
    logger = logging.getLogger("NaverReviewCrawler")
    
    # 이미 로거가 설정되어 있는 경우 기존 로거 반환
    if logger.handlers:
        return logger
    
    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, "naver_review_crawler.log")
    
    # 로거 설정
    logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


class NaverReviewCrawler:
    """네이버 쇼핑 구매평 크롤러 클래스"""
    
    def __init__(self, headless=True):
        """
        네이버 구매평 크롤러 초기화
        
        Args:
            headless (bool): 브라우저를 헤드리스 모드로 실행할지 여부
        """
        self.logger = get_logger()
        self.headless = headless
        self.browser = None
        self.page = None
        self.results_dir = "results/reviews"
        
        # 결과 저장 디렉토리 생성
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
    
    def start_browser(self):
        """Playwright 브라우저 시작"""
        if self.browser is None:
            self.logger.info("브라우저 시작 중...")
            playwright = sync_playwright().start()
            self.browser = playwright.chromium.launch(headless=self.headless)
            self.page = self.browser.new_page()
            self.page.set_default_timeout(30000)  # 30초 타임아웃 설정
            
            # 사용자 에이전트 설정
            self.page.set_extra_http_headers({
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            })
            
            self.logger.info("브라우저 시작 완료")
    
    def extract_product_id(self, url):
        """URL에서 상품 ID 추출
        
        Args:
            url (str): 상품 URL
            
        Returns:
            str: 상품 ID
        """
        # 네이버 쇼핑 상품 페이지 URL 패턴 처리
        patterns = [
            r'products/(\d+)',  # https://smartstore.naver.com/xxx/products/123456789
            r'product/(\d+)',   # https://brand.naver.com/xxx/product/123456789
            r'catalog/(\d+)',   # https://search.shopping.naver.com/catalog/123456789
            r'nvMid=(\d+)'      # nvMid 파라미터에서 추출
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # URL 쿼리 파라미터에서 상품 ID 추출 시도
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        
        if 'nvMid' in query_params:
            return query_params['nvMid'][0]
        
        # 상품 ID를 찾을 수 없는 경우
        self.logger.warning(f"URL에서 상품 ID를 추출할 수 없습니다: {url}")
        return None
        
    def get_review_api_url(self, product_id, page_index=1, page_size=30):
        """리뷰 API URL 생성
        
        Args:
            product_id (str): 상품 ID
            page_index (int): 페이지 번호 (1부터 시작)
            page_size (int): 페이지당 리뷰 수
            
        Returns:
            str: 리뷰 API URL
        """
        base_url = "https://smartstore.naver.com/i/v1/reviews/paged-reviews"
        params = {
            'vendorItemId': product_id,
            'page': page_index,
            'pageSize': page_size,
            'sortType': 'REVIEW_RANKING'  # 베스트순 정렬
        }
        
        query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    def navigate_to_product(self, url):
        """상품 페이지로 이동
        
        Args:
            url (str): 상품 URL
            
        Returns:
            bool: 성공 여부
        """
        try:
            self.logger.info(f"상품 페이지 접속 중: {url}")
            self.page.goto(url, wait_until="domcontentloaded")
            time.sleep(3)  # 페이지 로딩 대기
            
            # 페이지 제목 확인
            title = self.page.title()
            self.logger.info(f"페이지 제목: {title}")
            
            return True
            
        except PlaywrightTimeoutError:
            self.logger.error(f"페이지 로딩 시간 초과: {url}")
            return False
            
        except Exception as e:
            self.logger.error(f"페이지 접속 중 오류 발생: {str(e)}")
            return False
    
    def fetch_reviews_via_api(self, product_id, max_pages=10):
        """API를 통해 리뷰 데이터 수집
        
        Args:
            product_id (str): 상품 ID
            max_pages (int): 최대 수집할 페이지 수
            
        Returns:
            list: 수집된 리뷰 데이터 목록
        """
        reviews = []
        has_more = True
        page_index = 1
        
        self.logger.info(f"상품 ID {product_id}의 리뷰 수집 시작")
        
        # 헤더에 Referer 추가
        referer_url = f"https://smartstore.naver.com/main/products/{product_id}"
        
        while has_more and page_index <= max_pages:
            try:
                api_url = self.get_review_api_url(product_id, page_index)
                self.logger.info(f"리뷰 API 호출: {api_url} (페이지 {page_index})")
                
                # API 호출
                response = self.page.evaluate(f"""
                    async () => {{
                        const response = await fetch("{api_url}", {{
                            "headers": {{
                                "accept": "application/json, text/plain, */*",
                                "accept-language": "ko-KR,ko;q=0.9",
                                "referer": "{referer_url}"
                            }},
                            "method": "GET",
                            "credentials": "include"
                        }});
                        
                        if (!response.ok) {{
                            return {{ error: response.status }};
                        }}
                        
                        return await response.json();
                    }}
                """)
                
                # 오류 확인
                if isinstance(response, dict) and 'error' in response:
                    self.logger.error(f"API 응답 오류: {response['error']}")
                    break
                
                # 리뷰 데이터 추출
                if response and 'contents' in response:
                    page_reviews = response['contents']
                    page_review_count = len(page_reviews)
                    
                    if page_review_count == 0:
                        self.logger.info(f"더 이상 리뷰 데이터가 없습니다 (페이지 {page_index})")
                        has_more = False
                    else:
                        self.logger.info(f"페이지 {page_index}에서 {page_review_count}개의 리뷰를 수집했습니다")
                        reviews.extend(page_reviews)
                        
                        # 마지막 페이지 확인
                        total_pages = response.get('totalPages', 1)
                        if page_index >= total_pages:
                            self.logger.info(f"마지막 페이지에 도달했습니다 (총 {total_pages} 페이지)")
                            has_more = False
                else:
                    self.logger.warning(f"리뷰 데이터를 찾을 수 없습니다 (페이지 {page_index})")
                    has_more = False
                
                # 다음 페이지로 이동
                page_index += 1
                time.sleep(1.5)  # API 호출 간격 조절
                
            except Exception as e:
                self.logger.error(f"리뷰 데이터 수집 중 오류 발생: {str(e)}")
                break
        
        self.logger.info(f"총 {len(reviews)}개의 리뷰를 수집했습니다")
        return reviews
    
    def extract_review_data(self, reviews):
        """리뷰 데이터 가공
        
        Args:
            reviews (list): API에서 가져온 원본 리뷰 데이터
            
        Returns:
            list: 가공된 리뷰 데이터 목록
        """
        extracted_reviews = []
        
        for i, review in enumerate(reviews, 1):
            try:
                # 기본 정보 추출
                review_id = review.get('id', '')
                content = review.get('contents', '').strip()
                rating = review.get('reviewScore', 0)
                
                # 작성자 정보
                writer_info = review.get('writerInfo', {})
                writer_id = writer_info.get('id', '')
                writer_name = writer_info.get('name', '')
                
                # 날짜 정보 변환
                created_at = review.get('createdDate', '')
                if created_at:
                    # 타임스탬프를 날짜 형식으로 변환
                    if isinstance(created_at, (int, float)):
                        created_at = datetime.fromtimestamp(created_at/1000).strftime('%Y-%m-%d %H:%M:%S')
                
                # 구매 정보
                is_purchase = review.get('purchasedProductInfo', {}) is not None
                
                # 옵션 정보
                option_info = ''
                purchased_product = review.get('purchasedProductInfo', {})
                if purchased_product:
                    options = purchased_product.get('optionCombinations', [])
                    option_parts = []
                    for option in options:
                        name = option.get('optionName', '')
                        value = option.get('optionValue', '')
                        if name and value:
                            option_parts.append(f"{name}: {value}")
                    option_info = ' / '.join(option_parts)
                
                # 이미지 정보
                image_urls = []
                attach_info = review.get('attachFiles', [])
                for attach in attach_info:
                    if attach.get('fileType', '') == 'IMAGE':
                        image_url = attach.get('url', '')
                        if image_url:
                            image_urls.append(image_url)
                
                # 리뷰 데이터 구조화
                extracted_review = {
                    "순번": i,
                    "리뷰ID": review_id,
                    "작성자ID": writer_id,
                    "작성자명": writer_name,
                    "별점": rating,
                    "구매확정": "Y" if is_purchase else "N",
                    "옵션정보": option_info,
                    "작성일자": created_at,
                    "리뷰내용": content,
                    "이미지URL": ';'.join(image_urls)
                }
                
                extracted_reviews.append(extracted_review)
                
            except Exception as e:
                self.logger.error(f"리뷰 데이터 처리 중 오류 발생: {str(e)}")
                continue
        
        return extracted_reviews
    
    def crawl_product_reviews(self, product_url, max_pages=10):
        """상품 구매평 크롤링
        
        Args:
            product_url (str): 상품 URL
            max_pages (int): 최대 수집할 페이지 수
            
        Returns:
            list: 수집된 구매평 목록
        """
        self.start_browser()
        
        # 상품 ID 추출
        product_id = self.extract_product_id(product_url)
        if not product_id:
            self.logger.error(f"상품 ID를 추출할 수 없습니다: {product_url}")
            return []
        
        # 상품 페이지 접속
        if not self.navigate_to_product(product_url):
            self.logger.error(f"상품 페이지 접속에 실패했습니다: {product_url}")
            return []
        
        # 구매평 데이터 수집
        reviews_raw = self.fetch_reviews_via_api(product_id, max_pages)
        
        # 구매평 데이터 가공
        reviews = self.extract_review_data(reviews_raw)
        
        # 원시 데이터 저장 (디버깅용)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        raw_data_file = os.path.join(self.results_dir, f"raw_reviews_{product_id}_{timestamp}.json")
        with open(raw_data_file, 'w', encoding='utf-8') as f:
            json.dump(reviews_raw, f, ensure_ascii=False, indent=2)
        
        self.logger.info(f"원시 리뷰 데이터 저장 완료: {raw_data_file}")
        return reviews
    
    def process_product_list(self, input_file, output_file):
        """
        엑셀 파일에서 상품 URL 목록을 읽어 처리하고 결과 저장
        
        Args:
            input_file (str): 상품 URL 목록이 있는 엑셀/CSV 파일 경로
            output_file (str): 결과를 저장할 파일 경로
        """
        try:
            self.start_browser()
            
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
            
            # URL 컬럼 찾기
            url_col = None
            possible_cols = ['url', 'URL', 'link', 'LINK', '주소', '상품URL', '상품주소']
            
            for col in df.columns:
                if col.lower() in [c.lower() for c in possible_cols]:
                    url_col = col
                    break
            
            if not url_col:
                if len(df.columns) > 0:
                    # 첫 번째 컬럼을 URL 컬럼으로 가정
                    url_col = df.columns[0]
                    self.logger.warning(f"URL 컬럼을 명시적으로 찾을 수 없어 첫 번째 컬럼({url_col})을 사용합니다.")
                else:
                    self.logger.error("처리할 URL 컬럼을 찾을 수 없습니다.")
                    return
            
            # 결과 저장을 위한 리스트
            all_reviews = []
            
            # 각 상품 URL 처리
            for idx, row in df.iterrows():
                product_url = str(row[url_col]).strip()
                if not product_url or product_url == 'nan' or not product_url.startswith('http'):
                    continue
                
                self.logger.info(f"상품 처리 중: {product_url} ({idx+1}/{len(df)})")
                
                # 상품 리뷰 수집
                product_reviews = self.crawl_product_reviews(product_url)
                
                # 상품 URL 정보 추가
                for review in product_reviews:
                    review['상품URL'] = product_url
                
                all_reviews.extend(product_reviews)
                
                # 다음 상품 처리 전 잠시 대기
                time.sleep(3)
            
            # 결과 저장
            if all_reviews:
                # 결과를 데이터프레임으로 변환
                result_df = pd.DataFrame(all_reviews)
                
                # 출력 파일 확장자 확인 및 저장
                out_ext = os.path.splitext(output_file)[1].lower()
                
                if out_ext == '.xlsx' or out_ext == '.xls':
                    result_df.to_excel(output_file, index=False, engine='openpyxl')
                    self.logger.info(f"결과가 엑셀 파일로 저장되었습니다: {output_file}")
                else:
                    # 기본적으로 CSV로 저장
                    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                    self.logger.info(f"결과가 CSV 파일로 저장되었습니다: {output_file}")
            else:
                self.logger.warning("저장할 리뷰 데이터가 없습니다.")
            
        except Exception as e:
            self.logger.error(f"상품 목록 처리 중 오류 발생: {str(e)}")
            
        finally:
            self.close()
    
    def close(self):
        """브라우저 종료"""
        if self.browser:
            self.browser.close()
            self.browser = None
            self.page = None
            self.logger.info("브라우저가 종료되었습니다.")


# 모듈 직접 실행 시
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="네이버 쇼핑 구매평 크롤러")
    parser.add_argument("--input", help="입력 파일 경로(상품 URL 목록 엑셀/CSV)")
    parser.add_argument("--output", help="출력 파일 경로(결과 저장 엑셀/CSV)")
    parser.add_argument("--url", help="단일 상품 URL")
    parser.add_argument("--headless", action="store_true", help="헤드리스 모드로 실행")
    
    args = parser.parse_args()
    
    try:
        crawler = NaverReviewCrawler(headless=args.headless)
        
        if args.input and args.output:
            # 파일에서 상품 목록 처리
            crawler.process_product_list(args.input, args.output)
        elif args.url:
            # 단일 상품 URL 처리
            output_file = args.output or f"results/reviews/review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            reviews = crawler.crawl_product_reviews(args.url)
            
            if reviews:
                # 상품 URL 정보 추가
                for review in reviews:
                    review['상품URL'] = args.url
                
                # 결과를 데이터프레임으로 변환 및 저장
                result_df = pd.DataFrame(reviews)
                
                # 출력 파일 확장자 확인 및 저장
                out_ext = os.path.splitext(output_file)[1].lower()
                
                if out_ext == '.xlsx' or out_ext == '.xls':
                    result_df.to_excel(output_file, index=False, engine='openpyxl')
                else:
                    # 기본적으로 CSV로 저장
                    result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                
                logger = get_logger()
                logger.info(f"결과가 저장되었습니다: {output_file}")
        else:
            print("사용법: python naver_review_crawler.py --input 상품목록.xlsx --output 결과.xlsx")
            print("또는: python naver_review_crawler.py --url 상품URL --output 결과.xlsx")
    
    except Exception as e:
        logger = get_logger()
        logger.error(f"프로그램 실행 중 오류 발생: {str(e)}") 