#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from datetime import datetime

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 모듈 임포트
from modules.review_crawler.naver_review_crawler import NaverReviewCrawler


class ReviewTab:
    """구매평 수집 탭 클래스"""
    
    def __init__(self, parent, logger):
        """초기화"""
        self.parent = parent
        self.logger = logger
        self.crawler = None
        self.is_crawling = False
        
        # 프레임 생성
        self.frame = ttk.Frame(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        # 메인 프레임
        main_frame = ttk.Frame(self.frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 왼쪽 프레임 (입력 부분)
        left_frame = ttk.LabelFrame(main_frame, text="수집 설정", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 입력 유형 선택
        input_type_frame = ttk.Frame(left_frame)
        input_type_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_type_frame, text="입력 유형:").pack(side=tk.LEFT)
        
        self.input_type_var = tk.StringVar(value="url")
        ttk.Radiobutton(
            input_type_frame, 
            text="단일 URL", 
            variable=self.input_type_var, 
            value="url",
            command=self.toggle_input_type
        ).pack(side=tk.LEFT, padx=(10, 5))
        
        ttk.Radiobutton(
            input_type_frame, 
            text="URL 목록 파일", 
            variable=self.input_type_var, 
            value="file",
            command=self.toggle_input_type
        ).pack(side=tk.LEFT, padx=5)
        
        # 단일 URL 입력
        self.url_frame = ttk.Frame(left_frame)
        self.url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(self.url_frame, text="상품 URL:").pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        self.url_entry = ttk.Entry(self.url_frame, textvariable=self.url_var, width=50)
        self.url_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 복사 붙여넣기 바인딩 추가
        self.url_entry.bind("<Control-v>", lambda e: self.paste_to_entry(e, self.url_entry))
        self.url_entry.bind("<Control-c>", lambda e: self.copy_from_entry(e, self.url_entry))
        self.url_entry.bind("<Control-x>", lambda e: self.cut_from_entry(e, self.url_entry))
        self.url_entry.bind("<Control-a>", lambda e: self.select_all_entry(e, self.url_entry))
        # macOS용 Command 키 바인딩 추가
        self.url_entry.bind("<Command-v>", lambda e: self.paste_to_entry(e, self.url_entry))
        self.url_entry.bind("<Command-c>", lambda e: self.copy_from_entry(e, self.url_entry))
        self.url_entry.bind("<Command-x>", lambda e: self.cut_from_entry(e, self.url_entry))
        self.url_entry.bind("<Command-a>", lambda e: self.select_all_entry(e, self.url_entry))
        
        # 파일 입력
        self.file_frame = ttk.Frame(left_frame)
        
        ttk.Label(self.file_frame, text="입력 파일:").pack(side=tk.LEFT)
        self.input_file_var = tk.StringVar()
        self.input_file_entry = ttk.Entry(self.file_frame, textvariable=self.input_file_var, width=40)
        self.input_file_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 입력 파일 필드에 복사 붙여넣기 바인딩 추가
        self.input_file_entry.bind("<Control-v>", lambda e: self.paste_to_entry(e, self.input_file_entry))
        self.input_file_entry.bind("<Control-c>", lambda e: self.copy_from_entry(e, self.input_file_entry))
        self.input_file_entry.bind("<Control-x>", lambda e: self.cut_from_entry(e, self.input_file_entry))
        self.input_file_entry.bind("<Control-a>", lambda e: self.select_all_entry(e, self.input_file_entry))
        # macOS용 Command 키 바인딩 추가
        self.input_file_entry.bind("<Command-v>", lambda e: self.paste_to_entry(e, self.input_file_entry))
        self.input_file_entry.bind("<Command-c>", lambda e: self.copy_from_entry(e, self.input_file_entry))
        self.input_file_entry.bind("<Command-x>", lambda e: self.cut_from_entry(e, self.input_file_entry))
        self.input_file_entry.bind("<Command-a>", lambda e: self.select_all_entry(e, self.input_file_entry))
        
        ttk.Button(
            self.file_frame, 
            text="파일 선택", 
            command=self.select_input_file
        ).pack(side=tk.LEFT)
        
        # 출력 설정
        output_frame = ttk.Frame(left_frame)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="출력 파일:").pack(side=tk.LEFT)
        self.output_file_var = tk.StringVar()
        self.output_file_var.set(os.path.join("results", "reviews", f"reviews_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"))
        self.output_file_entry = ttk.Entry(output_frame, textvariable=self.output_file_var, width=40)
        self.output_file_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        # 출력 파일 필드에 복사 붙여넣기 바인딩 추가
        self.output_file_entry.bind("<Control-v>", lambda e: self.paste_to_entry(e, self.output_file_entry))
        self.output_file_entry.bind("<Control-c>", lambda e: self.copy_from_entry(e, self.output_file_entry))
        self.output_file_entry.bind("<Control-x>", lambda e: self.cut_from_entry(e, self.output_file_entry))
        self.output_file_entry.bind("<Control-a>", lambda e: self.select_all_entry(e, self.output_file_entry))
        # macOS용 Command 키 바인딩 추가
        self.output_file_entry.bind("<Command-v>", lambda e: self.paste_to_entry(e, self.output_file_entry))
        self.output_file_entry.bind("<Command-c>", lambda e: self.copy_from_entry(e, self.output_file_entry))
        self.output_file_entry.bind("<Command-x>", lambda e: self.cut_from_entry(e, self.output_file_entry))
        self.output_file_entry.bind("<Command-a>", lambda e: self.select_all_entry(e, self.output_file_entry))
        
        ttk.Button(
            output_frame, 
            text="파일 선택", 
            command=self.select_output_file
        ).pack(side=tk.LEFT)
        
        # 옵션 설정
        options_frame = ttk.Frame(left_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        self.headless_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            options_frame, 
            text="헤드리스 모드 (화면에 표시하지 않음)", 
            variable=self.headless_var
        ).pack(side=tk.LEFT)
        
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
        
        # 초기 UI 상태 설정
        self.toggle_input_type()
    
    def toggle_input_type(self):
        """입력 유형에 따른 UI 토글"""
        input_type = self.input_type_var.get()
        
        if input_type == "url":
            self.file_frame.pack_forget()
            self.url_frame.pack(fill=tk.X, pady=5, after=self.url_frame.master.winfo_children()[0])
        else:
            self.url_frame.pack_forget()
            self.file_frame.pack(fill=tk.X, pady=5, after=self.file_frame.master.winfo_children()[0])
    
    def select_input_file(self):
        """입력 파일 선택"""
        file_path = filedialog.askopenfilename(
            title="입력 파일 선택",
            filetypes=[
                ("엑셀 파일", "*.xlsx *.xls"),
                ("CSV 파일", "*.csv"),
                ("모든 파일", "*.*")
            ]
        )
        
        if file_path:
            self.input_file_var.set(file_path)
            
            # 출력 파일 이름도 자동 설정
            input_name = os.path.splitext(os.path.basename(file_path))[0]
            output_dir = os.path.dirname(self.output_file_var.get())
            self.output_file_var.set(
                os.path.join(output_dir, f"{input_name}_reviews.xlsx")
            )
    
    def select_output_file(self):
        """출력 파일 선택"""
        file_path = filedialog.asksaveasfilename(
            title="출력 파일 선택",
            defaultextension=".xlsx",
            filetypes=[
                ("엑셀 파일", "*.xlsx"),
                ("CSV 파일", "*.csv")
            ]
        )
        
        if file_path:
            self.output_file_var.set(file_path)
    
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
    
    def start_crawling(self):
        """크롤링 시작"""
        # 입력 검증
        input_type = self.input_type_var.get()
        
        if input_type == "url":
            url = self.url_var.get().strip()
            if not url:
                messagebox.showerror("오류", "상품 URL을 입력해주세요.")
                return
            
            # 크롤링 인자 설정
            kwargs = {
                "url": url,
                "output_file": self.output_file_var.get(),
                "headless": self.headless_var.get()
            }
            
        else:  # 파일 입력
            input_file = self.input_file_var.get()
            output_file = self.output_file_var.get()
            
            if not input_file:
                messagebox.showerror("오류", "입력 파일을 선택해주세요.")
                return
            
            if not output_file:
                messagebox.showerror("오류", "출력 파일을 선택해주세요.")
                return
            
            # 크롤링 인자 설정
            kwargs = {
                "input_file": input_file,
                "output_file": output_file,
                "headless": self.headless_var.get()
            }
        
        # 출력 디렉토리 생성
        output_dir = os.path.dirname(self.output_file_var.get())
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # UI 상태 업데이트
        self.is_crawling = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.progress_var.set(0)
        self.progress_label_var.set("0%")
        
        # 로그 초기화
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        
        self.add_log("수집을 시작합니다...")
        
        # 크롤러 인스턴스 생성 및 시작
        self.crawler = NaverReviewCrawler(headless=kwargs.get("headless", True))
        
        # 별도 스레드에서 크롤링 실행
        threading.Thread(
            target=self._crawling_thread,
            args=(input_type, kwargs),
            daemon=True
        ).start()
    
    def _crawling_thread(self, input_type, kwargs):
        """크롤링 스레드"""
        try:
            # 크롤러 초기화
            self.crawler = NaverReviewCrawler(headless=self.headless_var.get())
            self.add_log("크롤러가 초기화되었습니다.")
            
            # 진행 상태 초기화
            self.progress_var.set(0)
            self.progress_label_var.set("0%")
            
            # 결과 트리뷰 초기화
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            
            try:
                # 입력 유형에 따라 크롤링 실행
                if input_type == "url":
                    product_url = kwargs["url"]
                    output_file = kwargs["output_file"]
                    
                    self.add_log(f"상품 URL: {product_url}")
                    self.add_log(f"저장 파일: {output_file}")
                    
                    # 저장 폴더가 없으면 생성
                    output_dir = os.path.dirname(output_file)
                    if output_dir and not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    
                    # 진행상태 콜백 함수
                    def progress_callback(current, total, review_data=None):
                        if total > 0:
                            progress = (current / total) * 100
                            self.progress_var.set(progress)
                            self.progress_label_var.set(f"{progress:.1f}%")
                            
                            # 결과에 리뷰 추가
                            if review_data:
                                values = (
                                    current,
                                    review_data.get('작성자', ''),
                                    review_data.get('별점', ''),
                                    review_data.get('내용', '')[:100] + ('...' if len(review_data.get('내용', '')) > 100 else ''),
                                    review_data.get('작성일', ''),
                                    '있음' if review_data.get('이미지') else '없음'
                                )
                                item_id = self.result_tree.insert('', 'end', values=values)
                                self.result_tree.see(item_id)  # 스크롤 최신 항목으로
                    
                    # 크롤링 실행
                    result_df = self.crawler.collect_reviews(
                        product_url, 
                        progress_callback=progress_callback
                    )
                    
                    # 수집 완료 후 파일 저장
                    if result_df is not None and not result_df.empty:
                        # 파일 확장자에 따라 저장 형식 결정
                        if output_file.lower().endswith('.csv'):
                            result_df.to_csv(kwargs["output_file"], index=False, encoding='utf-8-sig')
                        else:
                            result_df.to_excel(kwargs["output_file"], index=False, engine='openpyxl')
                        
                        self.add_log(f"총 {len(result_df)}개의 구매평이 수집되어 '{output_file}'에 저장되었습니다.")
                        
                        # 결과 탭으로 이동
                        self.tab_control.select(1)  # 결과 탭으로 전환
                        
                        # GUI 스레드에서 messagebox 표시
                        self.parent.after(0, lambda: messagebox.showinfo("완료", f"총 {len(result_df)}개의 구매평이 성공적으로 수집되었습니다."))
                    else:
                        self.add_log("수집된 구매평이 없습니다.")
                else:
                    # 파일에서 URL 목록 읽기
                    input_file = kwargs["input_file"]
                    output_file = kwargs["output_file"]
                    
                    self.add_log(f"입력 파일: {input_file}")
                    self.add_log(f"저장 파일: {output_file}")
                    
                    # 저장 폴더가 없으면 생성
                    output_dir = os.path.dirname(output_file)
                    if output_dir and not os.path.exists(output_dir):
                        os.makedirs(output_dir)
                    
                    # 파일 형식에 따라 읽기
                    if input_file.lower().endswith(('.xlsx', '.xls')):
                        import pandas as pd
                        url_df = pd.read_excel(input_file)
                        
                        if not url_df.empty and len(url_df.columns) > 0:
                            urls = url_df.iloc[:, 0].dropna().tolist()
                        else:
                            urls = []
                    else:
                        # CSV 또는 텍스트 파일
                        with open(input_file, 'r', encoding='utf-8') as f:
                            urls = [line.strip() for line in f.readlines() if line.strip()]
                    
                    if not urls:
                        self.add_log("입력 파일에서 URL을 찾을 수 없습니다.")
                        return
                    
                    self.add_log(f"총 {len(urls)}개의 URL을 처리합니다.")
                    
                    # 모든 결과를 저장할 데이터프레임
                    import pandas as pd
                    all_results = pd.DataFrame()
                    
                    # 각 URL 처리
                    for idx, url in enumerate(urls, 1):
                        if not self.is_crawling:
                            self.add_log("크롤링이 중단되었습니다.")
                            break
                        
                        self.add_log(f"[{idx}/{len(urls)}] URL 처리 중: {url}")
                        
                        # 진행상태 콜백 함수
                        def progress_callback(current, total, review_data=None):
                            if total > 0:
                                overall_progress = ((idx - 1) + (current / total)) / len(urls) * 100
                                self.progress_var.set(overall_progress)
                                self.progress_label_var.set(f"{overall_progress:.1f}%")
                                
                                # 결과에 리뷰 추가
                                if review_data:
                                    values = (
                                        f"{idx}-{current}",
                                        review_data.get('작성자', ''),
                                        review_data.get('별점', ''),
                                        review_data.get('내용', '')[:100] + ('...' if len(review_data.get('내용', '')) > 100 else ''),
                                        review_data.get('작성일', ''),
                                        '있음' if review_data.get('이미지') else '없음'
                                    )
                                    item_id = self.result_tree.insert('', 'end', values=values)
                                    self.result_tree.see(item_id)  # 스크롤 최신 항목으로
                        
                            # 크롤링 중단 여부 확인
                            return self.is_crawling
                        
                        try:
                            # 크롤링 실행
                            result_df = self.crawler.collect_reviews(
                                url, 
                                progress_callback=progress_callback
                            )
                            
                            if result_df is not None and not result_df.empty:
                                # URL 정보 추가
                                result_df['상품URL'] = url
                                
                                # 전체 결과에 추가
                                all_results = pd.concat([all_results, result_df], ignore_index=True)
                                
                                self.add_log(f"[{idx}/{len(urls)}] {len(result_df)}개의 구매평 수집 완료")
                            else:
                                self.add_log(f"[{idx}/{len(urls)}] 수집된 구매평이 없습니다.")
                        except Exception as e:
                            self.add_log(f"[{idx}/{len(urls)}] 오류 발생: {str(e)}")
                    
                    # 전체 결과 저장
                    if not all_results.empty:
                        # 파일 확장자에 따라 저장 형식 결정
                        if output_file.lower().endswith('.csv'):
                            all_results.to_csv(output_file, index=False, encoding='utf-8-sig')
                        else:
                            all_results.to_excel(output_file, index=False, engine='openpyxl')
                        
                        self.add_log(f"총 {len(all_results)}개의 구매평이 수집되어 '{output_file}'에 저장되었습니다.")
                        
                        # 결과 탭으로 이동
                        self.tab_control.select(1)  # 결과 탭으로 전환
                        
                        # GUI 스레드에서 messagebox 표시
                        self.parent.after(0, lambda: messagebox.showinfo("완료", f"총 {len(all_results)}개의 구매평이 성공적으로 수집되었습니다."))
                    else:
                        self.add_log("수집된 구매평이 없습니다.")
            except Exception as e:
                self.add_log(f"오류 발생: {str(e)}")
                # GUI 스레드에서 messagebox 표시
                self.parent.after(0, lambda: messagebox.showerror("오류", f"크롤링 중 오류가 발생했습니다.\n{str(e)}"))
        finally:
            # 크롤러 종료
            if self.crawler:
                self.crawler.close()
                self.crawler = None
            
            # UI 상태 복원
            self.is_crawling = False
            self.parent.after(0, self.enable_ui)
    
    def stop_crawling(self):
        """크롤링 중단"""
        if self.is_crawling and self.crawler:
            self.add_log("수집을 중단합니다...")
            self.crawler.close()
            self.is_crawling = False
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
    
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