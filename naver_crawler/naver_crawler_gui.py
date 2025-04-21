#!/usr/bin/env python
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import os
import pandas as pd
import sys
import io
import time
import subprocess
import platform
from naver_search_crawler_url_analysis import NaverSearchCrawler
import webbrowser
import urllib.parse  # URL 인코딩을 위한 모듈 추가
from datetime import datetime  # 날짜, 시간 처리를 위한 모듈 추가

class RedirectText:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.buffer = io.StringIO()
        
    def write(self, string):
        self.buffer.write(string)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(tk.END, self.buffer.getvalue())
        self.text_widget.see(tk.END)
        
    def flush(self):
        pass

class NaverCrawlerGUI:
    def __init__(self, root):
        """GUI 초기화"""
        self.root = root
        self.root.title("네이버 검색 크롤러")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # 스타일 설정
        self.style = ttk.Style()
        self.style.configure("TButton", font=("맑은 고딕", 10))
        self.style.configure("TLabel", font=("맑은 고딕", 10))
        self.style.configure("TFrame", background="#f0f0f0")
        
        # 파비콘 설정 시도
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "naver_icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
        except Exception:
            pass
        
        # 변수 초기화
        self.file_path = tk.StringVar()
        # 결과 저장 기본 경로를 results 폴더로 지정
        self.results_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
        # results 폴더가 없으면 생성
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
        
        # 기본 파일명 변경
        self.output_path = tk.StringVar(value=os.path.join(self.results_dir, "네이버_검색_결과"))
        self.show_browser = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="준비")
        self.crawling_thread = None
        self.current_result_files = []
        
        # 메인 프레임
        self.main_frame = ttk.Frame(root, padding=10)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 상단 프레임 (입력 영역)
        self.input_frame = ttk.LabelFrame(self.main_frame, text="키워드 입력", padding=10)
        self.input_frame.pack(fill=tk.BOTH, padx=5, pady=5)
        
        # 키워드 직접 입력 영역
        self.keywords_label = ttk.Label(self.input_frame, text="키워드 입력 (쉼표 또는 줄바꿈으로 구분):")
        self.keywords_label.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        # 키워드 입력을 위한 텍스트 박스로 변경 (엑셀 복사/붙여넣기 지원)
        self.keywords_text = scrolledtext.ScrolledText(self.input_frame, width=50, height=5)
        self.keywords_text.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # 키워드 입력 도움말 추가
        help_text = "* 엑셀에서 복사한 내용을 그대로 붙여넣을 수 있습니다.\n* 쉼표(,) 또는 줄바꿈으로 구분된 키워드를 인식합니다.\n* 중복 키워드는 자동으로 제거됩니다."
        help_label = ttk.Label(self.input_frame, text=help_text, foreground="gray")
        help_label.grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # 텍스트 위젯에 오른쪽 클릭 메뉴 추가
        self.create_text_context_menu(self.keywords_text)
        
        # 텍스트 위젯에 키보드 바인딩 추가 (Ctrl+V 등)
        self.keywords_text.bind("<Control-v>", self.paste_to_text)
        self.keywords_text.bind("<Command-v>", self.paste_to_text)  # macOS 지원
        
        # 또는 구분선
        ttk.Separator(self.input_frame, orient=tk.HORIZONTAL).grid(row=2, column=0, columnspan=2, sticky=tk.EW, padx=5, pady=10)
        
        # 파일로 키워드 입력 영역
        self.file_label = ttk.Label(self.input_frame, text="키워드 파일 (xlsx, csv):")
        self.file_label.grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.file_frame = ttk.Frame(self.input_frame)
        self.file_frame.grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path, width=50)
        self.file_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.browse_button = ttk.Button(self.file_frame, text="찾아보기", command=self.browse_file)
        self.browse_button.pack(side=tk.RIGHT, padx=5)
        
        # 출력 파일 경로 설정
        self.output_label = ttk.Label(self.input_frame, text="결과 저장 경로:")
        self.output_label.grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.output_frame = ttk.Frame(self.input_frame)
        self.output_frame.grid(row=4, column=1, sticky=tk.EW, padx=5, pady=5)
        
        self.output_path = tk.StringVar(value="네이버_검색_결과")
        self.output_entry = ttk.Entry(self.output_frame, textvariable=self.output_path, width=50)
        self.output_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.output_browse_button = ttk.Button(self.output_frame, text="찾아보기", command=self.browse_output_dir)
        self.output_browse_button.pack(side=tk.RIGHT, padx=5)
        
        # 브라우저 표시 여부
        self.show_browser = tk.BooleanVar(value=False)
        self.show_browser_check = ttk.Checkbutton(self.input_frame, text="브라우저 화면 표시", variable=self.show_browser)
        self.show_browser_check.grid(row=5, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # 실행 버튼 프레임
        self.button_frame = ttk.Frame(self.main_frame)
        self.button_frame.pack(fill=tk.X, pady=10)
        
        self.run_button = ttk.Button(self.button_frame, text="크롤링 시작", command=self.start_crawling)
        self.run_button.pack(side=tk.RIGHT, padx=5)
        
        self.clear_button = ttk.Button(self.button_frame, text="초기화", command=self.clear_fields)
        self.clear_button.pack(side=tk.RIGHT, padx=5)
        
        # 결과 파일 바로가기 버튼들 (왼쪽에 배치)
        shortcut_label = ttk.Label(self.button_frame, text="결과 바로가기:")
        shortcut_label.pack(side=tk.LEFT, padx=(0, 5))
        
        self.open_folder_button = ttk.Button(self.button_frame, text="결과 폴더 열기", 
                                           command=self.open_result_folder, state="disabled")
        self.open_folder_button.pack(side=tk.LEFT, padx=5)
        
        self.open_excel_button = ttk.Button(self.button_frame, text="엑셀 파일 열기", 
                                           command=lambda: self.open_result_file("xlsx"), state="disabled")
        self.open_excel_button.pack(side=tk.LEFT, padx=5)
        
        self.open_csv_button = ttk.Button(self.button_frame, text="CSV 파일 열기", 
                                         command=lambda: self.open_result_file("csv"), state="disabled")
        self.open_csv_button.pack(side=tk.LEFT, padx=5)
        
        # 탭 컨트롤 추가 (로그/결과)
        self.tab_control = ttk.Notebook(self.main_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 로그 탭
        self.log_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.log_tab, text="실행 로그")
        
        # 결과 요약 탭
        self.summary_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.summary_tab, text="결과 요약")
        
        # 섹션 정보 탭
        self.section_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.section_tab, text="섹션 정보")
        
        # 결과 상세 탭
        self.detail_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.detail_tab, text="결과 상세")
        
        # 로그 영역
        self.log_frame = ttk.LabelFrame(self.log_tab, text="실행 로그", padding=10)
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(self.log_frame, height=15)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 결과 요약 영역
        self.summary_frame = ttk.LabelFrame(self.summary_tab, text="키워드별 결과 요약", padding=10)
        self.summary_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 요약 트리뷰
        self.summary_tree = ttk.Treeview(self.summary_frame)
        self.summary_tree["columns"] = ("키워드", "검색_URL", "인기글_탭_존재", "인기글_탭_제목", "첫번째_섹션")
        self.summary_tree.column("#0", width=0, stretch=tk.NO)
        self.summary_tree.column("키워드", anchor=tk.W, width=120)
        self.summary_tree.column("검색_URL", anchor=tk.W, width=180)
        self.summary_tree.column("인기글_탭_존재", anchor=tk.CENTER, width=80)
        self.summary_tree.column("인기글_탭_제목", anchor=tk.W, width=150)
        self.summary_tree.column("첫번째_섹션", anchor=tk.W, width=150)
        
        self.summary_tree.heading("#0", text="", anchor=tk.W)
        self.summary_tree.heading("키워드", text="키워드", anchor=tk.W)
        self.summary_tree.heading("검색_URL", text="검색 URL", anchor=tk.W)
        self.summary_tree.heading("인기글_탭_존재", text="인기글 존재", anchor=tk.CENTER)
        self.summary_tree.heading("인기글_탭_제목", text="인기글 섹션", anchor=tk.W)
        self.summary_tree.heading("첫번째_섹션", text="첫번째 섹션", anchor=tk.W)
        
        # 요약 트리뷰 스크롤바
        self.summary_scrollbar = ttk.Scrollbar(self.summary_frame, orient="vertical", command=self.summary_tree.yview)
        self.summary_tree.configure(yscrollcommand=self.summary_scrollbar.set)
        
        # 요약 트리뷰 수평 스크롤바
        self.summary_h_scrollbar = ttk.Scrollbar(self.summary_frame, orient="horizontal", command=self.summary_tree.xview)
        self.summary_tree.configure(xscrollcommand=self.summary_h_scrollbar.set)
        
        # 요약 트리뷰 그리드 배치
        self.summary_tree.grid(row=0, column=0, sticky="nsew")
        self.summary_scrollbar.grid(row=0, column=1, sticky="ns")
        self.summary_h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 요약 프레임 그리드 설정
        self.summary_frame.grid_rowconfigure(0, weight=1)
        self.summary_frame.grid_columnconfigure(0, weight=1)
        
        # 검색 URL 클릭 시 브라우저에서 열기
        self.summary_tree.bind("<Double-1>", self.on_summary_double_click)
        
        # 섹션 정보 영역
        self.section_frame = ttk.LabelFrame(self.section_tab, text="키워드별 섹션 순위", padding=10)
        self.section_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 섹션 트리뷰
        self.section_tree = ttk.Treeview(self.section_frame)
        self.section_tree["columns"] = ("키워드", "1순위", "2순위", "3순위", "4순위", "5순위", "6순위", "7순위", "8순위", "9순위", "10순위")
        self.section_tree.column("#0", width=0, stretch=tk.NO)
        self.section_tree.column("키워드", anchor=tk.W, width=100)
        
        for i in range(1, 11):
            self.section_tree.column(f"{i}순위", anchor=tk.W, width=120)
            self.section_tree.heading(f"{i}순위", text=f"{i}순위", anchor=tk.W)
        
        self.section_tree.heading("#0", text="", anchor=tk.W)
        self.section_tree.heading("키워드", text="키워드", anchor=tk.W)
        
        # 섹션 트리뷰 스크롤바
        self.section_scrollbar = ttk.Scrollbar(self.section_frame, orient="vertical", command=self.section_tree.yview)
        self.section_tree.configure(yscrollcommand=self.section_scrollbar.set)
        
        # 섹션 트리뷰 수평 스크롤바
        self.section_h_scrollbar = ttk.Scrollbar(self.section_frame, orient="horizontal", command=self.section_tree.xview)
        self.section_tree.configure(xscrollcommand=self.section_h_scrollbar.set)
        
        # 섹션 트리뷰 그리드 배치
        self.section_tree.grid(row=0, column=0, sticky="nsew")
        self.section_scrollbar.grid(row=0, column=1, sticky="ns")
        self.section_h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 섹션 프레임 그리드 설정
        self.section_frame.grid_rowconfigure(0, weight=1)
        self.section_frame.grid_columnconfigure(0, weight=1)
        
        # 결과 상세 영역
        self.detail_frame = ttk.LabelFrame(self.detail_tab, text="인기글 상세 결과", padding=10)
        self.detail_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 상세 트리뷰
        self.detail_tree = ttk.Treeview(self.detail_frame)
        self.detail_tree["columns"] = ("키워드", "섹션", "순번", "컨텐츠_유형", "제목", "게시처", "아이디", "작성일", "조회수", "URL")
        self.detail_tree.column("#0", width=0, stretch=tk.NO)
        self.detail_tree.column("키워드", anchor=tk.W, width=80)
        self.detail_tree.column("섹션", anchor=tk.W, width=100)
        self.detail_tree.column("순번", anchor=tk.CENTER, width=40)
        self.detail_tree.column("컨텐츠_유형", anchor=tk.W, width=80)
        self.detail_tree.column("제목", anchor=tk.W, width=200)
        self.detail_tree.column("게시처", anchor=tk.W, width=120)
        self.detail_tree.column("아이디", anchor=tk.W, width=100)
        self.detail_tree.column("작성일", anchor=tk.W, width=80)
        self.detail_tree.column("조회수", anchor=tk.W, width=60)
        self.detail_tree.column("URL", anchor=tk.W, width=200)
        
        self.detail_tree.heading("#0", text="", anchor=tk.W)
        self.detail_tree.heading("키워드", text="키워드", anchor=tk.W)
        self.detail_tree.heading("섹션", text="섹션", anchor=tk.W)
        self.detail_tree.heading("순번", text="순번", anchor=tk.CENTER)
        self.detail_tree.heading("컨텐츠_유형", text="유형", anchor=tk.W)
        self.detail_tree.heading("제목", text="제목", anchor=tk.W)
        self.detail_tree.heading("게시처", text="게시처", anchor=tk.W)
        self.detail_tree.heading("아이디", text="아이디", anchor=tk.W)
        self.detail_tree.heading("작성일", text="작성일", anchor=tk.W)
        self.detail_tree.heading("조회수", text="조회수", anchor=tk.W)
        self.detail_tree.heading("URL", text="URL", anchor=tk.W)
        
        # 상세 트리뷰 스크롤바
        self.detail_scrollbar = ttk.Scrollbar(self.detail_frame, orient="vertical", command=self.detail_tree.yview)
        self.detail_tree.configure(yscrollcommand=self.detail_scrollbar.set)
        
        # 상세 트리뷰 수평 스크롤바
        self.detail_h_scrollbar = ttk.Scrollbar(self.detail_frame, orient="horizontal", command=self.detail_tree.xview)
        self.detail_tree.configure(xscrollcommand=self.detail_h_scrollbar.set)
        
        # 상세 트리뷰 그리드 배치
        self.detail_tree.grid(row=0, column=0, sticky="nsew")
        self.detail_scrollbar.grid(row=0, column=1, sticky="ns")
        self.detail_h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # 상세 프레임 그리드 설정
        self.detail_frame.grid_rowconfigure(0, weight=1)
        self.detail_frame.grid_columnconfigure(0, weight=1)
        
        # URL 더블 클릭 시 브라우저에서 열기
        self.detail_tree.bind("<Double-1>", self.on_detail_double_click)
        
        # 상태 표시줄
        self.status_var = tk.StringVar(value="준비")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 로그 리다이렉션 설정
        self.redirect = RedirectText(self.log_text)
        sys.stdout = self.redirect
        
        # 현재 실행 중인 스레드
        self.crawling_thread = None
        
        # 현재 결과 파일 경로
        self.current_result_files = []
        
        # 초기 포커스 설정
        self.keywords_text.focus_set()
        
        # 창 종료 이벤트 연결
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_text_context_menu(self, text_widget):
        """
        텍스트 위젯에 우클릭 컨텍스트 메뉴 추가
        """
        context_menu = tk.Menu(text_widget, tearoff=0)
        context_menu.add_command(label="붙여넣기", command=lambda: self.paste_text(text_widget))
        context_menu.add_command(label="복사", command=lambda: self.copy_text(text_widget))
        context_menu.add_command(label="잘라내기", command=lambda: self.cut_text(text_widget))
        context_menu.add_separator()
        context_menu.add_command(label="모두 선택", command=lambda: self.select_all_text(text_widget))
        context_menu.add_command(label="모두 지우기", command=lambda: text_widget.delete(1.0, tk.END))
        
        # 우클릭 이벤트에 메뉴 표시
        text_widget.bind("<Button-3>", lambda event: self.show_context_menu(event, context_menu))
    
    def show_context_menu(self, event, menu):
        """컨텍스트 메뉴 표시"""
        menu.post(event.x_root, event.y_root)
    
    def paste_text(self, text_widget):
        """텍스트 위젯에 클립보드 내용 붙여넣기"""
        try:
            clipboard = self.root.clipboard_get()
            if text_widget.tag_ranges(tk.SEL):
                text_widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
            
            # Excel에서 복사한 내용 처리 (탭과 줄바꿈 처리)
            if '\t' in clipboard or '\r\n' in clipboard:
                # 탭을 쉼표로 변환
                clipboard = clipboard.replace('\t', ',')
                # Windows 줄바꿈 통일
                clipboard = clipboard.replace('\r\n', '\n')
                
                print("Excel에서 복사한 키워드를 감지하여 처리했습니다.")
            
            text_widget.insert(tk.INSERT, clipboard)
        except tk.TclError:
            pass
    
    def copy_text(self, text_widget):
        """선택된 텍스트 복사"""
        try:
            if text_widget.tag_ranges(tk.SEL):
                selected_text = text_widget.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
        except tk.TclError:
            pass
    
    def cut_text(self, text_widget):
        """선택된 텍스트 잘라내기"""
        self.copy_text(text_widget)
        if text_widget.tag_ranges(tk.SEL):
            text_widget.delete(tk.SEL_FIRST, tk.SEL_LAST)
    
    def select_all_text(self, text_widget):
        """텍스트 모두 선택"""
        text_widget.tag_add(tk.SEL, "1.0", tk.END)
        text_widget.mark_set(tk.INSERT, "1.0")
        text_widget.see(tk.INSERT)
    
    def paste_to_text(self, event=None):
        """Ctrl+V 이벤트 핸들러"""
        self.paste_text(self.keywords_text)
        return "break"  # tkinter 기본 이벤트 처리 중단
    
    def browse_file(self):
        """키워드 파일 선택 대화상자"""
        filetypes = (
            ("Excel 파일", "*.xlsx *.xls"),
            ("CSV 파일", "*.csv"),
            ("모든 파일", "*.*")
        )
        filename = filedialog.askopenfilename(
            title="키워드 파일 선택",
            filetypes=filetypes
        )
        if filename:
            self.file_path.set(filename)
    
    def browse_output_dir(self):
        """결과 저장 경로 선택 대화상자"""
        # 기본 디렉토리를 results 폴더로 설정
        initial_dir = self.results_dir
        
        output_path = filedialog.asksaveasfilename(
            title="결과 파일 저장 위치",
            defaultextension=".xlsx",
            filetypes=[("Excel 파일", "*.xlsx")],
            initialdir=initial_dir
        )
        if output_path:
            # 확장자 제거
            base_path = os.path.splitext(output_path)[0]
            self.output_path.set(base_path)
    
    def clear_fields(self):
        """모든 입력 필드 초기화"""
        self.keywords_text.delete(1.0, tk.END)
        self.file_path.set("")
        self.output_path.set("네이버_검색_결과")
        self.show_browser.set(False)
        self.log_text.delete(1.0, tk.END)
        self.status_var.set("준비")
        self.disable_result_buttons()
    
    def disable_result_buttons(self):
        """결과 파일 버튼 비활성화"""
        self.open_excel_button.configure(state="disabled")
        self.open_csv_button.configure(state="disabled")
        self.open_folder_button.configure(state="disabled")
        
    def enable_result_buttons(self):
        """결과 파일 버튼 활성화"""
        self.open_excel_button.configure(state="normal")
        self.open_csv_button.configure(state="normal")
        self.open_folder_button.configure(state="normal")
    
    def open_result_file(self, file_type):
        """결과 파일 열기"""
        # 현재 파일 목록에서 찾기
        if self.current_result_files:
            # 파일 타입에 따라 열 파일 선택
            if file_type == "xlsx":
                file_path = next((f for f in self.current_result_files if f.endswith(".xlsx")), None)
            elif file_type == "csv":
                file_path = next((f for f in self.current_result_files if f.endswith("_contents.csv")), None)
            else:
                file_path = None
            
            if file_path and os.path.exists(file_path):
                self.open_file(file_path)
                return
        
        # 현재 결과 파일이 없거나 파일이 존재하지 않으면 최신 파일 찾기
        try:
            # 기본 저장 경로 확인
            output_dir = os.path.dirname(self.output_path.get())
            if not output_dir:
                output_dir = "."
            
            if not os.path.exists(output_dir):
                messagebox.showinfo("알림", f"결과 폴더가 존재하지 않습니다: {output_dir}")
                return
            
            # 파일 목록 가져오기
            files = []
            file_pattern = "*.xlsx" if file_type == "xlsx" else "*_contents.csv"
            
            for filename in os.listdir(output_dir):
                if (file_type == "xlsx" and filename.endswith(".xlsx")) or \
                   (file_type == "csv" and filename.endswith("_contents.csv")):
                    filepath = os.path.join(output_dir, filename)
                    files.append((filepath, os.path.getmtime(filepath)))
            
            if not files:
                messagebox.showinfo("알림", f"'{file_type}' 형식의 결과 파일을 찾을 수 없습니다.")
                return
            
            # 가장 최근에 수정된 파일 열기
            newest_file = max(files, key=lambda x: x[1])[0]
            self.open_file(newest_file)
            print(f"최신 {file_type} 파일을 열었습니다: {os.path.basename(newest_file)}")
            
        except Exception as e:
            messagebox.showerror("오류", f"파일을 열 수 없습니다: {str(e)}")
            print(f"결과 파일 열기 오류: {str(e)}")
    
    def open_result_folder(self):
        """결과 파일이 있는 폴더 열기"""
        try:
            # 현재 결과 파일이 있으면 그 폴더 열기
            if self.current_result_files and os.path.exists(self.current_result_files[0]):
                folder_path = os.path.dirname(os.path.abspath(self.current_result_files[0]))
            else:
                # 아니면 결과 저장 폴더 열기
                folder_path = self.results_dir
                
                # 폴더가 없으면 생성
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path)
            
            # 운영체제별 폴더 열기
            if platform.system() == 'Windows':
                os.startfile(folder_path)
            elif platform.system() == 'Darwin':  # macOS
                subprocess.run(['open', folder_path])
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
                
            print(f"결과 폴더를 열었습니다: {folder_path}")
            
        except Exception as e:
            print(f"폴더 열기 오류: {str(e)}")
            messagebox.showerror("오류", f"폴더를 열 수 없습니다: {str(e)}")
    
    def open_file(self, filepath):
        """파일 열기 (운영체제별)"""
        if platform.system() == "Windows":
            os.startfile(filepath)
        elif platform.system() == "Darwin":  # macOS
            subprocess.run(["open", filepath])
        else:  # Linux
            subprocess.run(["xdg-open", filepath])
    
    def create_keywords_file(self, keywords):
        """
        키워드 목록으로 임시 CSV 파일 생성
        
        Args:
            keywords (list): 키워드 목록
            
        Returns:
            str: 생성된 파일 경로
        """
        # 현재 디렉토리에 임시 파일 생성
        temp_file = "temp_keywords.csv"
        
        # 키워드를 데이터프레임으로 변환
        df = pd.DataFrame({"키워드": keywords})
        
        # CSV 파일로 저장
        df.to_csv(temp_file, index=False, encoding="utf-8")
        
        return temp_file
    
    def process_keywords_text(self):
        """
        텍스트 상자에서 키워드 목록 추출
        
        Returns:
            list: 키워드 목록
        """
        text = self.keywords_text.get(1.0, tk.END).strip()
        if not text:
            return []
        
        # 쉼표, 탭, 줄바꿈으로 분리
        lines = text.replace('\r\n', '\n').split('\n')
        keywords = []
        
        for line in lines:
            # 줄에 쉼표가 있으면 쉼표로 분리
            if ',' in line:
                keywords.extend([k.strip() for k in line.split(',') if k.strip()])
            # 줄에 탭이 있으면 탭으로 분리
            elif '\t' in line:
                keywords.extend([k.strip() for k in line.split('\t') if k.strip()])
            else:
                # 없으면 그대로 추가
                if line.strip():
                    keywords.append(line.strip())
        
        # 중복 제거 및 정렬
        unique_keywords = sorted(list(dict.fromkeys(keywords)))
        if len(unique_keywords) < len(keywords):
            print(f"중복된 키워드 {len(keywords) - len(unique_keywords)}개가 제거되었습니다.")
        
        return unique_keywords
    
    def start_crawling(self):
        """크롤링 작업 시작"""
        # 실행 중이면 중단
        if self.crawling_thread and self.crawling_thread.is_alive():
            print("이미 실행 중인 작업이 있습니다.")
            return
        
        # 키워드 확인
        keywords = self.process_keywords_text()
        file_path = self.file_path.get().strip()
        
        if not keywords and not file_path:
            print("키워드를 입력하거나 키워드 파일을 선택해주세요.")
            self.status_var.set("오류: 키워드 없음")
            return
        
        # 출력 경로 확인
        output_path = self.output_path.get().strip()
        if not output_path:
            print("결과 저장 경로를 입력해주세요.")
            self.status_var.set("오류: 저장 경로 없음")
            return
        
        # 현재 시간을 파일명에 추가
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        
        # 기존 경로에 타임스탬프 추가
        output_dir = os.path.dirname(output_path)
        file_name = os.path.basename(output_path)
        
        # 결과 폴더가 없으면 생성
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"결과 저장 폴더 생성: {output_dir}")
        
        # 타임스탬프 추가한 새 출력 경로 생성
        output_path_with_timestamp = os.path.join(output_dir, f"{file_name}_{timestamp}")
        print(f"결과 파일은 {output_path_with_timestamp}로 저장됩니다.")
        
        # 작업 시작 상태 표시
        self.status_var.set("크롤링 작업 준비 중...")
        self.log_text.delete(1.0, tk.END)
        
        # 결과 파일 버튼 비활성화
        self.disable_result_buttons()
        
        # 키워드 입력 방식에 따라 처리
        input_file = file_path
        
        # 직접 입력한 키워드가 있으면 임시 파일 생성
        has_keywords = False
        if keywords:
            has_keywords = True
            print(f"입력한 키워드 {len(keywords)}개: {', '.join(keywords[:5])}" + ("..." if len(keywords) > 5 else ""))
            input_file = self.create_keywords_file(keywords)
            print(f"임시 키워드 파일 생성: {input_file}")
        
        # 브라우저 표시 여부
        show_browser = self.show_browser.get()
        
        # UI 요소 비활성화
        self.disable_ui()
        
        # 별도 스레드에서 크롤링 작업 실행
        self.crawling_thread = threading.Thread(
            target=self.run_crawler,
            args=(input_file, output_path_with_timestamp, show_browser, has_keywords)
        )
        self.crawling_thread.daemon = True
        self.crawling_thread.start()
    
    def on_summary_double_click(self, event):
        """요약 트리뷰 더블 클릭 시 브라우저에서 URL 열기"""
        try:
            item = self.summary_tree.selection()[0]
            column = self.summary_tree.identify_column(event.x)
            
            # "검색_URL" 컬럼(#2) 클릭 시
            if column == "#2":
                url = self.summary_tree.item(item, "values")[1]
                if url and url != "None" and url.startswith("http"):
                    webbrowser.open(url)
                    print(f"브라우저에서 URL 열기: {url}")
            # 키워드 열 클릭 시 네이버 검색 결과 열기
            elif column == "#1":
                keyword = self.summary_tree.item(item, "values")[0]
                encoded_keyword = urllib.parse.quote(keyword)
                search_url = f"https://search.naver.com/search.naver?query={encoded_keyword}"
                webbrowser.open(search_url)
                print(f"브라우저에서 검색 결과 열기: {search_url}")
        except (IndexError, Exception) as e:
            pass
    
    def on_detail_double_click(self, event):
        """상세 트리뷰 더블 클릭 시 브라우저에서 URL 열기"""
        try:
            item = self.detail_tree.selection()[0]
            column = self.detail_tree.identify_column(event.x)
            
            # "URL" 컬럼(#10) 클릭 시
            if column == "#10":
                url = self.detail_tree.item(item, "values")[9]
                if url and url != "None" and url != "링크 없음" and url.startswith("http"):
                    webbrowser.open(url)
                    print(f"브라우저에서 URL 열기: {url}")
            
            # "검색_URL" 열 또는 "키워드" 열 클릭 시 검색 URL 열기
            elif column in ("#1", "#2"):
                keyword = self.detail_tree.item(item, "values")[0]
                encoded_keyword = urllib.parse.quote(keyword)
                search_url = f"https://search.naver.com/search.naver?query={encoded_keyword}"
                webbrowser.open(search_url)
                print(f"브라우저에서 검색 결과 열기: {search_url}")
        
        except (IndexError, Exception) as e:
            pass
    
    def update_result_trees(self, all_results, content_results, section_results):
        """결과 트리뷰 업데이트"""
        # 기존 항목 삭제
        self.summary_tree.delete(*self.summary_tree.get_children())
        self.detail_tree.delete(*self.detail_tree.get_children())
        self.section_tree.delete(*self.section_tree.get_children())
        
        # 데이터가 없으면 탭 전환 없이 종료
        if not all_results and not content_results and not section_results:
            return
        
        # 요약 트리뷰 업데이트
        for i, result in enumerate(all_results):
            self.summary_tree.insert("", i, values=(
                result.get("키워드", ""),
                result.get("검색_URL", ""),
                "있음" if result.get("인기글_탭_존재") else "없음",
                result.get("인기글_탭_제목", ""),
                result.get("첫번째_섹션", "")
            ))
        
        # 섹션 트리뷰 업데이트
        for i, section_row in enumerate(section_results):
            # 섹션 정보 행 구성
            values = [section_row.get("키워드", "")]
            
            # 각 순위별 섹션 추가
            for rank in range(1, 11):
                rank_key = f"{rank}순위"
                values.append(section_row.get(rank_key, ""))
            
            self.section_tree.insert("", i, values=values)
        
        # 상세 트리뷰 업데이트
        for i, content in enumerate(content_results):
            self.detail_tree.insert("", i, values=(
                content.get("키워드", ""),
                content.get("섹션", ""),
                content.get("순번", ""),
                content.get("컨텐츠_유형", ""),
                content.get("제목", ""),
                content.get("게시처", ""),
                content.get("아이디", ""),
                content.get("작성일", ""),
                content.get("조회수", ""),
                content.get("URL", "")
            ))
        
        # 탭 전환하여 결과 보여주기
        if section_results:
            self.tab_control.select(self.section_tab)
        elif content_results:
            self.tab_control.select(self.detail_tab)
        else:
            self.tab_control.select(self.summary_tab)
    
    def load_results_from_files(self):
        """결과 파일에서 데이터 로드하여 트리뷰에 표시"""
        try:
            all_results = []
            content_results = []
            section_results = []
            
            # 현재 결과 파일이 있는지 확인
            if not self.current_result_files:
                print("먼저 크롤링을 실행하여 결과 파일을 생성해주세요.")
                return
            
            # 요약 CSV 파일 경로
            summary_file = next((f for f in self.current_result_files if f.endswith("_summary.csv")), None)
            
            # 컨텐츠 CSV 파일 경로
            contents_file = next((f for f in self.current_result_files if f.endswith("_contents.csv")), None)
            
            # 섹션 정보 CSV 파일 경로
            sections_file = next((f for f in self.current_result_files if f.endswith("_sections.csv")), None)
            
            # 요약 데이터 로드
            if summary_file and os.path.exists(summary_file):
                try:
                    summary_df = pd.read_csv(summary_file, encoding='utf-8-sig')
                    all_results = summary_df.to_dict('records')
                    print(f"요약 데이터 {len(all_results)}개 로드 완료")
                except Exception as e:
                    print(f"요약 데이터 로드 중 오류: {str(e)}")
            
            # 컨텐츠 데이터 로드
            if contents_file and os.path.exists(contents_file):
                try:
                    contents_df = pd.read_csv(contents_file, encoding='utf-8-sig')
                    content_results = contents_df.to_dict('records')
                    print(f"컨텐츠 데이터 {len(content_results)}개 로드 완료")
                except Exception as e:
                    print(f"컨텐츠 데이터 로드 중 오류: {str(e)}")
            
            # 섹션 데이터 로드
            if sections_file and os.path.exists(sections_file):
                try:
                    sections_df = pd.read_csv(sections_file, encoding='utf-8-sig')
                    section_results = sections_df.to_dict('records')
                    print(f"섹션 데이터 {len(section_results)}개 로드 완료")
                except Exception as e:
                    print(f"섹션 데이터 로드 중 오류: {str(e)}")
            
            # 트리뷰 업데이트
            self.update_result_trees(all_results, content_results, section_results)
            
        except Exception as e:
            print(f"결과 파일 로드 중 오류 발생: {str(e)}")
    
    def run_crawler(self, input_file, output_path, show_browser, has_keywords):
        """별도 스레드에서 크롤러 실행"""
        try:
            # 상태 업데이트
            self.update_status("크롤링 작업 실행 중...")
            
            # 크롤러 초기화 및 실행
            crawler = NaverSearchCrawler(headless=not show_browser)
            crawler.process_keyword_list(input_file, output_path)
            
            # 작업 완료 후 임시 파일 삭제
            if has_keywords and input_file == "temp_keywords.csv":
                if os.path.exists(input_file):
                    os.remove(input_file)
                    print("임시 키워드 파일 삭제")
            
            # 결과 파일 경로 출력
            self.current_result_files = [
                f"{output_path}.xlsx",
                f"{output_path}_summary.csv",
                f"{output_path}_sections.csv",
                f"{output_path}_contents.csv"
            ]
            
            print("\n크롤링 작업이 완료되었습니다.")
            print("결과 파일:")
            for file in self.current_result_files:
                if os.path.exists(file):
                    print(f"- {os.path.abspath(file)}")
            
            # 결과 파일 버튼 활성화
            self.root.after(0, self.enable_result_buttons)
            
            # 결과 데이터 로드 및 표시
            self.root.after(0, self.load_results_from_files)
            
            # 완료 상태로 업데이트
            self.update_status("크롤링 완료")
            
        except Exception as e:
            # 오류 발생 시 메시지 출력
            print(f"\n오류 발생: {str(e)}")
            self.update_status(f"오류: {str(e)[:30]}...")
        
        finally:
            # UI 요소 다시 활성화
            self.enable_ui()
    
    def update_status(self, message):
        """스레드 안전하게 상태 메시지 업데이트"""
        self.root.after(0, lambda: self.status_var.set(message))
    
    def disable_ui(self):
        """UI 요소 비활성화"""
        self.root.after(0, lambda: [
            self.keywords_text.configure(state="disabled"),
            self.file_entry.configure(state="disabled"),
            self.output_entry.configure(state="disabled"),
            self.browse_button.configure(state="disabled"),
            self.output_browse_button.configure(state="disabled"),
            self.run_button.configure(state="disabled"),
            self.show_browser_check.configure(state="disabled")
        ])
    
    def enable_ui(self):
        """UI 요소 다시 활성화"""
        self.root.after(0, lambda: [
            self.keywords_text.configure(state="normal"),
            self.file_entry.configure(state="normal"),
            self.output_entry.configure(state="normal"),
            self.browse_button.configure(state="normal"),
            self.output_browse_button.configure(state="normal"),
            self.run_button.configure(state="normal"),
            self.show_browser_check.configure(state="normal")
        ])
    
    def on_closing(self):
        """프로그램 종료 시 처리"""
        # 원래 stdout으로 복원
        sys.stdout = sys.__stdout__
        
        # 실행 중인 스레드가 있으면 경고
        if self.crawling_thread and self.crawling_thread.is_alive():
            if messagebox.askokcancel("종료 확인", "크롤링 작업이 실행 중입니다. 정말 종료하시겠습니까?"):
                self.root.destroy()
        else:
            self.root.destroy()

def main():
    root = tk.Tk()
    app = NaverCrawlerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 