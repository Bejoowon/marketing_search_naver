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
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# 모듈 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 모듈 임포트
from modules.review_crawler.review_analyzer import ReviewAnalyzer


class WordcloudTab:
    """워드클라우드 탭 클래스"""
    
    def __init__(self, parent, logger):
        """초기화"""
        self.parent = parent
        self.logger = logger
        self.analyzer = None
        self.wordcloud_positive = None
        self.wordcloud_negative = None
        self.is_generating = False
        
        # 프레임 생성
        self.frame = ttk.Frame(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        # 메인 프레임
        main_frame = ttk.Frame(self.frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 상단 프레임 (입력 부분)
        top_frame = ttk.LabelFrame(main_frame, text="워드클라우드 설정", padding=10)
        top_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 파일 선택 프레임
        file_frame = ttk.Frame(top_frame)
        file_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(file_frame, text="분석 결과 파일:").pack(side=tk.LEFT)
        self.input_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.input_file_var, width=50).pack(
            side=tk.LEFT, padx=5, fill=tk.X, expand=True
        )
        ttk.Button(
            file_frame, 
            text="파일 선택", 
            command=self.select_input_file
        ).pack(side=tk.LEFT)
        
        # 워드클라우드 옵션 프레임
        options_frame = ttk.Frame(top_frame)
        options_frame.pack(fill=tk.X, pady=5)
        
        # 배경색 선택
        ttk.Label(options_frame, text="배경색:").pack(side=tk.LEFT, padx=(0, 5))
        self.background_var = tk.StringVar(value="white")
        ttk.Combobox(
            options_frame, 
            textvariable=self.background_var, 
            values=["white", "black", "lightblue", "lightgreen"],
            width=10
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # 최대 단어 수
        ttk.Label(options_frame, text="최대 단어 수:").pack(side=tk.LEFT, padx=(0, 5))
        self.max_words_var = tk.IntVar(value=100)
        ttk.Spinbox(
            options_frame, 
            from_=10, 
            to=500, 
            increment=10, 
            textvariable=self.max_words_var,
            width=5
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        # 최소 빈도
        ttk.Label(options_frame, text="최소 빈도:").pack(side=tk.LEFT, padx=(0, 5))
        self.min_freq_var = tk.IntVar(value=1)
        ttk.Spinbox(
            options_frame, 
            from_=1, 
            to=50, 
            increment=1, 
            textvariable=self.min_freq_var,
            width=5
        ).pack(side=tk.LEFT)
        
        # 버튼 프레임
        button_frame = ttk.Frame(top_frame)
        button_frame.pack(fill=tk.X, pady=5)
        
        self.generate_button = ttk.Button(
            button_frame, 
            text="워드클라우드 생성", 
            command=self.generate_wordcloud
        )
        self.generate_button.pack(side=tk.LEFT, padx=(0, 5))
        
        self.save_button = ttk.Button(
            button_frame, 
            text="이미지 저장", 
            command=self.save_wordcloud_images,
            state=tk.DISABLED
        )
        self.save_button.pack(side=tk.LEFT)
        
        # 오른쪽 프레임 (결과 부분)
        right_frame = ttk.LabelFrame(main_frame, text="생성 정보", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 노트북 탭 컨트롤 추가 (로그/결과)
        self.tab_control = ttk.Notebook(right_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # 로그 탭
        self.log_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.log_tab, text="실행 로그")
        
        # 워드클라우드 탭
        self.wordcloud_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.wordcloud_tab, text="워드클라우드")
        
        # 로그 텍스트 영역
        self.log_text = ScrolledText(self.log_tab, width=50, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 워드클라우드 결과 영역
        self.wordcloud_frame = ttk.Frame(self.wordcloud_tab)
        self.wordcloud_frame.pack(fill=tk.BOTH, expand=True)
        
        # 긍정/부정 탭 컨트롤
        self.result_tabs = ttk.Notebook(self.wordcloud_frame)
        self.result_tabs.pack(fill=tk.BOTH, expand=True)
        
        # 긍정 워드클라우드 프레임
        self.positive_frame = ttk.Frame(self.result_tabs)
        self.result_tabs.add(self.positive_frame, text="긍정 워드클라우드")
        
        # 부정 워드클라우드 프레임
        self.negative_frame = ttk.Frame(self.result_tabs)
        self.result_tabs.add(self.negative_frame, text="부정 워드클라우드")
        
        # 워드클라우드 이미지 객체 초기화
        self.wordcloud_positive = None
        self.wordcloud_negative = None
        
        # 워드클라우드 이미지 저장 버튼
        self.save_frame = ttk.Frame(self.wordcloud_tab)
        self.save_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(
            self.save_frame, 
            text="긍정 워드클라우드 저장", 
            command=lambda: self.save_wordcloud_image("positive")
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            self.save_frame, 
            text="부정 워드클라우드 저장", 
            command=lambda: self.save_wordcloud_image("negative")
        ).pack(side=tk.LEFT)
        
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
        
        # 현재 워드클라우드 정보를 위한 변수
        self.current_file = None
        self.all_pos_words = []
        self.all_neg_words = []
    
    def select_input_file(self):
        """입력 파일 선택"""
        file_path = filedialog.askopenfilename(
            title="분석 결과 파일 선택",
            filetypes=[
                ("엑셀 파일", "*.xlsx *.xls"),
                ("CSV 파일", "*.csv"),
                ("모든 파일", "*.*")
            ]
        )
        
        if file_path:
            self.input_file_var.set(file_path)
    
    def generate_wordcloud(self):
        """워드클라우드 생성"""
        input_file = self.input_file_var.get()
        
        if not input_file:
            messagebox.showerror("오류", "분석 결과 파일을 선택해주세요.")
            return
        
        if not os.path.exists(input_file):
            messagebox.showerror("오류", f"파일을 찾을 수 없습니다: {input_file}")
            return
        
        # UI 상태 업데이트
        self.is_generating = True
        self.generate_button.config(state=tk.DISABLED)
        self.save_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_label_var.set("0%")
        
        # 기존 워드클라우드 캔버스 제거
        for widget in self.positive_frame.winfo_children():
            widget.destroy()
        for widget in self.negative_frame.winfo_children():
            widget.destroy()
        
        # 옵션 가져오기
        background_color = self.background_var.get()
        max_words = self.max_words_var.get()
        min_freq = self.min_freq_var.get()
        
        # 별도 스레드에서 워드클라우드 생성
        threading.Thread(
            target=self._wordcloud_thread,
            args=(input_file, background_color, max_words, min_freq),
            daemon=True
        ).start()
    
    def _wordcloud_thread(self, input_file, background_color, max_words, min_freq):
        """워드클라우드 생성 스레드 함수"""
        try:
            # 진행 상태 업데이트
            self.update_progress(10, "파일 읽는 중...")
            
            # 분석기 생성
            if not self.analyzer:
                self.analyzer = ReviewAnalyzer()
            
            # 파일 읽기
            if input_file.endswith('.xlsx') or input_file.endswith('.xls'):
                df = pd.read_excel(input_file)
            else:
                df = pd.read_csv(input_file, encoding='utf-8-sig')
            
            # 긍정/부정 단어 컬럼 확인
            if '긍정단어' not in df.columns or '부정단어' not in df.columns:
                # 분석 결과가 아닌 경우 분석 수행
                self.update_progress(20, "감성 분석 중...")
                df = self.analyzer.analyze_reviews_from_file(input_file)
                
                if df is None:
                    raise Exception("파일 분석 중 오류가 발생했습니다.")
            
            # 모든 긍정/부정 단어 수집
            self.update_progress(40, "단어 추출 중...")
            self.all_pos_words = []
            self.all_neg_words = []
            
            for pos_word_list in df['긍정단어'].dropna():
                if pos_word_list:
                    words = [w.strip() for w in pos_word_list.split(';') if w.strip()]
                    self.all_pos_words.extend(words)
            
            for neg_word_list in df['부정단어'].dropna():
                if neg_word_list:
                    words = [w.strip() for w in neg_word_list.split(';') if w.strip()]
                    self.all_neg_words.extend(words)
            
            # 최소 빈도 필터링
            from collections import Counter
            pos_counter = Counter(self.all_pos_words)
            neg_counter = Counter(self.all_neg_words)
            
            filtered_pos_words = {word: count for word, count in pos_counter.items() if count >= min_freq}
            filtered_neg_words = {word: count for word, count in neg_counter.items() if count >= min_freq}
            
            # 긍정 워드클라우드 생성
            self.update_progress(60, "긍정 워드클라우드 생성 중...")
            if filtered_pos_words:
                self.wordcloud_positive = self.analyzer.generate_wordcloud(
                    filtered_pos_words, 
                    width=800, 
                    height=400, 
                    background_color=background_color,
                    max_words=max_words
                )
            else:
                self.wordcloud_positive = None
            
            # 부정 워드클라우드 생성
            self.update_progress(80, "부정 워드클라우드 생성 중...")
            if filtered_neg_words:
                self.wordcloud_negative = self.analyzer.generate_wordcloud(
                    filtered_neg_words, 
                    width=800, 
                    height=400, 
                    background_color=background_color,
                    max_words=max_words
                )
            else:
                self.wordcloud_negative = None
            
            # 워드클라우드 표시
            self.update_progress(90, "워드클라우드 표시 중...")
            if self.wordcloud_positive or self.wordcloud_negative:
                # 메인 스레드에서 UI 업데이트 요청
                self.frame.after(0, self.display_wordclouds)
                self.current_file = input_file
            else:
                raise Exception("워드클라우드를 생성할 단어가 없습니다.")
            
            self.update_progress(100, "완료")
            
        except Exception as e:
            self.update_progress(0, "오류 발생")
            messagebox.showerror("오류", f"워드클라우드 생성 중 오류 발생: {str(e)}")
        
        finally:
            # UI 상태 업데이트
            self.is_generating = False
            self.generate_button.config(state=tk.NORMAL)
            if self.wordcloud_positive is not None or self.wordcloud_negative is not None:
                self.save_button.config(state=tk.NORMAL)
    
    def update_progress(self, value, message=None):
        """진행 상태 업데이트"""
        self.progress_var.set(value)
        
        if message:
            progress_text = f"{value}% ({message})"
        else:
            progress_text = f"{value}%"
            
        self.progress_label_var.set(progress_text)
    
    def display_wordclouds(self):
        """워드클라우드 이미지 표시"""
        # 긍정 워드클라우드 표시
        if self.wordcloud_positive:
            # matplotlib 그림 생성
            pos_fig = plt.Figure(figsize=(8, 4), dpi=100)
            pos_ax = pos_fig.add_subplot(111)
            pos_ax.imshow(self.wordcloud_positive, interpolation='bilinear')
            pos_ax.axis('off')
            pos_fig.tight_layout()
            
            # Tkinter 캔버스에 추가
            pos_canvas = FigureCanvasTkAgg(pos_fig, master=self.positive_frame)
            pos_canvas.draw()
            pos_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            # 워드클라우드 없음 메시지
            ttk.Label(
                self.positive_frame, 
                text="긍정 단어가 충분하지 않습니다.", 
                font=("Helvetica", 12)
            ).pack(expand=True)
        
        # 부정 워드클라우드 표시
        if self.wordcloud_negative:
            # matplotlib 그림 생성
            neg_fig = plt.Figure(figsize=(8, 4), dpi=100)
            neg_ax = neg_fig.add_subplot(111)
            neg_ax.imshow(self.wordcloud_negative, interpolation='bilinear')
            neg_ax.axis('off')
            neg_fig.tight_layout()
            
            # Tkinter 캔버스에 추가
            neg_canvas = FigureCanvasTkAgg(neg_fig, master=self.negative_frame)
            neg_canvas.draw()
            neg_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        else:
            # 워드클라우드 없음 메시지
            ttk.Label(
                self.negative_frame, 
                text="부정 단어가 충분하지 않습니다.", 
                font=("Helvetica", 12)
            ).pack(expand=True)
    
    def save_wordcloud_images(self):
        """워드클라우드 이미지 저장"""
        if not self.current_file:
            messagebox.showerror("오류", "저장할 워드클라우드가 없습니다.")
            return
        
        save_dir = filedialog.askdirectory(title="저장 폴더 선택")
        if not save_dir:
            return
        
        try:
            # 기본 파일명 생성
            base_name = os.path.splitext(os.path.basename(self.current_file))[0]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            saved_files = []
            
            # 긍정 워드클라우드 저장
            if self.wordcloud_positive:
                pos_file = os.path.join(save_dir, f"{base_name}_positive_{timestamp}.png")
                
                plt.figure(figsize=(10, 5))
                plt.imshow(self.wordcloud_positive, interpolation='bilinear')
                plt.axis('off')
                plt.tight_layout()
                plt.savefig(pos_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                saved_files.append(pos_file)
            
            # 부정 워드클라우드 저장
            if self.wordcloud_negative:
                neg_file = os.path.join(save_dir, f"{base_name}_negative_{timestamp}.png")
                
                plt.figure(figsize=(10, 5))
                plt.imshow(self.wordcloud_negative, interpolation='bilinear')
                plt.axis('off')
                plt.tight_layout()
                plt.savefig(neg_file, dpi=300, bbox_inches='tight')
                plt.close()
                
                saved_files.append(neg_file)
            
            if saved_files:
                messagebox.showinfo("저장 완료", f"워드클라우드 이미지가 저장되었습니다.\n{save_dir}")
            else:
                messagebox.showwarning("경고", "저장할 워드클라우드 이미지가 없습니다.")
            
        except Exception as e:
            messagebox.showerror("오류", f"이미지 저장 중 오류 발생: {str(e)}")
    
    def refresh(self):
        """UI 새로고침"""
        if not self.is_generating:
            # 기존 워드클라우드 캔버스 제거
            for widget in self.positive_frame.winfo_children():
                widget.destroy()
            for widget in self.negative_frame.winfo_children():
                widget.destroy()
            
            # 상태 초기화
            self.current_file = None
            self.wordcloud_positive = None
            self.wordcloud_negative = None
            self.all_pos_words = []
            self.all_neg_words = []
            
            # 버튼 상태 업데이트
            self.generate_button.config(state=tk.NORMAL)
            self.save_button.config(state=tk.DISABLED)
            
            # 진행 상태바 초기화
            self.progress_var.set(0)
            self.progress_label_var.set("0%") 

    def save_wordcloud_image(self, type):
        """워드클라우드 이미지 저장"""
        if type == "positive" and self.wordcloud_positive:
            file_path = filedialog.asksaveasfilename(
                title="긍정 워드클라우드 저장",
                defaultextension=".png",
                filetypes=[("PNG 이미지", "*.png"), ("모든 파일", "*.*")]
            )
            if file_path:
                self.wordcloud_positive.to_file(file_path)
                self.logger.add_log(f"긍정 워드클라우드 저장: {file_path}")
                messagebox.showinfo("저장 완료", f"긍정 워드클라우드가 저장되었습니다:\n{file_path}")
        
        elif type == "negative" and self.wordcloud_negative:
            file_path = filedialog.asksaveasfilename(
                title="부정 워드클라우드 저장",
                defaultextension=".png",
                filetypes=[("PNG 이미지", "*.png"), ("모든 파일", "*.*")]
            )
            if file_path:
                self.wordcloud_negative.to_file(file_path)
                self.logger.add_log(f"부정 워드클라우드 저장: {file_path}")
                messagebox.showinfo("저장 완료", f"부정 워드클라우드가 저장되었습니다:\n{file_path}")
        
        else:
            messagebox.showinfo("알림", "먼저 워드클라우드를 생성해야 합니다.") 