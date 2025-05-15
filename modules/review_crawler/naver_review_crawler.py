g#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import time
import json
import logging
import argparse
import pandas as pd
import random
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


# 사용자 에이전트 목록
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Whale/3.24.223.21 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.216 Whale/3.23.214.10 Safari/537.36"
]


class NaverReviewCrawler:
    """네이버 쇼핑 구매평 크롤러 클래스"""
    
    def __init__(self, headless=True, debug_mode=False):
        """초기화
        
        Args:
            headless (bool): 헤드리스 모드 사용 여부
            debug_mode (bool): 디버그 모드 사용 여부
        """
        # 로거 설정
        self.logger = get_logger()
        
        # 브라우저 옵션
        self.headless = headless
        self.debug_mode = debug_mode
        
        # 브라우저 인스턴스
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
        # 사용자 에이전트 설정
        self.rotate_user_agent()
        
        # 랜덤 키보드/마우스 이벤트 지연
        self.keyboard_delay = random.uniform(100, 300)
        self.mouse_delay = random.uniform(300, 800)
        
        # 세션 목록
        self.sessions = []
        
        # 프록시 설정
        self.current_proxy = None
        
        # 차단 감지 횟수
        self.block_count = 0
        self.max_block_retries = 5
        
        self.results_dir = "results/reviews"
        self.user_agent = random.choice(USER_AGENTS)
        self.retry_count = 3
        self.max_delay = 5
        self.min_delay = 1
        self.cookies_loaded = False
        self.cookies_path = "modules/review_crawler/cookies.json"
        
        # 결과 저장 디렉토리 생성
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
    
    def random_sleep(self, min_seconds=None, max_seconds=None):
        """랜덤한 시간동안 대기
        
        Args:
            min_seconds (float): 최소 대기 시간(초)
            max_seconds (float): 최대 대기 시간(초)
        """
        min_time = min_seconds if min_seconds is not None else self.min_delay
        max_time = max_seconds if max_seconds is not None else self.max_delay
        
        sleep_time = min_time + random.random() * (max_time - min_time)
        self.logger.info(f"랜덤 대기 중... {sleep_time:.2f}초")
        time.sleep(sleep_time)
    
    def rotate_user_agent(self):
        """사용자 에이전트 변경"""
        self.user_agent = random.choice(USER_AGENTS)
        self.logger.info(f"사용자 에이전트 변경: {self.user_agent}")
        
        if self.page:
            self.page.set_extra_http_headers({
                "User-Agent": self.user_agent
            })
    
    def save_cookies(self):
        """현재 브라우저의 쿠키 저장"""
        if not self.context:
            self.logger.warning("브라우저 컨텍스트가 없어 쿠키를 저장할 수 없습니다.")
            return
        
        try:
            cookies = self.context.cookies()
            os.makedirs(os.path.dirname(self.cookies_path), exist_ok=True)
            
            with open(self.cookies_path, 'w', encoding='utf-8') as f:
                json.dump(cookies, f, ensure_ascii=False)
            
            self.logger.info(f"쿠키 저장 완료: {self.cookies_path}")
        except Exception as e:
            self.logger.error(f"쿠키 저장 중 오류 발생: {str(e)}")
    
    def load_cookies(self):
        """저장된 쿠키 로드"""
        if not os.path.exists(self.cookies_path):
            self.logger.info("저장된 쿠키 파일이 없습니다.")
            return False
        
        if not self.context:
            self.logger.warning("브라우저 컨텍스트가 없어 쿠키를 로드할 수 없습니다.")
            return False
        
        try:
            with open(self.cookies_path, 'r', encoding='utf-8') as f:
                cookies = json.load(f)
            
            self.context.add_cookies(cookies)
            self.cookies_loaded = True
            self.logger.info(f"쿠키 로드 완료: {self.cookies_path}")
            return True
        except Exception as e:
            self.logger.error(f"쿠키 로드 중 오류 발생: {str(e)}")
            return False
    
    def start_browser(self, use_mobile=False):
        """Playwright 브라우저 시작
        
        Args:
            use_mobile (bool): 모바일 에뮬레이션 사용 여부
        """
        try:
            if self.browser is None:
                self.logger.info("브라우저 시작 중...")
                self.logger.info(f"모바일 모드: {'활성화' if use_mobile else '비활성화'}")
                self.playwright = sync_playwright().start()
                
                # 봇 감지 우회를 위한 브라우저 옵션 설정
                browser_args = [
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                ]
                
                # 브라우저 시작 옵션
                browser_options = {
                    "headless": (not self.debug_mode) and self.headless,
                    "slow_mo": random.randint(50, 100) if self.debug_mode else 0,
                    "args": browser_args,
                    "timeout": 60000  # 브라우저 시작 타임아웃을 60초로 설정
                }
                
                # 모바일 디바이스 에뮬레이션 설정
                if use_mobile:
                    self.logger.info("모바일 디바이스 에뮬레이션 활성화")
                    # 다양한 모바일 기기 중 랜덤 선택
                    mobile_devices = [
                        'iPhone 12',
                        'iPhone 13',
                        'Pixel 5',
                        'Galaxy S8',
                        'Galaxy S9+',
                    ]
                    device_name = random.choice(mobile_devices)
                    self.logger.info(f"모바일 기기 에뮬레이션: {device_name}")
                    
                    # 모바일 전용 사용자 에이전트
                    mobile_user_agents = [
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
                        "Mozilla/5.0 (Linux; Android 12; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
                        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/120.0.0.0 Mobile/15E148 Safari/604.1"
                    ]
                    self.user_agent = random.choice(mobile_user_agents)
                    self.logger.info(f"모바일 사용자 에이전트: {self.user_agent}")
                
                # 브라우저 시작
                self.logger.info("Chromium 브라우저 실행 중...")
                self.browser = self.playwright.chromium.launch(**browser_options)
                
                # 브라우저 지문 방지를 위한 컨텍스트 설정
                self.logger.info("브라우저 컨텍스트 생성 중...")
                context_options = {
                    "viewport": {'width': 375, 'height': 667} if use_mobile else {'width': random.randint(1200, 1400), 'height': random.randint(800, 900)},
                    "user_agent": self.user_agent,
                    "locale": 'ko-KR',
                    "timezone_id": 'Asia/Seoul', 
                    "geolocation": {'latitude': 37.566, 'longitude': 126.978},
                    "permissions": ['geolocation'],
                    "color_scheme": 'light',
                }
                
                if use_mobile:
                    context_options["device_scale_factor"] = 2.0
                    context_options["is_mobile"] = True
                    context_options["has_touch"] = True
                
                self.context = self.browser.new_context(**context_options)
                
                # 쿠키 로드 시도
                if not self.load_cookies():
                    self.logger.info("쿠키를 로드할 수 없습니다. 새 세션으로 진행합니다.")
                
                self.logger.info("페이지 생성 중...")
                self.page = self.context.new_page()
                
                self.page.set_default_timeout(60000)  # 60초 타임아웃 설정 (기본 30초에서 늘림)
                
                # 자바스크립트 변수 오버라이드로 봇 감지 회피
                self.logger.info("봇 감지 회피 스크립트 적용 중...")
                self.page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => false,
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [
                            {
                                0: {
                                    type: 'application/x-google-chrome-pdf',
                                    suffixes: 'pdf',
                                    description: 'Portable Document Format',
                                    enabledPlugin: Plugin,
                                },
                                description: 'Portable Document Format',
                                filename: 'internal-pdf-viewer',
                                length: 1,
                                name: 'Chrome PDF Plugin',
                            },
                            {
                                0: {
                                    type: 'application/pdf',
                                    suffixes: 'pdf',
                                    description: '',
                                    enabledPlugin: Plugin,
                                },
                                description: '',
                                filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                                length: 1,
                                name: 'Chrome PDF Viewer',
                            },
                            {
                                0: {
                                    type: 'application/x-nacl',
                                    suffixes: '',
                                    description: 'Native Client Executable',
                                    enabledPlugin: Plugin,
                                },
                                1: {
                                    type: 'application/x-pnacl',
                                    suffixes: '',
                                    description: 'Portable Native Client Executable',
                                    enabledPlugin: Plugin,
                                },
                                description: '',
                                filename: 'internal-nacl-plugin',
                                length: 2,
                                name: 'Native Client',
                            },
                        ],
                    });
                    
                    // 랜덤 스크롤 동작 구현
                    window.originalScrollTo = window.scrollTo;
                    window.scrollTo = function() {
                        window.originalScrollTo.apply(this, arguments);
                        // 랜덤한 작은 움직임 추가
                        setTimeout(function() {
                            window.originalScrollTo(
                                window.scrollX + Math.floor(Math.random() * 3) - 1,
                                window.scrollY + Math.floor(Math.random() * 3) - 1
                            );
                        }, Math.floor(Math.random() * 500) + 200);
                    };
                """)
                
                # 디버깅용 이벤트 리스너 설정
                if self.debug_mode:
                    self.page.on("console", lambda msg: self.logger.debug(f"브라우저 콘솔: {msg.text}"))
                    self.page.on("pageerror", lambda err: self.logger.error(f"페이지 오류: {err}"))
                    self.logger.info("디버그 모드가 활성화되었습니다.")
                
                self.logger.info("브라우저 시작 완료")
        except Exception as e:
            self.logger.error(f"브라우저 시작 중 오류 발생: {str(e)}")
            # 이미 시작된 리소스 정리
            self.close()
            raise e
    
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
        
        # 랜덤 요청 파라미터를 약간씩 변경하여 패턴 감지 회피
        sort_types = ["REVIEW_RANKING", "REVIEW_CREATE_DT_DESC", "REVIEW_SCORE_DESC", "REVIEW_SCORE_ASC"]
        sort_type = sort_types[0]  # 기본은 베스트순이지만 가끔 다른 정렬도 사용
        
        if random.random() < 0.2:  # 20% 확률로 다른 정렬 방식 사용
            sort_type = random.choice(sort_types)
        
        # 페이지 크기도 가끔 변경
        if random.random() < 0.2:
            page_size = random.choice([20, 30, 40])
        
        params = {
            'vendorItemId': product_id,
            'page': page_index,
            'pageSize': page_size,
            'sortType': sort_type,
            '_': int(time.time() * 1000)  # 타임스탬프 추가
        }
        
        query_string = '&'.join([f'{k}={v}' for k, v in params.items()])
        return f"{base_url}?{query_string}"
    
    def navigate_to_product(self, url, max_retries=3, use_mobile=False):
        """상품 페이지로 이동
        
        Args:
            url (str): 상품 URL
            max_retries (int): 최대 재시도 횟수
            use_mobile (bool): 모바일 페이지 여부
            
        Returns:
            bool: 성공 여부
        """
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # 브라우저가 시작되지 않았으면 시작
                if not self.browser or not self.page:
                    self.start_browser(use_mobile)
                
                # URL이 모바일 URL인지 확인하고 필요시 변환
                if use_mobile and "m.smartstore.naver.com" not in url and "smartstore.naver.com" in url:
                    url = url.replace("smartstore.naver.com", "m.smartstore.naver.com")
                    self.logger.info(f"PC URL을 모바일 URL로 변환: {url}")
                
                # 랜덤 레퍼러 설정
                referers = [
                    "https://search.shopping.naver.com/search/all",
                    "https://search.naver.com/search.naver",
                    "https://search.daum.net/search",
                    "https://www.google.com/search"
                ]
                referer = random.choice(referers)
                self.logger.info(f"레퍼러 설정: {referer}")
                
                self.page.set_extra_http_headers({
                    'Referer': referer
                })
                
                # 상품 페이지 접속
                self.logger.info(f"상품 페이지 접속 중: {url}")
                
                # 랜덤 지연 설정 (네트워크 환경과 유사한 지연)
                self.page.route("**/*", lambda route: route.continue_(
                    delay=random.randint(10, 100)
                ))
                
                try:
                    self.logger.info("페이지 로드 시작...")
                    # 타임아웃 60초로 연장
                    response = self.page.goto(
                        url, 
                        wait_until="networkidle",
                        timeout=60000
                    )
                    self.logger.info(f"페이지 로드 완료 - 상태 코드: {response.status if response else 'unknown'}")
                except PlaywrightTimeoutError:
                    self.logger.warning("페이지 로드 타임아웃 발생, 네트워크만 대기")
                    # 타임아웃이 발생하면 networkidle 대신 domcontentloaded만 대기
                    self.page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    self.logger.info("기본 페이지 로드 완료")
                
                # 랜덤 지연
                delay = random.uniform(1, 3)
                self.logger.info(f"랜덤 대기 중... {delay:.2f}초")
                time.sleep(delay)
                
                # 추가 로딩 대기
                try:
                    self.logger.info("추가 로딩 대기...")
                    self.page.wait_for_load_state("networkidle", timeout=30000)
                    self.logger.info("모든 네트워크 요청 완료")
                except PlaywrightTimeoutError:
                    self.logger.warning("네트워크 요청 완료 대기 타임아웃, 계속 진행")
                
                # 접근 차단 확인
                if self.is_blocked():
                    retry_count += 1
                    self.logger.warning(f"재시도 {retry_count}/{max_retries}")
                    
                    # 차단 우회 처리
                    if not self.handle_blocking():
                        continue
                else:
                    # 페이지 로드 완료되면 HTML 소스 디버깅용 저장 (디버그 모드인 경우)
                    if self.debug_mode:
                        html_content = self.page.content()
                        debug_dir = "debug"
                        if not os.path.exists(debug_dir):
                            os.makedirs(debug_dir)
                        with open(f"{debug_dir}/product_page.html", "w", encoding="utf-8") as f:
                            f.write(html_content)
                            
                        # 스크린샷도 저장
                        self.page.screenshot(path=f"{debug_dir}/product_page.png")
                    
                    return True
            
            except Exception as e:
                self.logger.error(f"페이지 접속 중 오류 발생: {str(e)}")
                retry_count += 1
                
                if retry_count < max_retries:
                    self.logger.info(f"재시도 {retry_count}/{max_retries} 시작...")
                    
                    # 무작위 대기
                    wait_time = random.uniform(3, 10)
                    self.logger.info(f"랜덤 대기 중... {wait_time:.2f}초")
                    time.sleep(wait_time)
                    
                    # 재시도할 때마다 30% 확률로 사용자 에이전트 변경
                    if random.random() < 0.3:
                        self.rotate_user_agent()
                
        self.logger.error("페이지 접속 실패")
        return False

    def handle_blocking(self):
        """봇 차단 감지 및 우회 처리

        Returns:
            bool: 성공 여부
        """
        try:
            self.logger.info("접근 차단 처리를 위해 브라우저 재시작 시도...")
            
            # 먼저 브라우저와 관련된 모든 리소스 정리
            if self.page:
                try:
                    self.page.close()
                except Exception:
                    pass
                self.page = None
                
            if self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
                self.context = None
                
            if self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
                self.browser = None
                
            if self.playwright:
                try:
                    self.playwright.stop()
                except Exception:
                    pass
                self.playwright = None
            
            # 랜덤 대기 시간
            wait_time = random.uniform(10, 30)
            self.logger.info(f"랜덤 대기 중... {wait_time:.2f}초")
            time.sleep(wait_time)
            
            # 에이전트 랜덤 교체
            self.rotate_user_agent()
            
            # 브라우저 재시작
            self.start_browser()
            
            return True
            
        except Exception as e:
            self.logger.error(f"차단 처리 중 오류: {str(e)}")
            return False
            
    def close(self):
        """리소스 정리 및 브라우저 종료"""
        try:
            # 쿠키 저장 시도
            if self.page and self.context:
                try:
                    self.save_cookies()
                except Exception as e:
                    self.logger.warning(f"쿠키 저장 실패: {str(e)}")
            
            # 페이지 닫기
            if hasattr(self, 'page') and self.page:
                try:
                    self.page.close()
                except Exception:
                    pass
                self.page = None
            
            # 컨텍스트 닫기
            if hasattr(self, 'context') and self.context:
                try:
                    self.context.close()
                except Exception:
                    pass
                self.context = None
            
            # 브라우저 닫기
            if hasattr(self, 'browser') and self.browser:
                try:
                    self.browser.close()
                except Exception:
                    pass
                self.browser = None
                
            # playwright 종료
            if hasattr(self, 'playwright') and self.playwright:
                try:
                    self.playwright.stop()
                except Exception:
                    pass
                self.playwright = None
                
        except Exception as e:
            self.logger.error(f"브라우저 종료 중 오류 발생: {str(e)}")
            
    def is_blocked(self):
        """차단 페이지 확인
        
        Returns:
            bool: 차단 페이지인지 여부
        """
        try:
            # 차단 관련 텍스트 또는 요소 확인
            content = self.page.content().lower()
            block_indicators = [
                "현재 서비스 접속이 불가합니다",
                "access denied",
                "차단되었습니다",
                "robot",
                "captcha",
                "자동화된 접근",
                "비정상적인 접속"
            ]
            
            for indicator in block_indicators:
                if indicator in content:
                    self.logger.warning(f"접근 차단 감지: '{indicator}'")
                    
                    # 디버그 모드에서 스크린샷 저장
                    if self.debug_mode:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        screenshot_path = os.path.join(self.results_dir, f"blocked_{timestamp}.png")
                        self.page.screenshot(path=screenshot_path)
                        self.logger.info(f"차단 화면 스크린샷 저장: {screenshot_path}")
                    
                    return True
            
            # 추가 검사: URL이 차단 페이지로 리디렉션 되었는지 확인
            current_url = self.page.url
            if "verify" in current_url or "captcha" in current_url or "block" in current_url:
                self.logger.warning(f"차단 URL 감지: {current_url}")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"차단 확인 중 오류: {str(e)}")
            return False
    
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
    
    def navigate_to_next_page(self, use_mobile=False):
        """다음 페이지로 이동
        
        Args:
            use_mobile (bool): 모바일 페이지 여부
        
        Returns:
            bool: 다음 페이지 존재 여부
        """
        try:
            # 현재 페이지 번호 찾기
            if use_mobile:
                # 모바일 페이지에서 현재 페이지 찾기
                current_page_selectors = [
                    'a.active', 
                    '[class*="PageButton_active"]',
                    'a[aria-current="page"]',
                    'span.current',
                    '.pagination-current'
                ]
            else:
                # PC 페이지에서 현재 페이지 찾기
                current_page_selectors = [
                    'a.active', 
                    '[class*="active"]',
                    'a[aria-current="page"]',
                    '[class*="current"]',
                    'a.pagination_active__1TRmL'
                ]
            
            current_page = 1
            for selector in current_page_selectors:
                element = self.page.query_selector(selector)
                if element:
                    text = element.text_content().strip()
                    if text.isdigit():
                        current_page = int(text)
                        self.logger.info(f"현재 페이지: {current_page}")
                        break
            
            # 다음 페이지 버튼 선택자
            if use_mobile:
                # 모바일 페이지에서 다음 버튼 선택자
                next_btn_selectors = [
                    'a.next',
                    'a[aria-label="다음"]',
                    '[class*="next"]',
                    'a:has-text("다음")',
                    'button:has-text("다음")',
                    'button[class*="next"]'
                ]
            else:
                # PC 페이지에서 다음 버튼 선택자
                next_btn_selectors = [
                    'a.pagination_next__3jQFJ',
                    'a.next',
                    'a[aria-label="다음"]',
                    '[class*="next"]',
                    'a:has-text("다음")',
                    'a[title="다음"]'
                ]
            
            # 다음 버튼 시도
            for selector in next_btn_selectors:
                next_btn = self.page.query_selector(selector)
                if next_btn:
                    # 비활성화 여부 확인
                    disabled = 'disabled' in (next_btn.get_attribute('class') or '') or next_btn.get_attribute('disabled') == 'true'
                    if not disabled:
                        self.logger.info(f"다음 페이지 버튼 클릭: {selector}")
                        
                        # 자연스러운 클릭 동작을 위해 먼저 마우스 이동
                        try:
                            bound = next_btn.bounding_box()
                            if bound:
                                # 버튼 위로 마우스 이동
                                self.page.mouse.move(
                                    x=bound['x'] + random.randint(5, int(bound['width'] - 5)),
                                    y=bound['y'] + random.randint(5, int(bound['height'] - 5)),
                                    steps=random.randint(3, 5)
                                )
                                self.random_sleep(0.2, 0.5)
                                
                                # 클릭
                                self.page.mouse.click(
                                    x=bound['x'] + random.randint(5, int(bound['width'] - 5)),
                                    y=bound['y'] + random.randint(5, int(bound['height'] - 5))
                                )
                            else:
                                next_btn.click()
                        except Exception:
                            # 일반 클릭으로 대체
                            next_btn.click()
                        
                        self.page.wait_for_timeout(2000)
                        self.page.wait_for_load_state("networkidle", timeout=10000)
                        return True
            
            # 다음 페이지 번호 직접 클릭 시도
            next_page = current_page + 1
            if use_mobile:
                page_btn_selector = f'a:has-text("{next_page}"), button:has-text("{next_page}")'
            else:
                page_btn_selector = f'a:has-text("{next_page}")'
                
            page_btn = self.page.query_selector(page_btn_selector)
            
            if page_btn:
                self.logger.info(f"페이지 {next_page} 버튼 클릭")
                
                # 자연스러운 클릭 동작
                try:
                    bound = page_btn.bounding_box()
                    if bound:
                        # 버튼 위로 마우스 이동
                        self.page.mouse.move(
                            x=bound['x'] + random.randint(3, int(bound['width'] - 3)),
                            y=bound['y'] + random.randint(3, int(bound['height'] - 3)),
                            steps=random.randint(2, 4)
                        )
                        self.random_sleep(0.2, 0.5)
                        
                        # 클릭
                        self.page.mouse.click(
                            x=bound['x'] + random.randint(3, int(bound['width'] - 3)),
                            y=bound['y'] + random.randint(3, int(bound['height'] - 3))
                        )
                    else:
                        page_btn.click()
                except Exception:
                    # 일반 클릭으로 대체
                    page_btn.click()
                
                self.page.wait_for_timeout(2000)
                self.page.wait_for_load_state("networkidle", timeout=10000)
                return True
            
            # 특별한 페이지네이션 처리 (모바일 페이지에서 더 보기 버튼이 있는 경우)
            if use_mobile:
                more_btns = [
                    'button:has-text("더보기")',
                    'a:has-text("더보기")',
                    'button[class*="more"]',
                    'a[class*="more"]',
                    '.more_button'
                ]
                
                for selector in more_btns:
                    more_btn = self.page.query_selector(selector)
                    if more_btn:
                        self.logger.info(f"더보기 버튼 클릭: {selector}")
                        more_btn.click()
                        self.page.wait_for_timeout(2000)
                        self.page.wait_for_load_state("networkidle", timeout=10000)
                        return True
            
            self.logger.info("다음 페이지가 없습니다.")
            return False
            
        except Exception as e:
            self.logger.error(f"다음 페이지 이동 중 오류: {str(e)}")
            return False

    def crawl_product_reviews(self, product_url, max_pages=10, use_proxy=False, proxy_url=None, use_mobile=False):
        """상품 구매평 크롤링
        
        Args:
            product_url (str): 상품 URL
            max_pages (int): 최대 수집할 페이지 수
            use_proxy (bool): 프록시 사용 여부
            proxy_url (str): 프록시 URL (예: "http://user:pass@ip:port")
            use_mobile (bool): 모바일 페이지 사용 여부
            
        Returns:
            list: 수집된 구매평 목록
        """
        # URL 형식 확인 및 변환 (PC -> 모바일 또는 모바일 -> PC)
        if use_mobile and "m.smartstore.naver.com" not in product_url:
            # PC URL을 모바일 URL로 변환
            if "smartstore.naver.com" in product_url:
                product_url = product_url.replace("smartstore.naver.com", "m.smartstore.naver.com")
                self.logger.info(f"PC URL을 모바일 URL로 변환: {product_url}")
        
        # 브라우저 시작 전 프록시 설정
        if use_proxy and proxy_url:
            self.logger.info(f"프록시 사용: {proxy_url}")
            # 기존 브라우저 인스턴스가 있으면 닫기
            if self.browser:
                self.browser.close()
                self.browser = None
                self.context = None
                self.page = None
        
        # 브라우저 시작
        self.start_browser(use_mobile)
        
        # 결과 저장 리스트
        all_reviews = []
        product_id = None
        
        try:
            # 상품 ID 추출
            product_id = self.extract_product_id(product_url)
            if not product_id:
                self.logger.error("상품 ID를 추출할 수 없습니다.")
                return []
                
            self.logger.info(f"상품 ID: {product_id}")
            
            # 크롤링 전략 결정 (API와 웹 스크레이핑을 혼합)
            # 첫 번째 시도는 API 방식
            try:
                self.logger.info("API 방식으로 리뷰 수집 시도...")
                
                # 리뷰 섹션으로 이동 (API 호출 준비)
                if not self.navigate_to_review_section(product_url, use_mobile):
                    self.logger.warning("리뷰 섹션으로 이동 실패, 대체 방법 시도...")
                else:
                    # API로 리뷰 데이터 수집 시도
                    api_reviews = self.fetch_reviews_via_api(product_id, max_pages)
                    
                    if api_reviews and len(api_reviews) > 0:
                        self.logger.info(f"API 방식으로 {len(api_reviews)}개의 리뷰를 수집했습니다.")
                        # API로 수집한 리뷰 데이터 가공
                        processed_reviews = self.extract_review_data(api_reviews)
                        
                        if processed_reviews and len(processed_reviews) > 0:
                            all_reviews = processed_reviews
                            self.logger.info("API 방식 리뷰 수집 성공")
                        else:
                            self.logger.warning("API 수집 데이터 처리 실패")
            except Exception as e:
                self.logger.error(f"API 리뷰 수집 중 오류: {str(e)}")
            
            # API 방식이 실패하거나 리뷰가 없으면 웹 스크레이핑 방식 시도
            if not all_reviews:
                self.logger.info("웹 스크레이핑 방식으로 리뷰 수집 시도...")
                
                # 리뷰 섹션 다시 이동 (신규 세션)
                if not self.navigate_to_review_section(product_url, use_mobile):
                    self.logger.error("리뷰 섹션으로 이동 실패, 수집 중단")
                    return []
                
                # 페이지 처리
                page_num = 1
                
                # 각 페이지 처리
                while page_num <= max_pages:
                    self.logger.info(f"=== 페이지 {page_num} 처리 중 ===")
                    
                    # 봇 차단 확인
                    if self.is_blocked():
                        self.logger.warning(f"페이지 {page_num} 처리 중 봇 차단 감지")
                        if not self.handle_blocking():
                            self.logger.error("봇 차단 해결 실패, 수집 중단")
                            break
                        
                        # 페이지 재접속
                        if not self.navigate_to_review_section(product_url, use_mobile):
                            self.logger.error("재접속 실패, 수집 중단")
                            break
                        
                        # 이전 페이지로 이동
                        for _ in range(1, page_num):
                            if not self.navigate_to_next_page(use_mobile):
                                self.logger.error("이전 페이지로 복귀 실패")
                                break
                        
                        continue
                    
                    # 리뷰 항목 추출
                    review_items = self.extract_review_items(use_mobile)
                    
                    if not review_items or len(review_items) == 0:
                        self.logger.warning(f"페이지 {page_num}에서 리뷰 항목을 찾을 수 없습니다.")
                        break
                    
                    self.logger.info(f"페이지 {page_num}에서 {len(review_items)}개의 리뷰를 찾았습니다.")
                    
                    # 각 리뷰 처리 (자연스러운 지연 추가)
                    for i, item in enumerate(review_items, 1):
                        try:
                            # 리뷰 정보 추출
                            review_data = self._extract_review_from_element(item, len(all_reviews) + 1, use_mobile)
                            if review_data:
                                all_reviews.append(review_data)
                                
                                # 요소 크롤링 간 무작위 지연 (자연스러운 크롤링)
                                if i < len(review_items) and random.random() < 0.3:  # 30% 확률로 지연
                                    delay = 0.2 + random.random() * 0.8  # 0.2~1초
                                    time.sleep(delay)
                                    
                        except Exception as e:
                            self.logger.error(f"리뷰 항목 {i} 처리 중 오류: {str(e)}")
                    
                    self.logger.info(f"페이지 {page_num}: {len(review_items)}개 리뷰 처리 완료 (누적: {len(all_reviews)}개)")
                    
                    # 페이지 이동 후 추가 대기 시간
                    self.random_sleep(1, 3)
                    
                    # 다음 페이지로 이동
                    if page_num < max_pages:
                        if not self.navigate_to_next_page(use_mobile):
                            self.logger.info("마지막 페이지에 도달했습니다.")
                            break
                        page_num += 1
                        
                        # 페이지 이동 후 자연스러운 대기
                        self.random_sleep(2, 5)
                    else:
                        self.logger.info(f"최대 페이지 수({max_pages})에 도달했습니다.")
                        break
            
            self.logger.info(f"총 {len(all_reviews)}개 리뷰 수집 완료")
            
            # 상품 정보 추가
            for review in all_reviews:
                if not review.get('상품ID'):
                    review['상품ID'] = product_id
            
        except Exception as e:
            self.logger.error(f"리뷰 수집 중 오류 발생: {str(e)}")
        
        # 원시 데이터 저장 (디버깅용)
        if all_reviews:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            product_id = product_id or "unknown"
            raw_data_file = os.path.join(self.results_dir, f"raw_reviews_{product_id}_{timestamp}.json")
            with open(raw_data_file, 'w', encoding='utf-8') as f:
                json.dump(all_reviews, f, ensure_ascii=False, indent=2)
            self.logger.info(f"원시 리뷰 데이터 저장 완료: {raw_data_file}")
        
        # 세션 종료 전 쿠키 저장
        self.save_cookies()
        
        return all_reviews

    def navigate_to_review_section(self, url, use_mobile=False):
        """리뷰 섹션으로 이동 및 페이지 구조 분석
        
        Args:
            url (str): 상품 URL
            use_mobile (bool): 모바일 페이지 사용 여부
            
        Returns:
            bool: 성공 여부
        """
        try:
            self.logger.info(f"리뷰 섹션으로 이동 시도 (모바일 모드: {use_mobile})")
            
            # 상품 페이지 이동
            if not self.navigate_to_product(url, use_mobile=use_mobile):
                self.logger.error("상품 페이지 이동 실패")
                return False
                
            # 페이지가 완전히 로드될 때까지 대기
            self.logger.info("리뷰 섹션으로 이동 시도 중...")
            
            # 자연스러운 페이지 로딩 대기
            self.random_sleep(2, 4)
            self.page.wait_for_load_state("networkidle", timeout=30000)
            
            # 자연스러운 스크롤 동작 (한 번에 내리지 않고 여러 단계로 나누어 스크롤)
            self.logger.info("페이지 스크롤 중...")
            
            # 랜덤 간격의 다중 스크롤 동작 시뮬레이션
            scroll_steps = random.randint(4, 7)  # 스크롤 단계 수를 랜덤하게 선택
            total_height = 0
            
            for i in range(scroll_steps):
                # 랜덤한 스크롤 거리
                scroll_y = random.randint(300, 600)
                total_height += scroll_y
                
                # 스크롤 실행
                self.page.evaluate(f"window.scrollTo(0, {total_height})")
                
                # 손가락으로 스크롤하는 느낌을 주는 불규칙한 대기
                delay = 0.5 + random.random() * 1.5
                time.sleep(delay)
                
                # 가끔 살짝 위로 스크롤 (사람이 읽다가 다시 올리는 행동)
                if random.random() < 0.3 and i > 1:
                    back_scroll = random.randint(50, 150)
                    self.page.evaluate(f"window.scrollTo(0, {total_height - back_scroll})")
                    total_height -= back_scroll
                    time.sleep(0.5 + random.random())
            
            # 모바일/PC 페이지에 따라 다른 선택자 사용
            if use_mobile:
                # 모바일 페이지 리뷰 탭 선택자
                review_selectors = [
                    'a.review_tab',
                    'a[href="#review"]',
                    '#review',
                    'a:has-text("구매평")',
                    'a:has-text("리뷰")',
                    'div[class*="review-tab"]',
                    'div[role="tab"]:has-text("리뷰")',
                    'div[role="tab"]:has-text("구매평")'
                ]
            else:
                # PC 페이지 리뷰 탭 선택자
                review_selectors = [
                    'a[href="#REVIEW"]',
                    '#REVIEW',
                    'a:has-text("상품평")',
                    'a:has-text("구매평")',
                    'a:has-text("리뷰")',
                    '[id*="review"]',
                    '[class*="review-"]',
                    'a.detail_tab',
                    'li.reviewPanel',
                    'div.reviewInfo'
                ]
            
            # 리뷰 탭 찾기 및 클릭 시도
            review_tab_found = False
            for selector in review_selectors:
                try:
                    review_tab = self.page.query_selector(selector)
                    if review_tab:
                        self.logger.info(f"리뷰 탭 발견: {selector}")
                        
                        # 클릭하기 전 자연스럽게 마우스 이동
                        try:
                            bound = review_tab.bounding_box()
                            if bound:
                                # 탭 위로 천천히 마우스 이동 후 클릭
                                self.page.mouse.move(
                                    x=bound['x'] + random.randint(5, int(bound['width'] - 5)),
                                    y=bound['y'] + random.randint(5, int(bound['height'] - 5)),
                                    steps=random.randint(5, 10)  # 천천히 움직이도록 steps 추가
                                )
                                self.random_sleep(0.3, 0.8)  # 마우스 올린 후 살짝 대기
                                
                                # 사람이 클릭하는 것 처럼 랜덤한 지점 클릭
                                self.page.mouse.click(
                                    x=bound['x'] + random.randint(5, int(bound['width'] - 5)),
                                    y=bound['y'] + random.randint(5, int(bound['height'] - 5))
                                )
                                self.logger.info("리뷰 탭 클릭 성공")
                                
                                # 클릭 후 자연스러운 대기
                                self.random_sleep(1.5, 3.0)
                                review_tab_found = True
                                break
                            else:
                                # 바운딩 박스가 없으면 직접 클릭
                                review_tab.click()
                                self.logger.info("리뷰 탭 일반 클릭 성공")
                                self.random_sleep(1.5, 3.0)
                                review_tab_found = True
                                break
                        except Exception as e:
                            self.logger.warning(f"마우스 이동 및 클릭 실패: {str(e)}")
                            # 일반 클릭 시도
                            review_tab.click()
                            self.logger.info("리뷰 탭 대체 클릭 성공")
                            self.random_sleep(1.5, 3.0)
                            review_tab_found = True
                            break
                except Exception as e:
                    self.logger.warning(f"선택자 '{selector}' 검색 중 오류: {str(e)}")
            
            if not review_tab_found:
                self.logger.warning("리뷰 탭을 찾을 수 없습니다. 페이지를 더 스크롤합니다.")
                
                # 모바일 페이지는 더 길게 스크롤 (일반적으로 모바일 페이지가 더 길다)
                total_scroll = 0
                scroll_attempts = 5 if use_mobile else 3
                
                for _ in range(scroll_attempts):
                    scroll_amount = random.randint(400, 700)
                    total_scroll += scroll_amount
                    self.page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {0.4 + random.random() * 0.4})")
                    self.random_sleep(1.0, 2.0)
                
                # 다시 리뷰 탭 찾기 시도
                for selector in review_selectors:
                    try:
                        review_tab = self.page.query_selector(selector)
                        if review_tab:
                            self.logger.info(f"추가 스크롤 후 리뷰 탭 발견: {selector}")
                            review_tab.click()
                            self.logger.info("리뷰 탭 클릭 성공")
                            self.random_sleep(1.5, 3.0)
                            review_tab_found = True
                            break
                    except Exception:
                        continue
                
                # 모바일 페이지에서는 특정 위치로 스크롤 시도
                if use_mobile and not review_tab_found:
                    self.logger.info("모바일 페이지에서 리뷰 영역으로 직접 스크롤 시도")
                    
                    # 일반적으로 페이지의 60-70% 정도 위치에 리뷰 섹션이 있음
                    height = self.page.evaluate("() => document.body.scrollHeight")
                    scroll_to = int(height * 0.65)
                    self.page.evaluate(f"window.scrollTo(0, {scroll_to})")
                    self.random_sleep(2.0, 3.0)
            
            # 리뷰 영역으로 스크롤
            if review_tab_found:
                # 리뷰 영역이 로드되도록 추가 대기
                self.random_sleep(2.0, 4.0)
                
                # 리뷰 영역 스크롤
                if use_mobile:
                    review_area_selectors = [
                        '#review', 
                        '.review-list', 
                        '[class*="review-section"]',
                        '[class*="ReviewList"]'
                    ]
                else:
                    review_area_selectors = [
                        '#REVIEW', 
                        '.review_section', 
                        '[class*="review"]',
                        '[id*="review"]'
                    ]
                
                for selector in review_area_selectors:
                    try:
                        review_area = self.page.query_selector(selector)
                        if review_area:
                            self.logger.info(f"리뷰 영역 발견: {selector}")
                            bound = review_area.bounding_box()
                            if bound:
                                # 리뷰 영역의 시작 부분으로 스크롤
                                self.page.evaluate(f"window.scrollTo(0, {bound['y'] - 100})")
                                self.random_sleep(1.0, 2.0)
                                break
                    except Exception:
                        continue
            
            # 디버그 모드에서 현재 페이지 스크린샷 저장
            if self.debug_mode:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = os.path.join(self.results_dir, f"review_section_{timestamp}.png")
                self.page.screenshot(path=screenshot_path)
                self.logger.info(f"스크린샷 저장: {screenshot_path}")
            
            # 봇 차단 확인
            if self.is_blocked():
                self.logger.warning("리뷰 섹션 이동 중 봇 차단 감지")
                if not self.handle_blocking():
                    return False
                
                # 세션 복구 시도 (다시 페이지 로드)
                return self.navigate_to_review_section(url, use_mobile)
            
            return True
            
        except Exception as e:
            self.logger.error(f"리뷰 섹션 이동 중 오류: {str(e)}")
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
        error_count = 0
        max_errors = 3
        
        self.logger.info(f"상품 ID {product_id}의 리뷰 수집 시작")
        
        # 헤더에 Referer 추가
        referer_url = f"https://smartstore.naver.com/main/products/{product_id}"
        
        while has_more and page_index <= max_pages and error_count < max_errors:
            try:
                # API 요청 간 무작위 지연
                self.random_sleep(1.5, 4)
                
                # 에이전트 랜덤 변경 (30% 확률)
                if random.random() < 0.3:
                    self.rotate_user_agent()
                
                # API URL 생성
                api_url = self.get_review_api_url(product_id, page_index)
                self.logger.info(f"리뷰 API 호출: {api_url} (페이지 {page_index})")
                
                # 랜덤 헤더 생성
                headers = {
                    "accept": "application/json, text/plain, */*",
                    "accept-language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
                    "cache-control": "no-cache" if random.random() < 0.3 else "max-age=0",
                    "pragma": "no-cache" if random.random() < 0.3 else "",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": self.user_agent,
                    "referer": referer_url
                }
                
                # 일부 헤더는 랜덤하게 포함/제외
                if random.random() < 0.7:
                    headers["sec-ch-ua"] = '"Not A;Brand";v="99", "Chromium";v="102", "Google Chrome";v="102"'
                if random.random() < 0.7:
                    headers["sec-ch-ua-mobile"] = "?0"
                if random.random() < 0.7:
                    headers["sec-ch-ua-platform"] = random.choice(['"Windows"', '"macOS"', '"Linux"'])
                
                # 헤더 문자열로 변환
                headers_str = ', '.join([f'"{k}": "{v}"' for k, v in headers.items() if v])
                
                # API 호출 코드 동적 생성
                fetch_script = f"""
                    async () => {{
                        try {{
                            const response = await fetch("{api_url}", {{
                                "headers": {{{headers_str}}},
                                "method": "GET",
                                "credentials": "include",
                                "referrerPolicy": "strict-origin-when-cross-origin",
                                "mode": "cors"
                            }});
                            
                            if (!response.ok) {{
                                return {{ error: response.status, message: response.statusText }};
                            }}
                            
                            return await response.json();
                        }} catch (error) {{
                            return {{ error: 'fetch_error', message: error.toString() }};
                        }}
                    }}
                """
                
                # API 호출 실행
                response = self.page.evaluate(fetch_script)
                
                # 오류 확인
                if isinstance(response, dict) and 'error' in response:
                    error_count += 1
                    self.logger.error(f"API 응답 오류: {response.get('error')} - {response.get('message', '')}")
                    
                    # 오류 처리 (봇 감지 또는 차단)
                    if response.get('error') in [403, 429, 'fetch_error']:
                        self.logger.warning("API 접근 제한 감지. 지연 후 재시도...")
                        self.random_sleep(15, 40)  # 긴 대기 후 재시도
                        
                        # 세션 재설정 시도
                        if error_count >= 2:
                            self.logger.info("세션 재설정 시도...")
                            self.handle_blocking()
                            continue
                    continue
                
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
                            # 다음 페이지 요청 전 무작위 대기
                            delay_time = 1.5 + random.random() * 3.5  # 1.5~5초 사이 무작위 대기
                            self.logger.info(f"다음 페이지 요청 전 {delay_time:.2f}초 대기")
                            time.sleep(delay_time)
                else:
                    self.logger.warning(f"리뷰 데이터를 찾을 수 없습니다 (페이지 {page_index})")
                    has_more = False
                
                # 다음 페이지로 이동
                page_index += 1
                
                # 중간에 가끔 더 긴 대기 시간 추가 (봇 탐지 회피)
                if random.random() < 0.2:  # 20% 확률로 긴 대기
                    long_delay = 5 + random.random() * 10  # 5~15초
                    self.logger.info(f"랜덤 추가 대기: {long_delay:.2f}초")
                    time.sleep(long_delay)
                
            except Exception as e:
                self.logger.error(f"리뷰 데이터 수집 중 오류 발생: {str(e)}")
                error_count += 1
                
                if error_count >= max_errors:
                    self.logger.warning(f"최대 오류 횟수({max_errors})에 도달하여 수집 중단")
                    break
                
                # 오류 발생 시 더 긴 대기
                self.random_sleep(5, 15)
        
        self.logger.info(f"총 {len(reviews)}개의 리뷰를 수집했습니다")
        return reviews

    def extract_review_items(self, use_mobile=False):
        """페이지에서 리뷰 항목 추출
        
        Args:
            use_mobile (bool): 모바일 페이지 여부
            
        Returns:
            list: 리뷰 요소 목록
        """
        try:
            # 리뷰 항목 선택자 목록 (모바일과 PC 버전 모두 포함)
            if use_mobile:
                # 모바일 페이지 선택자
                selectors = [
                    '.reviewItems_review_item__Jxh2p',
                    '.reviewItems_review__LcgOZ',
                    'li.review_list_item',
                    'div[class*="ReviewItem_"]',
                    'div[class*="review-list-item"]'
                ]
            else:
                # PC 페이지 선택자
                selectors = [
                    'div.reviewItems_review_item__Jxh2p',
                    'div.reviewItems_review__LcgOZ',
                    'div[class*="review-item"]',
                    'div[class*="ReviewItem"]',
                    'li.pReviewItem'
                ]
            
            # 각 선택자로 시도
            for selector in selectors:
                self.logger.info(f"리뷰 항목 선택자 시도: {selector}")
                items = self.page.query_selector_all(selector)
                if items and len(items) > 0:
                    self.logger.info(f"선택자 '{selector}'로 {len(items)}개 리뷰 항목 찾음")
                    return items
            
            # 찾지 못한 경우 더 일반적인 선택자로 시도
            general_selectors = [
                'div[class*="review"]',
                'li[class*="review"]',
                'div.review',
                'li.review'
            ]
            
            for selector in general_selectors:
                items = self.page.query_selector_all(selector)
                if items and len(items) > 0:
                    self.logger.info(f"일반 선택자 '{selector}'로 {len(items)}개 리뷰 항목 찾음")
                    return items
            
            self.logger.warning("리뷰 항목을 찾을 수 없습니다.")
            
            # 디버그 모드에서 현재 페이지의 HTML 구조 저장
            if self.debug_mode:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                debug_dir = "debug"
                if not os.path.exists(debug_dir):
                    os.makedirs(debug_dir)
                
                html_content = self.page.content()
                with open(f"{debug_dir}/review_page_{timestamp}.html", "w", encoding="utf-8") as f:
                    f.write(html_content)
                
                self.page.screenshot(path=f"{debug_dir}/review_page_{timestamp}.png")
                self.logger.info(f"디버그 정보 저장: {debug_dir}/review_page_{timestamp}.html")
            
            return []
            
        except Exception as e:
            self.logger.error(f"리뷰 항목 추출 중 오류: {str(e)}")
            return []
    
    def _extract_review_from_element(self, review_element, item_no, use_mobile=False):
        """리뷰 요소에서 데이터 추출
        
        Args:
            review_element: 리뷰 요소
            item_no (int): 리뷰 항목 번호
            use_mobile (bool): 모바일 페이지 여부
            
        Returns:
            dict: 추출된 리뷰 데이터
        """
        try:
            review_data = {
                "순번": item_no,
                "리뷰ID": "",
                "작성자ID": "",
                "작성자명": "",
                "별점": 0,
                "구매확정": "N",
                "옵션정보": "",
                "작성일자": "",
                "리뷰내용": "",
                "이미지URL": ""
            }
            
            # 모바일과 PC 페이지의 선택자 구조 차이 처리
            if use_mobile:
                # 모바일 페이지 리뷰 데이터 추출
                
                # 작성자명
                author_selectors = [
                    'span[class*="user_name"]',
                    '.reviewItems_name__17YdZ',
                    'span[class*="Name"]',
                    'span.user',
                    'div[class*="user"]'
                ]
                
                for selector in author_selectors:
                    author_el = review_element.query_selector(selector)
                    if author_el:
                        review_data["작성자명"] = author_el.text_content().strip()
                        break
                
                # 별점
                rating_selectors = [
                    'span[class*="rating"]',
                    'span.star em',
                    'div[class*="Rating"]',
                    'div[class*="score"]'
                ]
                
                for selector in rating_selectors:
                    rating_el = review_element.query_selector(selector)
                    if rating_el:
                        rating_text = rating_el.text_content().strip()
                        if rating_text:
                            try:
                                # 별점 추출 (예: "5", "별점 5점", "5.0" 등)
                                rating_value = re.search(r'(\d+(\.\d+)?)', rating_text)
                                if rating_value:
                                    review_data["별점"] = float(rating_value.group(1))
                            except Exception:
                                pass
                        break
                
                # 구매 확정 여부
                purchase_selectors = [
                    'span[class*="purchase"]',
                    'span.badge',
                    'div[class*="purchased"]'
                ]
                
                for selector in purchase_selectors:
                    purchase_el = review_element.query_selector(selector)
                    if purchase_el:
                        purchase_text = purchase_el.text_content().strip()
                        if "구매" in purchase_text:
                            review_data["구매확정"] = "Y"
                        break
                
                # 옵션 정보
                option_selectors = [
                    'div[class*="option"]',
                    'span[class*="option"]',
                    'p[class*="option"]'
                ]
                
                for selector in option_selectors:
                    option_el = review_element.query_selector(selector)
                    if option_el:
                        option_text = option_el.text_content().strip()
                        if option_text and ":" in option_text:
                            review_data["옵션정보"] = option_text
                        break
                
                # 작성일자
                date_selectors = [
                    'span[class*="date"]',
                    'span.date',
                    'time',
                    'div[class*="date"]'
                ]
                
                for selector in date_selectors:
                    date_el = review_element.query_selector(selector)
                    if date_el:
                        date_text = date_el.text_content().strip()
                        if date_text:
                            review_data["작성일자"] = date_text
                        break
                
                # 리뷰 내용
                content_selectors = [
                    'p[class*="content"]',
                    'div[class*="content"]',
                    'span[class*="text"]',
                    'div[class*="text"]'
                ]
                
                for selector in content_selectors:
                    content_el = review_element.query_selector(selector)
                    if content_el:
                        content_text = content_el.text_content().strip()
                        if content_text:
                            review_data["리뷰내용"] = content_text
                        break
                
                # 이미지 URL (있으면)
                image_selectors = [
                    'img[class*="thumbnail"]',
                    'img[class*="review"]',
                    'a[class*="photo"]',
                    'div[class*="thumbnail"] img'
                ]
                
                image_urls = []
                for selector in image_selectors:
                    image_elements = review_element.query_selector_all(selector)
                    for image_el in image_elements:
                        src = image_el.get_attribute('src')
                        if src:
                            image_urls.append(src)
                
                if image_urls:
                    review_data["이미지URL"] = ';'.join(image_urls)
                
            else:
                # PC 페이지 리뷰 데이터 추출
                
                # 작성자명
                author_selectors = [
                    'strong[class*="user_name"]',
                    '.reviewItems_name__17YdZ',
                    'strong[class*="Name"]',
                    'span.user_name'
                ]
                
                for selector in author_selectors:
                    author_el = review_element.query_selector(selector)
                    if author_el:
                        review_data["작성자명"] = author_el.text_content().strip()
                        break
                
                # 별점
                rating_selectors = [
                    'div[class*="rating"] em',
                    'div.review_score span',
                    'div[class*="Rating"] em',
                    'span.rating'
                ]
                
                for selector in rating_selectors:
                    rating_el = review_element.query_selector(selector)
                    if rating_el:
                        rating_text = rating_el.text_content().strip()
                        if rating_text:
                            try:
                                # 별점 추출 (예: "5", "별점 5점", "5.0" 등)
                                rating_value = re.search(r'(\d+(\.\d+)?)', rating_text)
                                if rating_value:
                                    review_data["별점"] = float(rating_value.group(1))
                            except Exception:
                                pass
                        break
                
                # 구매 확정 여부
                purchase_selectors = [
                    'span[class*="purchase_badge"]',
                    'span.badge_purchase',
                    'span.goods_purchase',
                    'div[class*="purchased"]'
                ]
                
                for selector in purchase_selectors:
                    purchase_el = review_element.query_selector(selector)
                    if purchase_el:
                        purchase_text = purchase_el.text_content().strip()
                        if "구매" in purchase_text:
                            review_data["구매확정"] = "Y"
                        break
                
                # 옵션 정보
                option_selectors = [
                    'div[class*="option_item"]',
                    'div.option',
                    'p.option_name',
                    'div[class*="ProductOption_"]'
                ]
                
                for selector in option_selectors:
                    option_el = review_element.query_selector(selector)
                    if option_el:
                        option_text = option_el.text_content().strip()
                        if option_text and ":" in option_text:
                            review_data["옵션정보"] = option_text
                        break
                
                # 작성일자
                date_selectors = [
                    'span[class*="date_"]',
                    'div.review_date',
                    'span.date',
                    'div[class*="Date_"]'
                ]
                
                for selector in date_selectors:
                    date_el = review_element.query_selector(selector)
                    if date_el:
                        date_text = date_el.text_content().strip()
                        if date_text:
                            review_data["작성일자"] = date_text
                        break
                
                # 리뷰 내용
                content_selectors = [
                    'div[class*="review_text"]',
                    'p[class*="review_text"]',
                    'span[class*="review_text"]',
                    'div.reviewItems_text__XO1CP'
                ]
                
                for selector in content_selectors:
                    content_el = review_element.query_selector(selector)
                    if content_el:
                        content_text = content_el.text_content().strip()
                        if content_text:
                            review_data["리뷰내용"] = content_text
                        break
                
                # 이미지 URL (있으면)
                image_selectors = [
                    'img[class*="review_img"]',
                    'div[class*="review_img"] img',
                    'div[class*="thumbnail"] img',
                    'a[class*="photo"] img'
                ]
                
                image_urls = []
                for selector in image_selectors:
                    image_elements = review_element.query_selector_all(selector)
                    for image_el in image_elements:
                        src = image_el.get_attribute('src')
                        if src:
                            image_urls.append(src)
                
                if image_urls:
                    review_data["이미지URL"] = ';'.join(image_urls)
            
            return review_data
            
        except Exception as e:
            self.logger.error(f"리뷰 데이터 추출 중 오류: {str(e)}")
            return None


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