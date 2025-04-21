import os
import datetime
import pandas as pd
import numpy as np
import tkinter as tk
from naver_crawler.naver_crawler_gui import NaverCrawlerGUI
from naver_crawler.naver_search_crawler_url_analysis import run_crawler

def crawl_and_save_with_params(params, gui=None):
    """조건에 맞게 크롤링을 실행하고 결과를 저장"""
    keywords = params.get("keywords", [])
    sections = params.get("sections", ["VIEW"])
    ranks = params.get("ranks", [1, 2, 3, 4, 5])
    save_path = params.get("save_path", "")
    
    # 결과 저장 함수
    def save_results(results, timestamp=None):
        if not timestamp:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
        # DataFrame 생성
        df = pd.DataFrame(results)
        
        # 필요한 경우 열 순서 정렬
        columns = [
            "키워드", "섹션", "순번", "컨텐츠_유형", "제목", "게시처", 
            "아이디", "작성일", "조회수", "URL"
        ]
        
        # DataFrame에 있는 열만 사용
        valid_columns = [col for col in columns if col in df.columns]
        df = df[valid_columns]
        
        # save_path가 있는 경우만 파일 저장
        if save_path:
            # 저장 디렉토리 확인
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else ".", exist_ok=True)
            
            # CSV 파일 저장
            csv_path = f"{save_path}_{timestamp}.csv"
            df.to_csv(csv_path, index=False, encoding="utf-8-sig")
            
            # Excel 파일 저장
            excel_path = f"{save_path}_{timestamp}.xlsx"
            df.to_excel(excel_path, index=False, engine="openpyxl")
            
            if gui:
                gui.show_result_msg(f"크롤링이 완료되었습니다.\n결과가 저장되었습니다:\n{csv_path}\n{excel_path}")
                gui.csv_path = csv_path
                gui.excel_path = excel_path
                gui.result_folder = os.path.dirname(csv_path) if os.path.dirname(csv_path) else "."
        
        return df
    
    # 실제 크롤링 실행
    all_results = []
    
    for keyword in keywords:
        if gui:
            gui.update_status(f"'{keyword}' 키워드 크롤링 중...")
        
        try:
            # 크롤링 실행
            results = run_crawler(
                keyword=keyword,
                sections=sections,
                ranks=ranks
            )
            
            if results:
                all_results.extend(results)
                
                if gui:
                    gui.update_status(f"'{keyword}' 키워드 결과: {len(results)}개")
            else:
                if gui:
                    gui.update_status(f"'{keyword}' 키워드 결과 없음")
        
        except Exception as e:
            error_msg = f"'{keyword}' 크롤링 중 오류 발생: {str(e)}"
            print(error_msg)
            if gui:
                gui.update_status(error_msg)
    
    if gui:
        gui.update_status("모든 키워드 크롤링 완료")
    
    # 결과가 있을 경우만 저장
    if all_results:
        df = save_results(all_results)
        return df, all_results
    else:
        if gui:
            gui.show_result_msg("크롤링 결과가 없습니다.")
        return pd.DataFrame(), []

# 애플리케이션 실행
if __name__ == "__main__":
    root = tk.Tk()
    app = NaverCrawlerGUI(root)
    root.mainloop() 