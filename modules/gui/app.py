#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from datetime import datetime
import threading
import pandas as pd

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 모듈 임포트
from modules.gui.review_tab import ReviewTab
from modules.gui.analysis_tab import AnalysisTab
from modules.gui.wordcloud_tab import WordcloudTab
from modules.gui.search_tab import SearchTab

# 로깅 설정
def setup_logging():
    """로깅 설정 초기화 함수"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"naver_crawler_gui_{timestamp}.log")
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file, encoding='utf-8')
        ]
    )
    return logging.getLogger("NaverCrawlerGUI")


class NaverCrawlerGUI:
    """네이버 크롤러 GUI 애플리케이션"""
    
    def __init__(self, root):
        """초기화"""
        self.root = root
        self.logger = setup_logging()
        
        # 프레임 관리용 변수
        self.current_frame = None
        self.frames = {}
        
        # UI 초기화
        self.setup_ui()
        
        self.logger.info("네이버 크롤러 GUI 애플리케이션이 시작되었습니다.")
        
        # 초기 화면으로 메인 랜딩 보여주기
        self.show_frame("main")
    
    def setup_macos_edit_bindings(self):
        """macOS에서 편집 기능 바인딩 설정 - 사용하지 않음"""
        pass
    
    def _event_generate_handler(self, event_name):
        """이벤트 생성 핸들러 - 사용하지 않음"""
        pass
    
    def _select_all_handler(self, event):
        """전체 선택 핸들러 - 사용하지 않음"""
        pass
    
    def setup_ui(self):
        """UI 초기화"""
        # 루트 윈도우 설정
        self.root.title("네이버 크롤러")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # 메뉴바 생성
        self.create_menu()
        
        # 메인 컨테이너 생성
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)
        
        # 메인 랜딩 프레임 생성
        main_frame = ttk.Frame(container)
        self.frames["main"] = main_frame
        
        # 키워드 수집기 프레임 생성
        keyword_frame = ttk.Frame(container)
        self.frames["keyword"] = {
            "frame": keyword_frame
        }
        
        # 구매평 수집기 프레임 생성
        review_collector_frame = ttk.Frame(container)
        # 먼저 딕셔너리에 추가
        self.frames["review_collector"] = {
            "frame": review_collector_frame,
            "notebook": None
        }
        # 그 다음 설정
        self.setup_review_collector(review_collector_frame)
        
        # 메인 랜딩 페이지 설정
        self.setup_main_landing(main_frame)
        
        # 상태바 생성
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def create_menu(self):
        """메뉴바 생성"""
        menu_bar = tk.Menu(self.root)
        
        # 파일 메뉴
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="홈으로", command=lambda: self.show_frame("main"))
        file_menu.add_command(label="새로고침", command=self.refresh)
        file_menu.add_separator()
        file_menu.add_command(label="종료", command=self.root.quit)
        menu_bar.add_cascade(label="파일", menu=file_menu)
        
        # 편집 메뉴 추가 (복사/붙여넣기 등)
        edit_menu = tk.Menu(menu_bar, tearoff=0)
        # <<Cut>>, <<Copy>>, <<Paste>> 등의 가상 이벤트를 사용
        edit_menu.add_command(label="잘라내기 (⌘X)", 
                             command=lambda: self.root.focus_get().event_generate("<<Cut>>"))
        edit_menu.add_command(label="복사 (⌘C)", 
                             command=lambda: self.root.focus_get().event_generate("<<Copy>>"))
        edit_menu.add_command(label="붙여넣기 (⌘V)", 
                             command=lambda: self.root.focus_get().event_generate("<<Paste>>"))
        edit_menu.add_separator()
        edit_menu.add_command(label="모두 선택 (⌘A)", 
                             command=self.select_all_text)
        menu_bar.add_cascade(label="편집", menu=edit_menu)
        
        # 기능 메뉴
        function_menu = tk.Menu(menu_bar, tearoff=0)
        function_menu.add_command(label="카페 외부노출 키워드 찾기", command=lambda: self.show_frame("keyword"))
        function_menu.add_command(label="구매평 수집기", command=lambda: self.show_frame("review_collector"))
        menu_bar.add_cascade(label="기능", menu=function_menu)
        
        # 도움말 메뉴
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="사용법", command=self.show_help)
        help_menu.add_command(label="정보", command=self.show_about)
        menu_bar.add_cascade(label="도움말", menu=help_menu)
        
        # 메뉴바 설정
        self.root.config(menu=menu_bar)
    
    def select_all_text(self):
        """메뉴: 모두 선택 기능"""
        try:
            widget = self.root.focus_get()
            if isinstance(widget, (tk.Text, ScrolledText)):
                widget.tag_add(tk.SEL, "1.0", tk.END)
                widget.mark_set(tk.INSERT, "1.0")
                widget.see(tk.INSERT)
            elif isinstance(widget, tk.Entry):
                widget.select_range(0, tk.END)
                widget.icursor(tk.END)
        except:
            pass
    
    def show_frame(self, frame_name):
        """특정 프레임 표시"""
        # 현재 표시된 프레임이 있으면 숨김
        if self.current_frame:
            if isinstance(self.current_frame, dict):
                self.current_frame["frame"].pack_forget()
            else:
                self.current_frame.pack_forget()
        
        # 선택된 프레임 표시
        if frame_name == "main":
            self.frames[frame_name].pack(fill="both", expand=True)
            self.current_frame = self.frames[frame_name]
            self.status_var.set("메인 화면")
        elif frame_name == "keyword":
            # 키워드 수집기 프레임이 설정되어 있지 않으면 설정
            if "loaded" not in self.frames["keyword"]:
                # 네이버 검색 크롤러 GUI 통합
                self.setup_keyword_collector(self.frames["keyword"]["frame"])
                self.frames["keyword"]["loaded"] = True
            
            self.frames["keyword"]["frame"].pack(fill="both", expand=True)
            self.current_frame = self.frames["keyword"]
            self.status_var.set("카페 외부노출 키워드 찾기")
        else:
            # 구매평 수집기 프레임
            self.frames[frame_name]["frame"].pack(fill="both", expand=True)
            self.current_frame = self.frames[frame_name]
            self.status_var.set("구매평 수집기")
    
    def setup_main_landing(self, parent):
        """메인 랜딩 페이지 설정"""
        # 제목 프레임
        title_frame = ttk.Frame(parent, padding=20)
        title_frame.pack(fill="x", pady=20)
        
        # 제목에는 일반 tk 레이블 사용(폰트 설정 가능)
        title_label = tk.Label(
            title_frame, 
            text="네이버 크롤러", 
            font=("Helvetica", 24, "bold")
        )
        title_label.pack()
        
        subtitle_label = tk.Label(
            title_frame, 
            text="네이버 검색 결과 및 구매평 수집 프로그램",
            font=("Helvetica", 14)
        )
        subtitle_label.pack(pady=5)
        
        # 메뉴 버튼 프레임
        menu_frame = ttk.Frame(parent, padding=20)
        menu_frame.pack(fill="both", expand=True, padx=100, pady=50)
        
        # 그리드 설정
        menu_frame.columnconfigure(0, weight=1)
        menu_frame.columnconfigure(1, weight=1)
        menu_frame.rowconfigure(0, weight=1)
        
        # 메뉴 버튼 스타일
        button_style = {"width": 25, "padding": 20}
        
        # 키워드 수집기 버튼
        keyword_button = ttk.Button(
            menu_frame,
            text="카페 외부노출 키워드 찾기",
            command=lambda: self.show_frame("keyword"),
            **button_style
        )
        keyword_button.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        
        # 구매평 수집기 버튼
        review_button = ttk.Button(
            menu_frame,
            text="구매평 수집기",
            command=lambda: self.show_frame("review_collector"),
            **button_style
        )
        review_button.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        
        # 설명 프레임
        info_frame = ttk.Frame(parent, padding=20)
        info_frame.pack(fill="x", pady=10)
        
        info_text = """
        네이버 크롤러는 네이버의 검색 결과와 쇼핑몰 상품 구매평 데이터를 수집하고 분석하는 도구입니다.
        
        카페 외부노출 키워드 찾기: 네이버 검색 시 노출되는 카페/블로그 인기글을 수집합니다.
        구매평 수집기: 쇼핑몰 상품 구매평을 수집하고 감성 분석, 워드클라우드를 생성합니다.
        
        결과는 자동으로 'keyword_result_{날짜시간분초}.xlsx' 형식으로 저장됩니다.
        """
        
        info_label = tk.Label(
            info_frame,
            text=info_text,
            justify="center",
            wraplength=700
        )
        info_label.pack(pady=10)
    
    def setup_review_collector(self, parent):
        """구매평 수집기 설정"""
        # 헤더 프레임 (뒤로 가기 버튼 포함)
        header_frame = ttk.Frame(parent, padding=10)
        header_frame.pack(fill="x")
        
        back_button = ttk.Button(
            header_frame,
            text="← 메인으로 돌아가기",
            command=lambda: self.show_frame("main")
        )
        back_button.pack(side=tk.LEFT)
        
        title_label = tk.Label(
            header_frame,
            text="구매평 수집기",
            font=("Helvetica", 14, "bold")
        )
        title_label.pack(side=tk.LEFT, padx=20)
        
        # 탭 컨트롤 생성
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        try:
            # 리뷰 수집기 모듈 로드 시도
            # 각 탭 생성
            review_tab = ReviewTab(notebook, self.logger)
            analysis_tab = AnalysisTab(notebook, self.logger)
            wordcloud_tab = WordcloudTab(notebook, self.logger)
            
            # 탭 추가
            notebook.add(review_tab.frame, text="구매평 수집")
            notebook.add(analysis_tab.frame, text="감성 분석")
            notebook.add(wordcloud_tab.frame, text="워드클라우드")
            
            # 노트북 참조 저장
            self.frames["review_collector"]["notebook"] = notebook
            self.frames["review_collector"]["tabs"] = {
                "review": review_tab,
                "analysis": analysis_tab,
                "wordcloud": wordcloud_tab
            }
            
            self.logger.info("구매평 수집기 모듈 로드 완료")
            
        except Exception as e:
            self.logger.error(f"구매평 수집기 모듈 로드 중 오류 발생: {e}")
            
            # 오류 메시지 탭 생성
            error_tab = ttk.Frame(notebook)
            notebook.add(error_tab, text="오류")
            
            error_label = tk.Label(
                error_tab,
                text=f"구매평 수집기 모듈을 로드할 수 없습니다:\n{e}",
                fg="red",
                font=("Helvetica", 12),
                wraplength=600,
                justify="center"
            )
            error_label.pack(expand=True, pady=50)
            
            suggestion_label = tk.Label(
                error_tab,
                text="modules/review_crawler 디렉토리에 필요한 모듈이 모두 있는지 확인하세요.",
                wraplength=600,
                justify="center"
            )
            suggestion_label.pack(pady=10)
            
            # 노트북 참조 저장
            self.frames["review_collector"]["notebook"] = notebook
            self.frames["review_collector"]["error"] = True
    
    def setup_keyword_collector(self, parent):
        """키워드 수집기 설정"""
        # 헤더 프레임 (뒤로 가기 버튼 포함)
        header_frame = ttk.Frame(parent, padding=10)
        header_frame.grid(row=0, column=0, sticky=tk.EW)
        
        # 헤더 프레임 설정
        header_frame.columnconfigure(0, weight=0)  # 버튼
        header_frame.columnconfigure(1, weight=1)  # 제목
        
        back_button = ttk.Button(
            header_frame,
            text="← 메인으로 돌아가기",
            command=lambda: self.show_frame("main")
        )
        back_button.grid(row=0, column=0, sticky=tk.W)
        
        title_label = tk.Label(
            header_frame,
            text="카페 외부노출 키워드 찾기",
            font=("Helvetica", 14, "bold")
        )
        title_label.grid(row=0, column=1, sticky=tk.W, padx=20)
        
        # 부모 컨테이너 설정
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)
        
        try:
            # naver_search_crawler 모듈 임포트
            # 현재 파일 경로 기준으로 naver_crawler 모듈 추가
            current_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            naver_crawler_dir = os.path.join(current_dir, "naver_crawler")
            if naver_crawler_dir not in sys.path:
                sys.path.append(naver_crawler_dir)
            
            from naver_crawler.naver_search_crawler_url_analysis import NaverSearchCrawler
            
            # 키워드 수집기 UI 구현
            main_frame = ttk.Frame(parent, padding=10)
            main_frame.grid(row=1, column=0, sticky=tk.NSEW)
            
            # 메인 프레임이 확장되도록 설정
            main_frame.columnconfigure(0, weight=1)  # 왼쪽 패널
            main_frame.columnconfigure(1, weight=2)  # 오른쪽 패널
            main_frame.rowconfigure(0, weight=1)
            
            # 왼쪽 패널: 입력 옵션
            left_panel = ttk.LabelFrame(main_frame, text="키워드 입력 옵션", padding=10)
            left_panel.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 10))
            
            # 왼쪽 패널이 확장되도록 설정
            left_panel.columnconfigure(0, weight=1)
            for i in range(8):  # 총 행 수만큼 설정
                left_panel.rowconfigure(i, weight=0)
            left_panel.rowconfigure(1, weight=1)  # 키워드 입력 텍스트 영역은 확장되도록
            
            # 키워드 입력 영역
            ttk.Label(left_panel, text="키워드 입력 (쉼표 또는 줄바꿈으로 구분):").grid(
                row=0, column=0, sticky=tk.W, pady=(0, 5)
            )
            
            # 키워드 입력을 위한 텍스트 박스
            self.keywords_text = ScrolledText(left_panel, width=40, height=10, wrap=tk.WORD)
            self.keywords_text.grid(row=1, column=0, sticky=tk.NSEW, padx=5, pady=5)
            
            # 키보드 바인딩 추가
            self.keywords_text.bind("<Control-v>", lambda e: self.paste_keyword_text(e))
            self.keywords_text.bind("<Control-c>", lambda e: self.copy_keyword_text(e))
            self.keywords_text.bind("<Control-x>", lambda e: self.cut_keyword_text(e))
            self.keywords_text.bind("<Control-a>", lambda e: self.select_all_keyword_text(e))
            # macOS용 Command 키 바인딩 추가
            self.keywords_text.bind("<Command-v>", lambda e: self.paste_keyword_text(e))
            self.keywords_text.bind("<Command-c>", lambda e: self.copy_keyword_text(e))
            self.keywords_text.bind("<Command-x>", lambda e: self.cut_keyword_text(e))
            self.keywords_text.bind("<Command-a>", lambda e: self.select_all_keyword_text(e))
            
            # 도움말 텍스트
            help_text = "* 쉼표 또는 줄바꿈으로 구분된 키워드 입력\n* 엑셀에서 복사한 내용도 붙여넣기 가능"
            ttk.Label(left_panel, text=help_text, foreground="gray").grid(
                row=2, column=0, sticky=tk.W, pady=5
            )
            
            # 구분선
            ttk.Separator(left_panel, orient=tk.HORIZONTAL).grid(
                row=3, column=0, sticky=tk.EW, pady=10
            )
            
            # 파일 입력 영역
            file_frame = ttk.Frame(left_panel)
            file_frame.grid(row=4, column=0, sticky=tk.EW, pady=5)
            
            # file_frame 내부 설정
            file_frame.columnconfigure(0, weight=0)  # 라벨
            file_frame.columnconfigure(1, weight=1)  # Entry 확장
            file_frame.columnconfigure(2, weight=0)  # 버튼
            
            ttk.Label(file_frame, text="키워드 파일:").grid(row=0, column=0, sticky=tk.W)
            
            self.keyword_file_var = tk.StringVar()
            self.keyword_file_entry = ttk.Entry(file_frame, textvariable=self.keyword_file_var)
            self.keyword_file_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
            
            ttk.Button(
                file_frame, 
                text="찾아보기", 
                command=self.browse_keyword_file
            ).grid(row=0, column=2, sticky=tk.E)
            
            # 출력 옵션
            output_frame = ttk.Frame(left_panel)
            output_frame.grid(row=5, column=0, sticky=tk.EW, pady=10)
            
            # output_frame 내부 설정
            output_frame.columnconfigure(0, weight=0)  # 라벨
            output_frame.columnconfigure(1, weight=1)  # Entry 확장
            output_frame.columnconfigure(2, weight=0)  # 버튼
            
            ttk.Label(output_frame, text="결과 저장:").grid(row=0, column=0, sticky=tk.W)
            
            self.keyword_output_var = tk.StringVar(
                value=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                 "results", "네이버_검색_결과")
            )
            
            self.keyword_output_entry = ttk.Entry(
                output_frame, 
                textvariable=self.keyword_output_var
            )
            self.keyword_output_entry.grid(row=0, column=1, sticky=tk.EW, padx=5)
            
            ttk.Button(
                output_frame, 
                text="경로 선택", 
                command=self.browse_keyword_output
            ).grid(row=0, column=2, sticky=tk.E)
            
            # 브라우저 표시 여부
            browser_frame = ttk.Frame(left_panel)
            browser_frame.grid(row=6, column=0, sticky=tk.EW, pady=5)
            
            # browser_frame 내부 설정
            browser_frame.columnconfigure(0, weight=1)
            
            self.show_browser_var = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                browser_frame, 
                text="브라우저 화면 표시", 
                variable=self.show_browser_var
            ).grid(row=0, column=0, sticky=tk.W)
            
            # 버튼 영역
            button_frame = ttk.Frame(left_panel)
            button_frame.grid(row=7, column=0, sticky=tk.EW, pady=10)
            
            # button_frame 내부 설정
            button_frame.columnconfigure(0, weight=1)
            button_frame.columnconfigure(1, weight=1)
            button_frame.columnconfigure(2, weight=1)
            
            self.start_keyword_button = ttk.Button(
                button_frame, 
                text="크롤링 시작", 
                command=self.start_keyword_crawling
            )
            self.start_keyword_button.grid(row=0, column=0, padx=5, sticky=tk.EW)
            
            ttk.Button(
                button_frame, 
                text="초기화", 
                command=self.clear_keyword_fields
            ).grid(row=0, column=1, padx=5, sticky=tk.EW)
            
            ttk.Button(
                button_frame, 
                text="결과 폴더 열기", 
                command=self.open_keyword_result_folder
            ).grid(row=0, column=2, padx=5, sticky=tk.EW)
            
            # 오른쪽 패널: 로그와 결과
            right_panel = ttk.Frame(main_frame)
            right_panel.grid(row=0, column=1, sticky=tk.NSEW)
            
            # 오른쪽 패널이 확장되도록 설정
            right_panel.columnconfigure(0, weight=1)
            right_panel.rowconfigure(0, weight=1)  # 로그 프레임
            right_panel.rowconfigure(1, weight=0)  # 상태 프레임
            
            # 로그 출력
            log_frame = ttk.LabelFrame(right_panel, text="실행 로그", padding=10)
            log_frame.grid(row=0, column=0, sticky=tk.NSEW, pady=(0, 5))
            
            # log_frame 내부 설정
            log_frame.columnconfigure(0, weight=1)
            log_frame.rowconfigure(0, weight=1)
            
            self.keyword_log_text = ScrolledText(log_frame, height=15, wrap=tk.WORD)
            self.keyword_log_text.grid(row=0, column=0, sticky=tk.NSEW)
            self.keyword_log_text.config(state=tk.DISABLED)
            
            # 상태 표시
            status_frame = ttk.Frame(right_panel)
            status_frame.grid(row=1, column=0, sticky=tk.EW, pady=5)
            
            # status_frame 내부 설정
            status_frame.columnconfigure(0, weight=0)  # 라벨
            status_frame.columnconfigure(1, weight=1)  # 상태 텍스트
            
            ttk.Label(status_frame, text="상태:").grid(row=0, column=0, sticky=tk.W)
            
            self.keyword_status_var = tk.StringVar(value="준비됨")
            ttk.Label(status_frame, textvariable=self.keyword_status_var).grid(row=0, column=1, sticky=tk.W, padx=5)
            
            # 크롤링 관련 변수
            self.keyword_crawler_thread = None
            self.is_keyword_crawling = False
            
            # 저장
            self.frames["keyword"]["crawler"] = NaverSearchCrawler
            self.frames["keyword"]["loaded"] = True
            
            self.logger.info("카페 외부노출 키워드 찾기 모듈 로드 완료")
            
        except ImportError as e:
            # 모듈 로드 실패 시 오류 메시지 표시
            error_frame = ttk.Frame(parent, padding=20)
            error_frame.grid(row=1, column=0, sticky=tk.NSEW)
            
            error_label = tk.Label(
                error_frame,
                text=f"카페 외부노출 키워드 찾기 모듈을 로드할 수 없습니다:\n{e}",
                fg="red",
                font=("Helvetica", 12),
                wraplength=600,
                justify="center"
            )
            error_label.pack(expand=True, pady=50)
            
            suggestion_text = """
            naver_crawler 모듈이 올바른 위치에 있는지 확인하세요.
            프로젝트 루트 디렉토리에 naver_crawler 폴더가 있어야 합니다.
            """
            suggestion_label = tk.Label(
                error_frame,
                text=suggestion_text,
                wraplength=600,
                justify="center"
            )
            suggestion_label.pack(pady=10)
            
            self.frames["keyword"]["error"] = True
            self.logger.error(f"카페 외부노출 키워드 찾기 모듈 로드 실패: {e}")
    
    def browse_keyword_file(self):
        """키워드 파일 찾아보기"""
        filetypes = [
            ("모든 파일", "*.*"),
            ("Excel 파일", "*.xlsx;*.xls"),
            ("CSV 파일", "*.csv"),
            ("텍스트 파일", "*.txt")
        ]
        
        filename = filedialog.askopenfilename(
            title="키워드 파일 선택",
            filetypes=filetypes
        )
        
        if filename:
            self.keyword_file_var.set(filename)
    
    def browse_keyword_output(self):
        """키워드 결과 저장 경로 선택"""
        # 파일 저장 다이얼로그
        initialdir = os.path.dirname(self.keyword_output_var.get())
        if not os.path.exists(initialdir):
            initialdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "results")
            if not os.path.exists(initialdir):
                os.makedirs(initialdir)
        
        filename = filedialog.asksaveasfilename(
            title="결과 저장 경로",
            initialdir=initialdir,
            defaultextension=".xlsx",
            filetypes=[("Excel 파일", "*.xlsx"), ("CSV 파일", "*.csv")]
        )
        
        if filename:
            self.keyword_output_var.set(filename)
            # 사용자에게 파일명 수정 정보 알림
            self.add_keyword_log(f"결과 저장 경로가 설정되었습니다: {filename}")
            self.add_keyword_log("※ 실제 저장 시 파일명에 날짜와 시간이 추가됩니다 (예: keyword_result_20250502_123456.xlsx)")
    
    def add_keyword_log(self, message):
        """키워드 수집기 로그 추가"""
        self.keyword_log_text.config(state=tk.NORMAL)
        self.keyword_log_text.insert(tk.END, f"{message}\n")
        self.keyword_log_text.see(tk.END)
        self.keyword_log_text.config(state=tk.DISABLED)
    
    def open_keyword_result_folder(self):
        """키워드 결과 폴더 열기"""
        # 결과 폴더 경로
        output_path = self.keyword_output_var.get()
        result_dir = os.path.dirname(output_path)
        
        if not os.path.exists(result_dir):
            result_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "results")
            if not os.path.exists(result_dir):
                os.makedirs(result_dir)
        
        # 운영체제에 따라 폴더 열기
        if sys.platform == "win32":
            os.startfile(result_dir)
        elif sys.platform == "darwin":  # macOS
            os.system(f"open {result_dir}")
        else:  # Linux
            os.system(f"xdg-open {result_dir}")
    
    def clear_keyword_fields(self):
        """키워드 수집기 입력 필드 초기화"""
        self.keywords_text.delete(1.0, tk.END)
        self.keyword_file_var.set("")
        self.show_browser_var.set(False)
        self.keyword_log_text.config(state=tk.NORMAL)
        self.keyword_log_text.delete(1.0, tk.END)
        self.keyword_log_text.config(state=tk.DISABLED)
        self.keyword_status_var.set("준비됨")
    
    def process_keywords_text(self):
        """텍스트 영역에서 키워드 추출"""
        keywords_text = self.keywords_text.get(1.0, tk.END).strip()
        
        # 빈 텍스트인 경우
        if not keywords_text:
            return []
        
        # 쉼표로 구분된 키워드 또는 줄바꿈으로 구분된 키워드
        if "," in keywords_text:
            # 쉼표로 구분
            keywords = [k.strip() for k in keywords_text.split(",") if k.strip()]
        else:
            # 줄바꿈으로 구분
            keywords = [k.strip() for k in keywords_text.splitlines() if k.strip()]
        
        # 중복 제거 및 정렬
        keywords = sorted(list(set(keywords)))
        
        return keywords
    
    def start_keyword_crawling(self):
        """키워드 수집 크롤링 시작"""
        if self.is_keyword_crawling:
            return
        
        # 키워드 준비
        keywords = self.process_keywords_text()
        file_path = self.keyword_file_var.get().strip()
        
        # 키워드 또는 파일 중 하나는 있어야 함
        if not keywords and not file_path:
            messagebox.showerror("오류", "키워드를 입력하거나 키워드 파일을 선택하세요.")
            return
        
        # 결과 파일 경로
        output_path = self.keyword_output_var.get().strip()
        if not output_path:
            messagebox.showerror("오류", "결과 저장 경로를 지정하세요.")
            return
        
        # 결과 폴더 생성
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # 브라우저 표시 여부
        show_browser = self.show_browser_var.get()
        
        # UI 비활성화
        self.is_keyword_crawling = True
        self.start_keyword_button["state"] = tk.DISABLED
        
        # 로그 초기화
        self.keyword_log_text.config(state=tk.NORMAL)
        self.keyword_log_text.delete(1.0, tk.END)
        self.keyword_log_text.config(state=tk.DISABLED)
        
        # 상태 업데이트
        self.keyword_status_var.set("크롤링 시작...")
        
        # 크롤링 스레드 시작
        self.keyword_crawler_thread = threading.Thread(
            target=self.run_keyword_crawler,
            args=(keywords, file_path, output_path, show_browser)
        )
        self.keyword_crawler_thread.daemon = True
        self.keyword_crawler_thread.start()
    
    def run_keyword_crawler(self, keywords, file_path, output_path, show_browser):
        """키워드 크롤러 실행 스레드"""
        try:
            # 파일에서 키워드를 읽는 경우
            if file_path and not keywords:
                # 파일에서 키워드 로드
                self.add_keyword_log(f"파일에서 키워드를 로드합니다: {file_path}")
                
                # 파일 형식에 따라 처리
                if file_path.endswith((".xlsx", ".xls")):
                    # Excel 파일
                    try:
                        df = pd.read_excel(file_path)
                        if not df.empty and len(df.columns) > 0:
                            keywords = df.iloc[:, 0].dropna().astype(str).tolist()
                    except Exception as e:
                        self.add_keyword_log(f"Excel 파일 로드 오류: {e}")
                        messagebox.showerror("오류", f"Excel 파일 로드 오류: {e}")
                        self.keyword_status_var.set("오류 발생")
                        self.start_keyword_button["state"] = tk.NORMAL
                        self.is_keyword_crawling = False
                        return
                
                elif file_path.endswith(".csv"):
                    # CSV 파일
                    try:
                        df = pd.read_csv(file_path)
                        if not df.empty and len(df.columns) > 0:
                            keywords = df.iloc[:, 0].dropna().astype(str).tolist()
                    except Exception as e:
                        self.add_keyword_log(f"CSV 파일 로드 오류: {e}")
                        messagebox.showerror("오류", f"CSV 파일 로드 오류: {e}")
                        self.keyword_status_var.set("오류 발생")
                        self.start_keyword_button["state"] = tk.NORMAL
                        self.is_keyword_crawling = False
                        return
                
                else:
                    # 텍스트 파일
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read().strip()
                            if "," in content:
                                keywords = [k.strip() for k in content.split(",") if k.strip()]
                            else:
                                keywords = [k.strip() for k in content.splitlines() if k.strip()]
                    except Exception as e:
                        self.add_keyword_log(f"텍스트 파일 로드 오류: {e}")
                        messagebox.showerror("오류", f"텍스트 파일 로드 오류: {e}")
                        self.keyword_status_var.set("오류 발생")
                        self.start_keyword_button["state"] = tk.NORMAL
                        self.is_keyword_crawling = False
                        return
            
            # 키워드가 없으면 종료
            if not keywords:
                self.add_keyword_log("키워드가 없습니다.")
                messagebox.showerror("오류", "키워드가 없습니다.")
                self.keyword_status_var.set("오류 발생")
                self.start_keyword_button["state"] = tk.NORMAL
                self.is_keyword_crawling = False
                return
            
            # 중복 제거 및 정렬
            keywords = sorted(list(set(keywords)))
            
            # 키워드 목록 로그 출력
            self.add_keyword_log(f"총 {len(keywords)}개 키워드 처리 예정:")
            for i, keyword in enumerate(keywords[:10], 1):
                self.add_keyword_log(f"{i}. {keyword}")
            if len(keywords) > 10:
                self.add_keyword_log(f"외 {len(keywords)-10}개...")
            
            # NaverSearchCrawler 인스턴스 생성
            self.add_keyword_log("크롤러를 초기화하는 중...")
            crawler = self.frames["keyword"]["crawler"](headless=not show_browser)
            
            # 현재 날짜와 시간을 파일명에 추가
            now = datetime.now()
            timestamp = now.strftime("%Y%m%d_%H%M%S")
            
            # 출력 경로 설정
            output_dir = os.path.dirname(output_path)
            file_name = f"keyword_result_{timestamp}"
            
            # 파일 확장자 확인
            if output_path.endswith(".csv"):
                file_ext = ".csv"
                result_format = "csv"
            else:
                file_ext = ".xlsx"
                result_format = "excel"
            
            # 최종 출력 파일 경로
            final_output_path = os.path.join(output_dir, file_name + file_ext)
            
            # 키워드 처리
            results = []
            all_content_data = []  # 모든 콘텐츠 데이터 저장 (결과창에 표시용)
            
            for i, keyword in enumerate(keywords, 1):
                if not self.is_keyword_crawling:  # 취소 확인
                    break
                
                self.add_keyword_log(f"[{i}/{len(keywords)}] '{keyword}' 처리 중...")
                self.keyword_status_var.set(f"'{keyword}' 처리 중 ({i}/{len(keywords)})")
                
                try:
                    # 키워드 분석
                    result = crawler.analyze_search_result(keyword)
                    if result is not None:
                        # 데이터프레임인지 확인하고 아니면 변환
                        if not isinstance(result, pd.DataFrame):
                            # 딕셔너리 결과가 반환된 경우 처리
                            if isinstance(result, dict):
                                result_df = pd.DataFrame([result])
                            else:
                                # 리스트 형태인 경우
                                result_df = pd.DataFrame(result)
                        else:
                            result_df = result
                        
                        # 키워드 정보 추가
                        result_df['검색어'] = keyword
                        
                        # 결과 리스트에 추가
                        results.append(result_df)
                        
                        # 결과창에 표시할 데이터 수집
                        if '인기글_컨텐츠' in result and isinstance(result['인기글_컨텐츠'], list):
                            for content_item in result['인기글_컨텐츠']:
                                content_data = {
                                    '키워드': keyword,
                                    '컨텐츠 유형': content_item.get('컨텐츠_유형', ''),
                                    '제목': content_item.get('제목', ''),
                                    '순번': content_item.get('순번', ''),
                                    '작성일': content_item.get('작성일', ''),
                                    '조회수': content_item.get('조회수', ''),
                                    'URL': content_item.get('URL', '')
                                }
                                all_content_data.append(content_data)
                        else:
                            # 기본 결과 구조인 경우 
                            content_data = {
                                '키워드': keyword,
                                '컨텐츠 유형': result.get('컨텐츠_유형', ''),
                                '제목': result.get('제목', ''),
                                '순번': '',
                                '작성일': '',
                                '조회수': '',
                                'URL': result.get('URL', '')
                            }
                            all_content_data.append(content_data)
                        
                        self.add_keyword_log(f"[{i}/{len(keywords)}] '{keyword}' 처리 완료")
                    else:
                        self.add_keyword_log(f"[{i}/{len(keywords)}] '{keyword}'에 대한 결과가 없습니다.")
                
                except Exception as e:
                    self.add_keyword_log(f"[{i}/{len(keywords)}] '{keyword}' 처리 중 오류: {e}")
                    continue
            
            # 크롤러 종료
            crawler.close()
            
            # 결과 저장
            if results:
                try:
                    # 결과 데이터프레임 생성 - 결과창에 표시되는 형식과 동일하게
                    columns = ['번호', '검색어', '유형', '제목', '순위', '작성일', '조회수', 'URL']
                    
                    # 결과 데이터 정리
                    result_rows = []
                    for i, item in enumerate(all_content_data, 1):
                        # 컨텐츠 유형 표준화
                        content_type = item.get('컨텐츠 유형', '')
                        simplified_type = "기타"
                        
                        if '블로그' in content_type.lower():
                            simplified_type = "블로그"
                        elif '카페' in content_type.lower():
                            simplified_type = "카페"
                        elif '포스트' in content_type.lower():
                            simplified_type = "포스트"
                        elif '웹' in content_type.lower() or '웹사이트' in content_type.lower():
                            simplified_type = "웹페이지"
                        elif '뉴스' in content_type.lower() or '기사' in content_type.lower():
                            simplified_type = "뉴스"
                        elif '지식' in content_type.lower():
                            simplified_type = "지식iN"
                        
                        row = {
                            '번호': i,
                            '검색어': item.get('키워드', ''),
                            '유형': simplified_type,
                            '제목': item.get('제목', ''),
                            '순위': item.get('순번', ''),
                            '작성일': item.get('작성일', ''),
                            '조회수': item.get('조회수', ''),
                            'URL': item.get('URL', '')
                        }
                        result_rows.append(row)
                    
                    # 결과창에 표시되는 형식과 동일한 DataFrame 생성
                    result_df = pd.DataFrame(result_rows, columns=columns)
                    
                    # 기본은 엑셀 파일로 저장
                    excel_output_path = os.path.join(output_dir, file_name + ".xlsx")
                    result_df.to_excel(excel_output_path, index=False, engine='openpyxl')
                    self.add_keyword_log(f"Excel 결과 파일이 저장되었습니다: {excel_output_path}")
                    
                    # CSV 파일도 저장
                    if result_format == "csv":
                        csv_output_path = os.path.join(output_dir, file_name + ".csv")
                        result_df.to_csv(csv_output_path, index=False, encoding='utf-8-sig')
                        self.add_keyword_log(f"CSV 결과 파일도 저장되었습니다: {csv_output_path}")
                    
                    total_results = len(result_df)
                    self.add_keyword_log(f"총 {total_results}개 결과가 저장되었습니다.")
                    
                    # 결과창 표시 (Excel 파일 경로로 전달)
                    self.show_results_window(all_content_data, excel_output_path)
                    
                    messagebox.showinfo("완료", f"크롤링이 완료되었습니다.\n총 {total_results}개 결과가 저장되었습니다.")
                except Exception as e:
                    self.add_keyword_log(f"결과 저장 중 오류 발생: {e}")
                    messagebox.showerror("오류", f"결과 저장 중 오류 발생: {e}")
            else:
                self.add_keyword_log("저장할 결과가 없습니다.")
                messagebox.showinfo("완료", "크롤링이 완료되었으나 저장할 결과가 없습니다.")
        
        except Exception as e:
            self.add_keyword_log(f"크롤링 중 오류 발생: {e}")
            messagebox.showerror("오류", f"크롤링 중 오류 발생: {e}")
        
        finally:
            # UI 상태 복원
            self.keyword_status_var.set("준비됨")
            self.start_keyword_button["state"] = tk.NORMAL
            self.is_keyword_crawling = False
    
    def show_results_window(self, results_data, output_path):
        """결과 표시 창 생성"""
        # 결과 창 생성
        results_window = tk.Toplevel(self.root)
        results_window.title("크롤링 결과")
        results_window.geometry("900x600")
        
        # 상단 정보 프레임
        info_frame = ttk.Frame(results_window, padding=10)
        info_frame.pack(fill=tk.X)
        
        ttk.Label(info_frame, text=f"저장 경로: {output_path}").pack(side=tk.LEFT)
        
        ttk.Button(
            info_frame,
            text="결과 파일 열기",
            command=lambda: self.open_result_file(output_path)
        ).pack(side=tk.RIGHT)
        
        # 탭 컨트롤 추가
        tab_control = ttk.Notebook(results_window)
        tab_control.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 검색 결과 탭
        results_tab = ttk.Frame(tab_control)
        tab_control.add(results_tab, text="크롤링 결과")
        
        # 요약 정보 탭
        summary_tab = ttk.Frame(tab_control)
        tab_control.add(summary_tab, text="요약 정보")
        
        # 결과 테이블 프레임 (크롤링 결과 탭에 추가)
        table_frame = ttk.Frame(results_tab, padding=5)
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # 결과 테이블 생성 (컬럼 수정)
        columns = ('번호', '검색어', '유형', '제목', '순위', '작성일', '조회수', 'URL')
        tree = ttk.Treeview(table_frame, columns=columns, show='headings')
        
        # 열 설정
        for col in columns:
            tree.heading(col, text=col)
            
            # 열 너비 설정
            if col == '번호':
                tree.column(col, width=50, anchor=tk.CENTER)
            elif col == '검색어':
                tree.column(col, width=100)
            elif col == '유형':
                tree.column(col, width=80)
            elif col == '제목':
                tree.column(col, width=250)
            elif col == '순위':
                tree.column(col, width=50, anchor=tk.CENTER)
            elif col == '작성일':
                tree.column(col, width=80, anchor=tk.CENTER)
            elif col == '조회수':
                tree.column(col, width=80, anchor=tk.CENTER)
            elif col == 'URL':
                tree.column(col, width=150)
        
        # 스크롤바 추가
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 수평 스크롤바 추가
        h_scrollbar = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(xscroll=h_scrollbar.set)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # 항목 추가 (데이터 구조에 맞게 수정)
        for i, item in enumerate(results_data, 1):
            # 컨텐츠 유형 표준화
            content_type = item.get('컨텐츠 유형', '')
            simplified_type = "기타"
            
            if '블로그' in content_type.lower():
                simplified_type = "블로그"
            elif '카페' in content_type.lower():
                simplified_type = "카페"
            elif '포스트' in content_type.lower():
                simplified_type = "포스트"
            elif '웹' in content_type.lower() or '웹사이트' in content_type.lower():
                simplified_type = "웹페이지"
            elif '뉴스' in content_type.lower() or '기사' in content_type.lower():
                simplified_type = "뉴스"
            elif '지식' in content_type.lower():
                simplified_type = "지식iN"
            
            # 항목 확인 및 기본값 설정
            values = (
                i,
                item.get('키워드', ''),
                simplified_type,
                item.get('제목', ''),
                item.get('순번', ''),
                item.get('작성일', ''),
                item.get('조회수', ''),
                item.get('URL', '')
            )
            
            # 트리뷰에 항목 추가 (URL을 태그로 저장)
            item_id = tree.insert('', tk.END, values=values, tags=(item.get('URL', '')))
        
        # URL 클릭 이벤트 연결
        tree.bind('<Double-1>', lambda event: self.open_url_from_tree(event, tree))
        
        # 요약 정보 탭 내용
        summary_frame = ttk.Frame(summary_tab, padding=10)
        summary_frame.pack(fill=tk.BOTH, expand=True)
        
        # 검색어별 통계
        keywords = sorted(set([item.get('키워드', '') for item in results_data]))
        
        ttk.Label(
            summary_frame, 
            text="검색 결과 요약", 
            font=('Helvetica', 14, 'bold')
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # 요약 표시
        ttk.Label(
            summary_frame,
            text=f"• 총 검색어 수: {len(keywords)}개"
        ).pack(anchor=tk.W, pady=2)
        
        ttk.Label(
            summary_frame,
            text=f"• 총 검색 결과 수: {len(results_data)}개"
        ).pack(anchor=tk.W, pady=2)
        
        # 컨텐츠 유형 별 통계
        content_types = {}
        for item in results_data:
            content_type = item.get('컨텐츠 유형', '')
            simplified_type = "기타"
            
            if '블로그' in content_type.lower():
                simplified_type = "블로그"
            elif '카페' in content_type.lower():
                simplified_type = "카페"
            elif '포스트' in content_type.lower():
                simplified_type = "포스트"
            elif '웹' in content_type.lower() or '웹사이트' in content_type.lower():
                simplified_type = "웹페이지"
            elif '뉴스' in content_type.lower() or '기사' in content_type.lower():
                simplified_type = "뉴스"
            elif '지식' in content_type.lower():
                simplified_type = "지식iN"
                
            content_types[simplified_type] = content_types.get(simplified_type, 0) + 1
        
        ttk.Label(
            summary_frame,
            text="컨텐츠 유형별 결과:",
            font=('Helvetica', 12, 'bold')
        ).pack(anchor=tk.W, pady=(10, 5))
        
        for type_name, count in sorted(content_types.items(), key=lambda x: x[1], reverse=True):
            ttk.Label(
                summary_frame,
                text=f"• {type_name}: {count}개"
            ).pack(anchor=tk.W, pady=1)
        
        # 검색어별 결과 요약
        ttk.Label(
            summary_frame,
            text="검색어별 결과:",
            font=('Helvetica', 12, 'bold')
        ).pack(anchor=tk.W, pady=(10, 5))
        
        # 검색어별 결과 스크롤 영역
        summary_scroll = ttk.Frame(summary_frame)
        summary_scroll.pack(fill=tk.BOTH, expand=True, pady=5)
        
        keyword_text = tk.Text(summary_scroll, wrap=tk.WORD, height=10)
        keyword_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        keyword_scroll = ttk.Scrollbar(summary_scroll, command=keyword_text.yview)
        keyword_text.configure(yscrollcommand=keyword_scroll.set)
        keyword_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 검색어별 결과 추가
        for keyword in keywords:
            keyword_results = [item for item in results_data if item.get('키워드', '') == keyword]
            keyword_text.insert(tk.END, f"- '{keyword}': {len(keyword_results)}개 결과\n")
        
        keyword_text.config(state=tk.DISABLED)
        
        # 상태 표시줄
        status_frame = ttk.Frame(results_window, padding=(10, 5))
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        ttk.Label(
            status_frame, 
            text=f"총 {len(results_data)}개 항목 | 더블 클릭: 원본 페이지 열기"
        ).pack(side=tk.LEFT)
    
    def open_url_from_tree(self, event, tree):
        """트리뷰 항목 더블 클릭 시 URL 열기"""
        # 선택한 항목 식별
        item_id = tree.identify('item', event.x, event.y)
        if not item_id:
            return
            
        # 선택한 항목의 URL 가져오기 (태그에 저장됨)
        url = tree.item(item_id, 'tags')[0]
        if url:
            # URL 열기
            import webbrowser
            webbrowser.open(url)
    
    def open_result_file(self, file_path):
        """결과 파일 열기"""
        if not os.path.exists(file_path):
            messagebox.showerror("오류", "파일을 찾을 수 없습니다.")
            return
            
        # 운영체제에 따라 파일 열기
        if sys.platform == "win32":
            os.startfile(file_path)
        elif sys.platform == "darwin":  # macOS
            import subprocess
            subprocess.run(['open', file_path])
        else:  # Linux
            import subprocess
            subprocess.run(['xdg-open', file_path])
    
    def paste_keyword_text(self, event):
        """키워드 텍스트 붙여넣기"""
        self.keywords_text.event_generate("<<Paste>>")
        return "break"
    
    def copy_keyword_text(self, event):
        """키워드 텍스트 복사"""
        self.keywords_text.event_generate("<<Copy>>")
        return "break"
    
    def cut_keyword_text(self, event):
        """키워드 텍스트 자르기"""
        self.keywords_text.event_generate("<<Cut>>")
        return "break"
    
    def select_all_keyword_text(self, event):
        """키워드 텍스트 전체 선택"""
        self.keywords_text.tag_add(tk.SEL, "1.0", tk.END)
        self.keywords_text.mark_set(tk.INSERT, "1.0")
        self.keywords_text.see(tk.INSERT)
        return "break"
    
    def refresh(self):
        """프로그램 새로고침"""
        self.logger.info("새로고침을 수행합니다.")
        self.status_var.set("새로고침 중...")
        
        # 현재 프레임이 구매평 수집기 프레임인 경우 새로고침
        if self.current_frame and isinstance(self.current_frame, dict):
            if "review_collector" in self.frames and self.current_frame == self.frames["review_collector"]:
                for tab_name, tab in self.frames["review_collector"]["tabs"].items():
                    tab.refresh()
        
        self.status_var.set("새로고침 완료")
    
    def show_help(self):
        """도움말 표시"""
        help_text = """
네이버 크롤러 사용법:

1. 카페 외부노출 키워드 찾기:
   - 네이버 검색 시 노출되는 카페/블로그 인기글을 수집합니다.
   - 단일 키워드 또는 다중 키워드 입력 지원
   - 결과는 Excel(.xlsx) 파일로 저장됩니다.

2. 구매평 수집기:
   - 쇼핑몰 상품 구매평을 수집하고 감성 분석, 워드클라우드를 생성합니다.
        """
        messagebox.showinfo("사용법", help_text)
    
    def show_about(self):
        """프로그램 정보 표시"""
        about_text = """
네이버 크롤러 v1.0

- 네이버 쇼핑 검색 결과 크롤링
- 네이버 쇼핑 상품 구매평 수집
- 구매평 감성 분석 및 워드클라우드 생성

개발자: 사용자
        """
        messagebox.showinfo("정보", about_text)


def main():
    """메인 함수"""
    root = tk.Tk()
    app = NaverCrawlerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main() 