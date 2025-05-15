#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from datetime import datetime
import pandas as pd

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 모듈 임포트
from modules.review_crawler.naver_review_crawler import NaverReviewCrawler


class ReviewTab(ttk.Frame):
    """구매평 수집 탭 클래스"""
    
    def __init__(self, parent, logger):
        """초기화"""
        self.parent = parent
        self.logger = logger
        self.crawler = None
        self.is_crawling = False
        self.thread = None
        
        # 변수 초기화
        self.url_var = tk.StringVar()
        self.max_pages_var = tk.StringVar(value="10")
        self.headless_var = tk.BooleanVar(value=True)
        self.debug_var = tk.BooleanVar(value=False)  # 디버그 모드 변수 추가
        self.output_file_var = tk.StringVar(
            value=os.path.join("results", "reviews", f"reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
        )
        
        # 프레임 생성
        self.frame = ttk.Frame(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """UI 구성"""
        # UI 구성 요소 생성
        main_frame = ttk.Frame(self.frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 왼쪽 패널 (입력 패널)
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # URL 입력 프레임
        url_frame = ttk.LabelFrame(left_frame, text="상품 URL")
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text="URL:").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Entry(url_frame, textvariable=self.url_var, width=50).pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        # 옵션 프레임
        options_frame = ttk.LabelFrame(left_frame, text="수집 옵션")
        options_frame.pack(fill=tk.X, pady=5)
        
        # 최대 페이지 수
        ttk.Label(options_frame, text="최대 페이지 수:").pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Entry(options_frame, textvariable=self.max_pages_var, width=5).pack(side=tk.LEFT, padx=5, pady=5)
        
        # 헤드리스 모드 체크박스
        ttk.Checkbutton(
            options_frame, 
            text="헤드리스 모드", 
            variable=self.headless_var
        ).pack(side=tk.LEFT)
        
        # 디버그 모드 체크박스
        ttk.Checkbutton(
            options_frame, 
            text="디버그 모드 (문제 해결 시 활성화)", 
            variable=self.debug_var
        ).pack(side=tk.LEFT, padx=10)
        
        # 수집 버튼
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(
            button_frame, 
            text="수집 시작", 
            command=self.start_crawling
        )
        self.start_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_button = ttk.Button(
            button_frame, 
            text="수집 중단", 
            command=self.stop_crawling,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT)
        
        # 오른쪽 프레임 (로그 및 결과 부분)
        right_frame = ttk.LabelFrame(main_frame, text="수집 정보", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 노트북 탭 컨트롤 추가 (로그/결과)
        self.tab_control = ttk.Notebook(right_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # 로그 탭
        self.log_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.log_tab, text="실행 로그")
        
        # 결과 탭
        self.result_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.result_tab, text="수집 결과")
        
        # 로그 텍스트 영역
        self.log_text = ScrolledText(self.log_tab, width=50, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 결과 트리뷰
        self.result_frame = ttk.Frame(self.result_tab)
        self.result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 트리뷰 열 정의
        columns = ("번호", "작성자", "별점", "내용", "작성일", "이미지")
        self.result_tree = ttk.Treeview(self.result_frame, columns=columns, show="headings")
        
        # 각 열 설정
        self.result_tree.column("번호", width=40, anchor=tk.CENTER)
        self.result_tree.column("작성자", width=80, anchor=tk.W)
        self.result_tree.column("별점", width=40, anchor=tk.CENTER)
        self.result_tree.column("내용", width=300, anchor=tk.W)
        self.result_tree.column("작성일", width=80, anchor=tk.CENTER)
        self.result_tree.column("이미지", width=50, anchor=tk.CENTER)
        
        # 헤더 설정
        self.result_tree.heading("번호", text="번호")
        self.result_tree.heading("작성자", text="작성자")
        self.result_tree.heading("별점", text="별점")
        self.result_tree.heading("내용", text="리뷰 내용")
        self.result_tree.heading("작성일", text="작성일")
        self.result_tree.heading("이미지", text="이미지")
        
        # 스크롤바
        result_scrollbar = ttk.Scrollbar(self.result_frame, orient="vertical", command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scrollbar.set)
        
        # 수평 스크롤바
        result_h_scrollbar = ttk.Scrollbar(self.result_frame, orient="horizontal", command=self.result_tree.xview)
        self.result_tree.configure(xscrollcommand=result_h_scrollbar.set)
        
        # 트리뷰와 스크롤바 배치
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        result_scrollbar.grid(row=0, column=1, sticky="ns")
        result_h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 결과 프레임 그리드 설정
        self.result_frame.grid_rowconfigure(0, weight=1)
        self.result_frame.grid_columnconfigure(0, weight=1)
        
        # 이미지 더블클릭시 보기
        self.result_tree.bind("<Double-1>", self.on_result_double_click)
        
        # 진행 상태바
        progress_frame = ttk.Frame(self.frame, padding=(10, 0, 10, 10))
        progress_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Label(progress_frame, text="진행 상태:").pack(side=tk.LEFT)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            variable=self.progress_var, 
            length=200, 
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.progress_label_var = tk.StringVar(value="0%")
        ttk.Label(progress_frame, textvariable=self.progress_label_var, width=6).pack(side=tk.LEFT)
    
    def start_crawling(self):
        """크롤링 시작"""
        if self.is_crawling:
            messagebox.showwarning("경고", "이미 수집 중입니다.")
            return
        
        # 입력 URL 가져오기
        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("경고", "URL을 입력해주세요.")
            return
        
        # URL 유효성 검사
        if not url.startswith(("http://", "https://")):
            messagebox.showwarning("경고", "유효한 URL을 입력해주세요.")
            return
        
        # 로그 초기화
        self.log_text.delete(1.0, tk.END)
        self.add_log(f"URL: {url}")
        self.add_log("수집을 시작합니다...")
        
        # 최대 페이지 수 가져오기
        try:
            max_pages = int(self.max_pages_var.get())
        except ValueError:
            max_pages = 10
            self.add_log(f"최대 페이지 수가 유효하지 않아 기본값 {max_pages}으로 설정합니다.")
        
        # 출력 파일 경로 가져오기
        output_file = self.output_file_var.get()
        
        # 크롤러 인스턴스 생성
        self.crawler = NaverReviewCrawler(headless=True)
        
        # UI 비활성화
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.is_crawling = True
        
        # 디버그 모드 설정
        debug_mode = self.debug_var.get() if hasattr(self, 'debug_var') else False
        
        # 스레드 생성
        self.thread = threading.Thread(
            target=self._crawl_thread,
            args=(url, max_pages, output_file, debug_mode)
        )
        self.thread.daemon = True
        self.thread.start()
    
    def _crawl_thread(self, url, max_pages, output_file, debug_mode=False):
        """크롤링 스레드"""
        try:
            # 결과 저장 디렉토리 확인
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            
            # 구매평 수집 시작
            self.add_log(f"최대 {max_pages}페이지까지 수집합니다...")
            
            # 디버그 모드 로그
            if debug_mode:
                self.add_log("디버그 모드가 활성화되었습니다. 상세 로그가 출력됩니다.")
            
            # 진행 상황 콜백 함수
            def progress_callback(current, total, review=None):
                self.progress_var.set(int(current / total * 100))
                self.progress_label_var.set(f"{int(current / total * 100)}%")
                
                if review:
                    if hasattr(review, 'get'):
                        self.add_log(f"리뷰 수집 중: {review.get('작성자명', '알 수 없음')}님의 리뷰")
                    else:
                        self.add_log(f"리뷰 수집 중...")
            
            # 크롤링 실행
            result_df = self.crawler.collect_reviews(
                url, 
                max_pages=max_pages, 
                progress_callback=progress_callback,
                debug_mode=debug_mode
            )
            
            # 결과 처리
            if result_df is not None and not result_df.empty:
                # 엑셀 파일로 저장
                result_df.to_excel(output_file, index=False, engine="openpyxl")
                self.add_log(f"총 {len(result_df)}개의 구매평을 수집하여 저장했습니다.")
                self.add_log(f"파일 경로: {output_file}")
                
                # 테이블에 결과 표시
                self.display_result(result_df)
                
                # 완료 메시지
                messagebox.showinfo("완료", f"구매평 수집이 완료되었습니다.\n총 {len(result_df)}개의 구매평이 저장되었습니다.")
            else:
                self.add_log("수집된 구매평이 없습니다.")
                messagebox.showinfo("완료", "수집된 구매평이 없습니다.")
                
                # 빈 결과 표시
                self.display_result(pd.DataFrame(columns=[
                    "순번", "작성자명", "별점", "작성일자", "리뷰내용"
                ]))
        
        except Exception as e:
            self.add_log(f"오류 발생: {str(e)}")
            
            if debug_mode:
                # 디버그 모드에서는 상세 오류 정보 출력
                import traceback
                self.add_log(f"상세 오류: {traceback.format_exc()}")
                
            messagebox.showerror("오류", f"구매평 수집 중 오류가 발생했습니다.\n{str(e)}")
        
        finally:
            # 크롤링 완료 후 UI 상태 복원
            self.is_crawling = False
            self.progress_var.set(0)
            self.progress_label_var.set("0%")
            self.enable_ui()  # UI 활성화
            
            # 크롤러 종료
            if self.crawler:
                self.crawler.close()
                self.crawler = None
    
    def stop_crawling(self):
        """크롤링 중단"""
        if self.is_crawling and self.crawler:
            self.add_log("수집을 중단합니다...")
            self.crawler.close()
            self.is_crawling = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
    def enable_ui(self):
        """UI 상태 복원"""
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_label_var.set("0%")
    
    def refresh(self):
        """UI 새로고침"""
        if not self.is_crawling:
            # 출력 파일 이름 초기화
            self.output_file_var.set(
                os.path.join("results", "reviews", f"reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")
            )
    
    def paste_to_entry(self, event, widget):
        """Entry 위젯에 텍스트 붙여넣기"""
        try:
            widget.event_generate("<<Paste>>")
        except:
            pass
        return "break"
    
    def copy_from_entry(self, event, widget):
        """Entry 위젯에서 텍스트 복사"""
        try:
            widget.event_generate("<<Copy>>")
        except:
            pass
        return "break"
    
    def cut_from_entry(self, event, widget):
        """Entry 위젯에서 텍스트 자르기"""
        try:
            widget.event_generate("<<Cut>>")
        except:
            pass
        return "break"
    
    def select_all_entry(self, event, widget):
        """Entry 위젯의 텍스트 전체 선택"""
        try:
            widget.select_range(0, tk.END)
            widget.icursor(tk.END)
        except:
            pass
        return "break"
    
    def on_result_double_click(self, event):
        """결과 트리뷰 더블클릭 이벤트"""
        # 선택한 아이템 확인
        item_id = self.result_tree.identify('item', event.x, event.y)
        if not item_id:
            return
        
        # 선택한 행의 열 구하기
        column = self.result_tree.identify('column', event.x, event.y)
        
        # 열 인덱스 (번호: #1, 이미지: #6)
        col_idx = int(column.replace('#', ''))
        
        # 이미지 열인 경우 이미지 보기 기능 실행
        if col_idx == 6:  # 이미지 열
            # 해당 행의 데이터
            values = self.result_tree.item(item_id, 'values')
            
            # 이미지가 있는 경우
            if values[5] == '있음':
                # 크롤링 결과에서 이미지 URL 찾기 필요 (구현 필요)
                messagebox.showinfo("이미지 보기", "이 기능은 아직 준비 중입니다.")
    
    def add_log(self, message):
        """로그 텍스트 영역에 메시지 추가"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def update_progress(self, value, max_value):
        """진행 상태바 업데이트"""
        progress = (value / max_value) * 100
        self.progress_var.set(progress)
        self.progress_label_var.set(f"{progress:.1f}%")
        
    def display_result(self, df):
        """결과 트리뷰에 데이터 표시"""
        # 기존 데이터 삭제
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
            
        # 새 데이터 추가
        if not df.empty:
            for _, row in df.iterrows():
                # 표시할 컬럼 선택 및 포맷팅
                try:
                    values = (
                        row.get("순번", ""),
                        row.get("작성자명", ""),
                        row.get("별점", ""),
                        row.get("작성일자", ""),
                        row.get("리뷰내용", "")[:100] + ("..." if len(row.get("리뷰내용", "")) > 100 else "")
                    )
                    self.result_tree.insert("", "end", values=values)
                except Exception as e:
                    self.add_log(f"결과 표시 중 오류: {str(e)}")
                    
    def submit_crawling(self):
        """크롤링 시작"""
        if self.is_crawling:
            messagebox.showwarning("경고", "이미 수집 중입니다.")
            return 