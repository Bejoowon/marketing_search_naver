#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import argparse
import logging
from datetime import datetime

# 로깅 설정
def setup_logging():
    """로깅 설정 초기화 함수"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"naver_crawler_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    return logging.getLogger("NaverCrawlerMain")

# 메인 프로그램 클래스
class NaverCrawlerMain:
    """네이버 크롤러 메인 프로그램"""
    
    def __init__(self):
        """초기화 함수"""
        self.logger = setup_logging()
        self.logger.info("네이버 크롤러 프로그램을 시작합니다.")
        self.modules = {}
        self._load_modules()
    
    def _load_modules(self):
        """크롤러 모듈 로딩"""
        try:
            # 검색 결과 크롤러 모듈 로드
            from modules.search_crawler.naver_search_crawler import NaverSearchCrawler
            self.modules["search"] = NaverSearchCrawler
            self.logger.info("네이버 검색 크롤러 모듈 로드 완료")
            
            # 구매평 크롤러 모듈 로드
            from modules.review_crawler.naver_review_crawler import NaverReviewCrawler
            self.modules["review"] = NaverReviewCrawler
            self.logger.info("네이버 구매평 크롤러 모듈 로드 완료")
            
        except ImportError as e:
            self.logger.error(f"모듈 로드 중 오류 발생: {e}")
            self.logger.error("필요한 모듈이 올바른 위치에 있는지 확인하세요.")
    
    def list_available_modules(self):
        """사용 가능한 모듈 목록 표시"""
        self.logger.info("사용 가능한 크롤러 모듈:")
        for module_name in self.modules.keys():
            self.logger.info(f"- {module_name}")
        
        if not self.modules:
            self.logger.warning("사용 가능한 모듈이 없습니다.")
    
    def run_module(self, module_name, **kwargs):
        """특정 모듈 실행"""
        if module_name not in self.modules:
            self.logger.error(f"'{module_name}' 모듈을 찾을 수 없습니다.")
            self.list_available_modules()
            return False
        
        try:
            self.logger.info(f"{module_name} 모듈을 실행합니다.")
            
            if module_name == "search":
                # 검색 모듈 실행
                if "input_file" in kwargs and "output_file" in kwargs:
                    module_class = self.modules[module_name]
                    module_instance = module_class(headless=kwargs.get("headless", True))
                    
                    module_instance.process_keyword_list(
                        kwargs["input_file"], 
                        kwargs["output_file"]
                    )
                    
                    # 모듈 종료
                    if hasattr(module_instance, 'close'):
                        module_instance.close()
                else:
                    self.logger.error("검색 모듈에는 input_file과 output_file이 필요합니다.")
                    return False
            
            elif module_name == "review":
                # 구매평 크롤러 모듈
                module_class = self.modules[module_name]
                module_instance = module_class(
                    headless=kwargs.get("headless", True),
                    debug_mode=kwargs.get("debug", False)
                )
                
                try:
                    # 단일 URL 또는 파일 목록 처리
                    if "url" in kwargs:
                        output_file = kwargs.get("output_file", f"results/reviews/review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
                        
                        # 구매평 크롤링 실행
                        reviews = module_instance.crawl_product_reviews(
                            kwargs["url"],
                            use_mobile=kwargs.get("use_mobile", False)
                        )
                        
                        if reviews:
                            # 결과를 데이터프레임으로 변환하여 저장
                            import pandas as pd
                            
                            # 상품 URL 정보 추가
                            for review in reviews:
                                review['상품URL'] = kwargs["url"]
                            
                            result_df = pd.DataFrame(reviews)
                            # 출력 파일 확장자 확인 및 저장
                            out_ext = os.path.splitext(output_file)[1].lower()
                            
                            if out_ext == '.xlsx' or out_ext == '.xls':
                                result_df.to_excel(output_file, index=False, engine='openpyxl')
                            else:
                                # 기본적으로 CSV로 저장
                                result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
                            
                            self.logger.info(f"결과가 저장되었습니다: {output_file}")
                    
                    elif "input_file" in kwargs and "output_file" in kwargs:
                        # 파일 목록 처리
                        module_instance.process_product_list(
                            kwargs["input_file"], 
                            kwargs["output_file"]
                        )
                    else:
                        self.logger.error("구매평 모듈은 input_file과 output_file 또는 url이 필요합니다.")
                        return False
                
                finally:
                    # 모듈 종료 (finally 블록에서 항상 실행)
                    if hasattr(module_instance, 'close'):
                        module_instance.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"모듈 실행 중 오류 발생: {str(e)}")
            return False
    
    def run_cli(self):
        """명령줄 인터페이스 실행"""
        parser = argparse.ArgumentParser(description="네이버 크롤러 통합 프로그램")
        parser.add_argument("--module", choices=list(self.modules.keys()), help="실행할 크롤러 모듈")
        parser.add_argument("--input", help="입력 파일 경로(키워드 목록 파일 등)")
        parser.add_argument("--output", help="출력 파일 경로")
        parser.add_argument("--url", help="단일 URL (구매평 모듈에서 사용)")
        parser.add_argument("--headless", action="store_true", help="헤드리스 모드 실행")
        parser.add_argument("--debug", action="store_true", help="디버그 모드 활성화 (브라우저 표시 및 상세 로깅)")
        parser.add_argument("--mobile", action="store_true", help="모바일 페이지 버전으로 접근")
        
        args = parser.parse_args()
        
        if not args.module:
            self.logger.info("모듈이 지정되지 않았습니다. 사용 가능한 모듈 목록을 표시합니다.")
            self.list_available_modules()
            return
        
        kwargs = {
            "headless": args.headless,
            "debug": args.debug,
            "use_mobile": args.mobile
        }
        
        if args.input:
            kwargs["input_file"] = args.input
        
        if args.output:
            kwargs["output_file"] = args.output
            
        if args.url:
            kwargs["url"] = args.url
        
        self.run_module(args.module, **kwargs)


# 메인 함수
def main():
    """메인 진입점 함수"""
    crawler = NaverCrawlerMain()
    crawler.run_cli()


if __name__ == "__main__":
    main() 