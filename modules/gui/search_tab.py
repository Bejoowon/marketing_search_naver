#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
import threading
import queue
import pandas as pd
from datetime import datetime

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 검색 크롤러 모듈 임포트
from modules.search_crawler.naver_search_crawler import NaverSearchCrawler


class SearchTab:
    """네이버 검색 결과 크롤링 탭"""
    
    def __init__(self, parent, logger):
        """초기화"""
        self.parent = parent
        self.logger = logger
        self.frame = ttk.Frame(parent)
        self.result_queue = queue.Queue()
        self.crawler_thread = None
        
        # 상태 변수
        self.is_crawling = False
        
        # UI 요소 초기화
        self.setup_ui()
    
    def setup_ui(self):
        """UI 초기화"""
        # 메인 프레임을 그리드로 구성
        main_frame = ttk.Frame(self.frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 왼쪽 패널 (입력 옵션)
        left_panel = ttk.LabelFrame(main_frame, text="검색 크롤링 옵션", padding=10)
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 5))
        
        # 입력 모드 선택 (단일 키워드, 멀티 키워드 또는 파일)
        ttk.Label(left_panel, text="입력 모드:").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        self.input_mode = tk.StringVar(value="keyword")
        
        ttk.Radiobutton(
            left_panel, 
            text="단일 키워드", 
            variable=self.input_mode, 
            value="keyword",
            command=self.toggle_input_mode
        ).grid(row=0, column=1, sticky=tk.W, pady=(0, 5))

        ttk.Radiobutton(
            left_panel, 
            text="다중 키워드", 
            variable=self.input_mode, 
            value="multi_keyword",
            command=self.toggle_input_mode
        ).grid(row=0, column=2, sticky=tk.W, pady=(0, 5))
        
        ttk.Radiobutton(
            left_panel, 
            text="키워드 파일", 
            variable=self.input_mode, 
            value="file",
            command=self.toggle_input_mode
        ).grid(row=0, column=3, sticky=tk.W, pady=(0, 5))
        
        # 단일 키워드 입력 프레임
        self.keyword_frame = ttk.Frame(left_panel)
        self.keyword_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W+tk.E, pady=(0, 10))
        
        ttk.Label(self.keyword_frame, text="검색어:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.keyword_entry = ttk.Entry(self.keyword_frame, width=30)
        self.keyword_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # 단일 키워드 입력 필드에 바인딩 추가
        self.keyword_entry.bind("<Control-v>", lambda e: self.paste_entry(e, self.keyword_entry))
        self.keyword_entry.bind("<Control-c>", lambda e: self.copy_entry(e, self.keyword_entry))
        self.keyword_entry.bind("<Control-x>", lambda e: self.cut_entry(e, self.keyword_entry))
        self.keyword_entry.bind("<Control-a>", lambda e: self.select_all_entry(e, self.keyword_entry))
        # macOS용 Command 키 바인딩 추가
        self.keyword_entry.bind("<Command-v>", lambda e: self.paste_entry(e, self.keyword_entry))
        self.keyword_entry.bind("<Command-c>", lambda e: self.copy_entry(e, self.keyword_entry))
        self.keyword_entry.bind("<Command-x>", lambda e: self.cut_entry(e, self.keyword_entry))
        self.keyword_entry.bind("<Command-a>", lambda e: self.select_all_entry(e, self.keyword_entry))
        
        # 다중 키워드 입력 프레임
        self.multi_keyword_frame = ttk.Frame(left_panel)
        
        ttk.Label(self.multi_keyword_frame, text="검색어 목록:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.multi_keyword_text = ScrolledText(self.multi_keyword_frame, width=30, height=5, wrap=tk.WORD)
        self.multi_keyword_text.grid(row=1, column=0, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # 키보드 바인딩 추가
        self.multi_keyword_text.bind("<Control-v>", lambda e: self.paste_text(e, self.multi_keyword_text))
        self.multi_keyword_text.bind("<Control-c>", lambda e: self.copy_text(e, self.multi_keyword_text))
        self.multi_keyword_text.bind("<Control-x>", lambda e: self.cut_text(e, self.multi_keyword_text))
        self.multi_keyword_text.bind("<Control-a>", lambda e: self.select_all_text(e, self.multi_keyword_text))
        # macOS용 Command 키 바인딩 추가
        self.multi_keyword_text.bind("<Command-v>", lambda e: self.paste_text(e, self.multi_keyword_text))
        self.multi_keyword_text.bind("<Command-c>", lambda e: self.copy_text(e, self.multi_keyword_text))
        self.multi_keyword_text.bind("<Command-x>", lambda e: self.cut_text(e, self.multi_keyword_text))
        self.multi_keyword_text.bind("<Command-a>", lambda e: self.select_all_text(e, self.multi_keyword_text))
        
        ttk.Label(self.multi_keyword_frame, text="각 검색어를 줄바꿈으로 구분하여 입력하세요.").grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 파일 입력 프레임
        self.file_frame = ttk.Frame(left_panel)
        
        ttk.Label(self.file_frame, text="키워드 파일:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.file_entry = ttk.Entry(self.file_frame, width=30)
        self.file_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # 파일 입력 필드에 복사 붙여넣기 바인딩 추가
        self.file_entry.bind("<Control-v>", lambda e: self.paste_entry(e, self.file_entry))
        self.file_entry.bind("<Control-c>", lambda e: self.copy_entry(e, self.file_entry))
        self.file_entry.bind("<Control-x>", lambda e: self.cut_entry(e, self.file_entry))
        self.file_entry.bind("<Control-a>", lambda e: self.select_all_entry(e, self.file_entry))
        # macOS용 Command 키 바인딩 추가
        self.file_entry.bind("<Command-v>", lambda e: self.paste_entry(e, self.file_entry))
        self.file_entry.bind("<Command-c>", lambda e: self.copy_entry(e, self.file_entry))
        self.file_entry.bind("<Command-x>", lambda e: self.cut_entry(e, self.file_entry))
        self.file_entry.bind("<Command-a>", lambda e: self.select_all_entry(e, self.file_entry))
        
        ttk.Button(
            self.file_frame, 
            text="파일 선택", 
            command=self.browse_file
        ).grid(row=0, column=2, padx=5, pady=5)
        
        # 출력 옵션
        ttk.Label(left_panel, text="저장 경로:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.output_entry = ttk.Entry(left_panel, width=30)
        self.output_entry.grid(row=3, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=5)
        self.output_entry.insert(0, os.path.join(os.getcwd(), "results"))
        
        # 출력 입력 필드에 복사 붙여넣기 바인딩 추가
        self.output_entry.bind("<Control-v>", lambda e: self.paste_entry(e, self.output_entry))
        self.output_entry.bind("<Control-c>", lambda e: self.copy_entry(e, self.output_entry))
        self.output_entry.bind("<Control-x>", lambda e: self.cut_entry(e, self.output_entry))
        self.output_entry.bind("<Control-a>", lambda e: self.select_all_entry(e, self.output_entry))
        # macOS용 Command 키 바인딩 추가
        self.output_entry.bind("<Command-v>", lambda e: self.paste_entry(e, self.output_entry))
        self.output_entry.bind("<Command-c>", lambda e: self.copy_entry(e, self.output_entry))
        self.output_entry.bind("<Command-x>", lambda e: self.cut_entry(e, self.output_entry))
        self.output_entry.bind("<Command-a>", lambda e: self.select_all_entry(e, self.output_entry))
        
        ttk.Button(
            left_panel, 
            text="경로 선택", 
            command=self.browse_output_dir
        ).grid(row=3, column=3, padx=5, pady=5)
        
        # 브라우저 모드 체크박스
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            left_panel, 
            text="헤드리스 모드", 
            variable=self.headless_var
        ).grid(row=4, column=0, columnspan=2, sticky=tk.W, pady=5)
        
        # 버튼 프레임
        button_frame = ttk.Frame(left_panel)
        button_frame.grid(row=6, column=0, columnspan=4, sticky=tk.W+tk.E, pady=10)
        
        self.start_button = ttk.Button(
            button_frame, 
            text="크롤링 시작", 
            command=self.start_crawling
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = ttk.Button(
            button_frame, 
            text="중지", 
            command=self.stop_crawling,
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="결과 폴더 열기", 
            command=self.open_results_folder
        ).pack(side=tk.LEFT, padx=5)
        
        # 오른쪽 패널 (로그 출력)
        right_panel = ttk.LabelFrame(main_frame, text="로그", padding=10)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 로그 텍스트 위젯
        self.log_text = ScrolledText(right_panel, width=60, height=20, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 진행 상태 바
        progress_frame = ttk.Frame(self.frame, padding=(10, 0, 10, 10))
        progress_frame.pack(fill=tk.X, expand=False)
        
        ttk.Label(progress_frame, text="진행 상태:").pack(side=tk.LEFT, padx=(0, 5))
        self.progress_var = tk.StringVar(value="준비됨")
        ttk.Label(progress_frame, textvariable=self.progress_var).pack(side=tk.LEFT, padx=5)
        
        self.progress_bar = ttk.Progressbar(
            progress_frame, 
            orient=tk.HORIZONTAL, 
            length=200, 
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        # 초기 모드 설정
        self.toggle_input_mode()
    
    def toggle_input_mode(self):
        """입력 모드에 따라 UI 요소 토글"""
        input_mode = self.input_mode.get()
        
        # 모든 입력 프레임 숨기기
        self.keyword_frame.grid_forget()
        self.multi_keyword_frame.grid_forget()
        self.file_frame.grid_forget()
        
        # 선택된 모드에 따라 표시
        if input_mode == "keyword":
            # 키워드 프레임 표시
            self.keyword_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W+tk.E, pady=(0, 10))
        elif input_mode == "multi_keyword":
            # 멀티 키워드 프레임 표시
            self.multi_keyword_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W+tk.E, pady=(0, 10))
        else:
            # 파일 프레임 표시
            self.file_frame.grid(row=1, column=0, columnspan=4, sticky=tk.W+tk.E, pady=(0, 10))
    
    def browse_file(self):
        """키워드 파일 선택 다이얼로그"""
        filetypes = [
            ("모든 파일", "*.*"),
            ("CSV 파일", "*.csv"),
            ("Excel 파일", "*.xlsx"),
            ("텍스트 파일", "*.txt")
        ]
        
        filename = filedialog.askopenfilename(
            title="키워드 파일 선택",
            filetypes=filetypes
        )
        
        if filename:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, filename)
    
    def browse_output_dir(self):
        """저장 경로 선택 다이얼로그"""
        directory = filedialog.askdirectory(
            title="저장 경로 선택"
        )
        
        if directory:
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, directory)
    
    def open_results_folder(self):
        """결과 폴더 열기"""
        output_dir = self.output_entry.get().strip()
        
        if not output_dir:
            output_dir = os.path.join(os.getcwd(), "results")
        
        # 폴더가 존재하지 않는 경우 생성
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 운영체제에 따라 폴더 열기 명령 실행
        if sys.platform == "win32":
            os.startfile(output_dir)
        elif sys.platform == "darwin":  # macOS
            os.system(f"open {output_dir}")
        else:  # Linux
            os.system(f"xdg-open {output_dir}")
    
    def add_log(self, message):
        """로그 텍스트 위젯에 메시지 추가"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def update_progress(self, current, total, message=""):
        """진행 상태 업데이트"""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar["value"] = progress
            status_text = f"{message} ({current}/{total}, {progress}%)"
        else:
            self.progress_bar["value"] = 0
            status_text = message
        
        self.progress_var.set(status_text)
    
    def start_crawling(self):
        """크롤링 작업 시작"""
        if self.is_crawling:
            return
        
        # 입력 모드 확인
        input_mode = self.input_mode.get()
        
        # 헤드리스 모드 설정
        headless = self.headless_var.get()
        
        # 출력 경로 확인
        output_dir = self.output_entry.get().strip()
        if not output_dir:
            output_dir = os.path.join(os.getcwd(), "results")
        
        # 폴더가 존재하지 않는 경우 생성
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 크롤링 모드에 따라 처리
        if input_mode == "keyword":
            # 단일 키워드 모드
            keyword = self.keyword_entry.get().strip()
            if not keyword:
                messagebox.showerror("오류", "검색어를 입력하세요.")
                return
            
            # 출력 파일 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"search_result_{keyword}_{timestamp}.xlsx")
            
            # 크롤링 스레드 시작
            self.crawler_thread = threading.Thread(
                target=self.crawl_single_keyword,
                args=(keyword, output_file, headless)
            )
        
        elif input_mode == "multi_keyword":
            # 다중 키워드 모드
            keywords_text = self.multi_keyword_text.get(1.0, tk.END).strip()
            if not keywords_text:
                messagebox.showerror("오류", "검색어 목록을 입력하세요.")
                return
            
            # 줄바꿈으로 구분하여 키워드 목록 생성
            keywords = [k.strip() for k in keywords_text.split('\n') if k.strip()]
            if not keywords:
                messagebox.showerror("오류", "유효한 검색어를 입력하세요.")
                return
            
            # 출력 파일 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"search_results_{timestamp}.xlsx")
            
            # 크롤링 스레드 시작
            self.crawler_thread = threading.Thread(
                target=self.crawl_multi_keywords,
                args=(keywords, output_file, headless)
            )
            
        else:
            # 파일 모드
            input_file = self.file_entry.get().strip()
            if not input_file or not os.path.exists(input_file):
                messagebox.showerror("오류", "유효한 키워드 파일을 선택하세요.")
                return
            
            # 출력 파일 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = os.path.join(output_dir, f"search_results_{timestamp}.xlsx")
            
            # 크롤링 스레드 시작
            self.crawler_thread = threading.Thread(
                target=self.crawl_from_file,
                args=(input_file, output_file, headless)
            )
        
        # UI 상태 변경
        self.is_crawling = True
        self.start_button["state"] = tk.DISABLED
        self.stop_button["state"] = tk.NORMAL
        
        # 로그 초기화
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        # 스레드 시작
        self.crawler_thread.daemon = True
        self.crawler_thread.start()
        
        # 결과 큐 확인 스케줄링
        self.check_result_queue()
    
    def crawl_single_keyword(self, keyword, output_file, headless):
        """단일 키워드 크롤링 처리"""
        try:
            self.add_log(f"검색어 '{keyword}' 크롤링을 시작합니다.")
            self.result_queue.put(("progress", 0, 1, "크롤링 준비 중..."))
            
            # 크롤러 인스턴스 생성
            crawler = NaverSearchCrawler(headless=headless)
            
            self.add_log("네이버 검색 페이지에 접속합니다.")
            self.result_queue.put(("progress", 0, 1, "검색 중..."))
            
            # 검색 결과 분석
            result_df = crawler.analyze_search_result(keyword)
            
            # 크롤러 종료
            crawler.close()
            
            # 결과 저장
            if result_df is not None and not result_df.empty:
                result_df.to_excel(output_file, index=False)
                self.add_log(f"검색 결과를 저장했습니다: {output_file}")
                self.result_queue.put(("progress", 1, 1, "완료"))
                self.result_queue.put(("complete", f"{len(result_df)}개의 검색 결과가 저장되었습니다."))
            else:
                self.add_log(f"'{keyword}'에 대한 검색 결과가 없습니다.")
                self.result_queue.put(("progress", 1, 1, "완료"))
                self.result_queue.put(("complete", "검색 결과가 없습니다."))
        
        except Exception as e:
            self.add_log(f"크롤링 중 오류 발생: {e}")
            self.result_queue.put(("error", f"오류 발생: {e}"))
    
    def crawl_from_file(self, input_file, output_file, headless):
        """파일에서 키워드 목록 크롤링 처리"""
        try:
            self.add_log(f"키워드 파일 '{input_file}'에서 크롤링을 시작합니다.")
            self.result_queue.put(("progress", 0, 1, "파일 로딩 중..."))
            
            # 크롤러 인스턴스 생성
            crawler = NaverSearchCrawler(headless=headless)
            
            # 파일 처리
            result = crawler.process_keyword_list(input_file, output_file)
            
            # 크롤러 종료
            crawler.close()
            
            if result:
                self.add_log(f"모든 키워드 검색 결과를 저장했습니다: {output_file}")
                self.result_queue.put(("progress", 1, 1, "완료"))
                self.result_queue.put(("complete", f"검색 결과가 저장되었습니다."))
            else:
                self.add_log("키워드 처리 중 오류가 발생했습니다.")
                self.result_queue.put(("progress", 1, 1, "완료"))
                self.result_queue.put(("error", "키워드 처리 중 오류가 발생했습니다."))
        
        except Exception as e:
            self.add_log(f"크롤링 중 오류 발생: {e}")
            self.result_queue.put(("error", f"오류 발생: {e}"))
    
    def crawl_multi_keywords(self, keywords, output_file, headless):
        """다중 키워드 크롤링 처리"""
        try:
            total_keywords = len(keywords)
            self.add_log(f"총 {total_keywords}개의 검색어 크롤링을 시작합니다.")
            self.result_queue.put(("progress", 0, total_keywords, "크롤링 준비 중..."))
            
            # 결과 데이터프레임 초기화
            results = []
            
            # 크롤러 인스턴스 생성
            crawler = NaverSearchCrawler(headless=headless)
            
            # 각 키워드 처리
            for idx, keyword in enumerate(keywords, 1):
                if not self.is_crawling:
                    break
                
                self.add_log(f"[{idx}/{total_keywords}] 검색어 '{keyword}' 크롤링 중...")
                self.result_queue.put(("progress", idx-1, total_keywords, f"검색어 '{keyword}' 크롤링 중..."))
                
                # 검색 결과 분석
                try:
                    result_df = crawler.analyze_search_result(keyword)
                    
                    if result_df is not None and not result_df.empty:
                        # 키워드 정보 추가
                        result_df["검색어"] = keyword
                        results.append(result_df)
                        self.add_log(f"[{idx}/{total_keywords}] '{keyword}'에 대해 {len(result_df)}개의 결과를 찾았습니다.")
                    else:
                        self.add_log(f"[{idx}/{total_keywords}] '{keyword}'에 대한 검색 결과가 없습니다.")
                
                except Exception as e:
                    self.add_log(f"[{idx}/{total_keywords}] '{keyword}' 검색 중 오류 발생: {e}")
                    continue
            
            # 크롤러 종료
            crawler.close()
            
            # 결과 저장
            if results:
                # 모든 결과 데이터프레임 합치기
                final_df = pd.concat(results, ignore_index=True)
                
                # 엑셀 파일로 저장
                final_df.to_excel(output_file, index=False)
                
                self.add_log(f"총 {len(final_df)}개의 검색 결과를 저장했습니다: {output_file}")
                self.result_queue.put(("progress", total_keywords, total_keywords, "완료"))
                self.result_queue.put(("complete", f"{len(final_df)}개의 검색 결과가 저장되었습니다."))
            else:
                self.add_log("모든 검색어에 대한 결과가 없습니다.")
                self.result_queue.put(("progress", total_keywords, total_keywords, "완료"))
                self.result_queue.put(("complete", "크롤링 완료되었으나 검색 결과가 없습니다."))
        
        except Exception as e:
            self.add_log(f"크롤링 중 오류 발생: {e}")
            self.result_queue.put(("error", f"오류 발생: {e}"))
    
    def check_result_queue(self):
        """결과 큐에서 메시지 확인 및 처리"""
        try:
            while not self.result_queue.empty():
                message = self.result_queue.get(0)
                
                if message[0] == "progress":
                    _, current, total, status = message
                    self.update_progress(current, total, status)
                
                elif message[0] == "log":
                    self.add_log(message[1])
                
                elif message[0] == "complete":
                    self.add_log(message[1])
                    messagebox.showinfo("완료", message[1])
                    self.is_crawling = False
                    self.start_button["state"] = tk.NORMAL
                    self.stop_button["state"] = tk.DISABLED
                    return
                
                elif message[0] == "error":
                    self.add_log(message[1])
                    messagebox.showerror("오류", message[1])
                    self.is_crawling = False
                    self.start_button["state"] = tk.NORMAL
                    self.stop_button["state"] = tk.DISABLED
                    return
        
        except queue.Empty:
            pass
        
        # 크롤링이 진행 중인 경우 계속 큐 확인
        if self.is_crawling:
            self.frame.after(100, self.check_result_queue)
    
    def stop_crawling(self):
        """크롤링 작업 중지"""
        if not self.is_crawling:
            return
        
        self.add_log("크롤링을 중지합니다...")
        self.is_crawling = False
        
        # 버튼 상태 변경
        self.start_button["state"] = tk.NORMAL
        self.stop_button["state"] = tk.DISABLED
    
    def refresh(self):
        """탭 새로고침"""
        if not self.is_crawling:
            self.progress_bar["value"] = 0
            self.progress_var.set("준비됨")
            self.log_text.config(state=tk.NORMAL)
            self.log_text.delete(1.0, tk.END)
            self.log_text.config(state=tk.DISABLED)
    
    def copy_text(self, event, widget):
        """텍스트 복사"""
        try:
            widget.event_generate("<<Copy>>")
        except:
            pass
        return "break"
    
    def paste_text(self, event, widget):
        """텍스트 붙여넣기"""
        try:
            widget.event_generate("<<Paste>>")
        except:
            pass
        return "break"
    
    def cut_text(self, event, widget):
        """텍스트 자르기"""
        try:
            widget.event_generate("<<Cut>>")
        except:
            pass
        return "break"
    
    def select_all_text(self, event, widget):
        """텍스트 전체 선택"""
        try:
            widget.tag_add(tk.SEL, "1.0", tk.END)
            widget.mark_set(tk.INSERT, "1.0")
            widget.see(tk.INSERT)
        except:
            pass
        return "break"

    def paste_entry(self, event, widget):
        """Entry 위젯에 텍스트 붙여넣기"""
        try:
            widget.event_generate("<<Paste>>")
        except:
            pass
        return "break"

    def copy_entry(self, event, widget):
        """Entry 위젯에서 텍스트 복사"""
        try:
            widget.event_generate("<<Copy>>")
        except:
            pass
        return "break"

    def cut_entry(self, event, widget):
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