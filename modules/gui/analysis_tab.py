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
from modules.review_crawler.review_analyzer import ReviewAnalyzer


class AnalysisTab:
    """감성 분석 탭 클래스"""
    
    def __init__(self, parent, logger):
        """초기화"""
        self.parent = parent
        self.logger = logger
        self.analyzer = None
        self.is_analyzing = False
        self.analysis_results = None
        
        # 프레임 생성
        self.frame = ttk.Frame(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """UI 설정"""
        # 메인 프레임
        main_frame = ttk.Frame(self.frame, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 왼쪽 프레임 (입력/제어 부분)
        left_frame = ttk.LabelFrame(main_frame, text="분석 설정", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 입력 파일 선택
        input_frame = ttk.Frame(left_frame)
        input_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(input_frame, text="리뷰 파일:").pack(side=tk.LEFT)
        self.input_file_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.input_file_var, width=40).pack(
            side=tk.LEFT, padx=5, fill=tk.X, expand=True
        )
        ttk.Button(
            input_frame, 
            text="파일 선택", 
            command=self.select_input_file
        ).pack(side=tk.LEFT)
        
        # 출력 파일 선택
        output_frame = ttk.Frame(left_frame)
        output_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(output_frame, text="출력 파일:").pack(side=tk.LEFT)
        self.output_file_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_file_var, width=40).pack(
            side=tk.LEFT, padx=5, fill=tk.X, expand=True
        )
        ttk.Button(
            output_frame, 
            text="파일 선택", 
            command=self.select_output_file
        ).pack(side=tk.LEFT)
        
        # 분석 옵션
        options_frame = ttk.LabelFrame(left_frame, text="분석 옵션", padding=10)
        options_frame.pack(fill=tk.X, pady=10)
        
        # 사용자 정의 감성 단어 추가
        word_frame = ttk.Frame(options_frame)
        word_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(word_frame, text="단어 추가:").pack(side=tk.LEFT)
        self.sentiment_word_var = tk.StringVar()
        ttk.Entry(word_frame, textvariable=self.sentiment_word_var, width=20).pack(
            side=tk.LEFT, padx=5
        )
        
        self.sentiment_type_var = tk.StringVar(value="positive")
        ttk.Radiobutton(
            word_frame, 
            text="긍정", 
            variable=self.sentiment_type_var, 
            value="positive"
        ).pack(side=tk.LEFT, padx=(5, 0))
        
        ttk.Radiobutton(
            word_frame, 
            text="부정", 
            variable=self.sentiment_type_var, 
            value="negative"
        ).pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Button(
            word_frame, 
            text="추가", 
            command=self.add_sentiment_word
        ).pack(side=tk.LEFT)
        
        # 분석 시작 버튼
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_button = ttk.Button(
            button_frame, 
            text="분석 시작", 
            command=self.start_analysis
        )
        self.start_button.pack(side=tk.LEFT)
        
        # 오른쪽 프레임 (로그 및 결과 부분)
        right_frame = ttk.LabelFrame(main_frame, text="분석 정보", padding=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 노트북 탭 컨트롤 추가 (로그/결과)
        self.tab_control = ttk.Notebook(right_frame)
        self.tab_control.pack(fill=tk.BOTH, expand=True)
        
        # 로그 탭
        self.log_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.log_tab, text="실행 로그")
        
        # 결과 요약 탭
        self.summary_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.summary_tab, text="분석 요약")
        
        # 결과 상세 탭
        self.detail_tab = ttk.Frame(self.tab_control)
        self.tab_control.add(self.detail_tab, text="상세 결과")
        
        # 로그 텍스트 영역
        self.log_text = ScrolledText(self.log_tab, width=50, height=15, wrap=tk.WORD)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        self.log_text.config(state=tk.DISABLED)
        
        # 요약 정보 영역
        self.summary_frame = ttk.Frame(self.summary_tab, padding=5)
        self.summary_frame.pack(fill=tk.BOTH, expand=True)
        
        # 요약 텍스트 영역
        self.summary_text = ScrolledText(self.summary_frame, width=50, height=15, wrap=tk.WORD)
        self.summary_text.pack(fill=tk.BOTH, expand=True)
        self.summary_text.config(state=tk.DISABLED)
        
        # 상세 결과 트리뷰
        self.result_frame = ttk.Frame(self.detail_tab)
        self.result_frame.pack(fill=tk.BOTH, expand=True)
        
        # 트리뷰 열 정의
        columns = ("번호", "별점", "감성분석", "긍정단어", "부정단어")
        self.result_tree = ttk.Treeview(self.result_frame, columns=columns, show="headings")
        
        # 각 열 설정
        self.result_tree.column("번호", width=40, anchor=tk.CENTER)
        self.result_tree.column("별점", width=40, anchor=tk.CENTER)
        self.result_tree.column("감성분석", width=80, anchor=tk.CENTER)
        self.result_tree.column("긍정단어", width=200, anchor=tk.W)
        self.result_tree.column("부정단어", width=200, anchor=tk.W)
        
        # 헤더 설정
        self.result_tree.heading("번호", text="번호")
        self.result_tree.heading("별점", text="별점")
        self.result_tree.heading("감성분석", text="감성분석")
        self.result_tree.heading("긍정단어", text="긍정단어")
        self.result_tree.heading("부정단어", text="부정단어")
        
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
        
        # 감성 분석 결과에 색상 지정
        self.result_tree.tag_configure('positive', background='#E6F5E6')  # 연한 녹색
        self.result_tree.tag_configure('negative', background='#F5E6E6')  # 연한 빨간색
        self.result_tree.tag_configure('neutral', background='#F5F5F5')   # 연한 회색
        
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
    
    def select_input_file(self):
        """입력 파일 선택"""
        file_path = filedialog.askopenfilename(
            title="리뷰 파일 선택",
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
            input_dir = os.path.dirname(file_path)
            self.output_file_var.set(
                os.path.join(input_dir, f"{input_name}_analyzed.xlsx")
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
    
    def add_sentiment_word(self):
        """감성 사전에 단어 추가"""
        word = self.sentiment_word_var.get().strip()
        sentiment_type = self.sentiment_type_var.get()
        
        if not word:
            messagebox.showwarning("경고", "추가할 단어를 입력해주세요.")
            return
        
        if not self.analyzer:
            self.analyzer = ReviewAnalyzer()
        
        success = self.analyzer.add_sentiment_word(word, sentiment_type)
        
        if success:
            messagebox.showinfo("안내", f"'{word}'을(를) {sentiment_type} 사전에 추가했습니다.")
            self.sentiment_word_var.set("")  # 입력 필드 초기화
        else:
            messagebox.showwarning("경고", f"'{word}'을(를) 추가하는데 실패했습니다. 이미 존재하거나 오류가 발생했습니다.")
    
    def start_analysis(self):
        """감성 분석 시작"""
        input_file = self.input_file_var.get()
        output_file = self.output_file_var.get()
        
        if not input_file:
            messagebox.showerror("오류", "분석할 리뷰 파일을 선택해주세요.")
            return
        
        if not output_file:
            messagebox.showerror("오류", "결과를 저장할 파일을 선택해주세요.")
            return
        
        # 출력 디렉토리 생성
        output_dir = os.path.dirname(output_file)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # UI 상태 업데이트
        self.is_analyzing = True
        self.start_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.progress_label_var.set("0%")
        
        # 결과 테이블 초기화
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # 요약 텍스트 초기화
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.config(state=tk.DISABLED)
        
        # 분석기 생성
        if not self.analyzer:
            self.analyzer = ReviewAnalyzer()
        
        # 별도 스레드에서 분석 실행
        threading.Thread(
            target=self._analysis_thread,
            args=(input_file, output_file),
            daemon=True
        ).start()
    
    def _analysis_thread(self, input_file, output_file):
        """분석 스레드 함수"""
        try:
            self.add_log(f"리뷰 파일 분석 중: {input_file}")
            
            # 결과 트리뷰 초기화
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            
            # 요약 텍스트 초기화
            self.summary_text.config(state=tk.NORMAL)
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.config(state=tk.DISABLED)
            
            # 진행 상태 초기화
            self.progress_var.set(0)
            self.progress_label_var.set("0%")
            
            # 파일 확장자 확인
            ext = os.path.splitext(input_file)[1].lower()
            
            # 파일 읽기
            try:
                import pandas as pd
                if ext in ['.xlsx', '.xls']:
                    df = pd.read_excel(input_file)
                elif ext == '.csv':
                    df = pd.read_csv(input_file, encoding='utf-8-sig')
                else:
                    self.add_log(f"지원하지 않는 파일 형식입니다: {ext}")
                    self.parent.after(0, lambda: messagebox.showerror("오류", f"지원하지 않는 파일 형식입니다: {ext}"))
                    return
                
                if df.empty:
                    self.add_log("파일에 데이터가 없습니다.")
                    self.parent.after(0, lambda: messagebox.showinfo("알림", "파일에 데이터가 없습니다."))
                    return
                
                # 필수 열이 있는지 확인 ('내용' 또는 '리뷰' 열 필요)
                review_col = None
                for col_name in ['내용', '리뷰', '리뷰내용', '후기', '구매평']:
                    if col_name in df.columns:
                        review_col = col_name
                        break
                
                if review_col is None:
                    self.add_log("리뷰 내용 열을 찾을 수 없습니다.")
                    self.parent.after(0, lambda: messagebox.showerror("오류", "리뷰 내용 열을 찾을 수 없습니다. '내용', '리뷰', '리뷰내용', '후기', '구매평' 중 하나의 열이 필요합니다."))
                    return
                
                # 감성 분석기 초기화
                analyzer = ReviewAnalyzer()
                
                # 긍정/부정 단어 사전 로드
                self.add_log("감성 사전 로드 중...")
                analyzer.load_dictionaries()
                
                # 사용자 사전 파일 확인
                if self.user_dict_var.get():
                    user_dict_file = self.user_dict_var.get()
                    if os.path.exists(user_dict_file):
                        self.add_log(f"사용자 감성 사전 로드 중: {user_dict_file}")
                        analyzer.load_user_dictionary(user_dict_file)
                    else:
                        self.add_log(f"사용자 감성 사전 파일을 찾을 수 없습니다: {user_dict_file}")
                
                # 각 리뷰 분석
                total_rows = len(df)
                positive_count = 0
                negative_count = 0
                neutral_count = 0
                
                self.add_log(f"총 {total_rows}개의 리뷰 분석 시작...")
                
                # 별점 열 찾기
                rating_col = None
                for col_name in ['별점', '평점', '점수', 'rating', 'score']:
                    if col_name in df.columns:
                        rating_col = col_name
                        break
                
                # 결과 저장할 새 열 추가
                df['감성분석'] = ''
                df['긍정단어'] = ''
                df['부정단어'] = ''
                
                # 각 행 처리
                for idx, row in df.iterrows():
                    if not self.is_analyzing:
                        self.add_log("분석이 중단되었습니다.")
                        break
                    
                    # 진행 상태 업데이트
                    progress = int((idx + 1) / total_rows * 100)
                    self.progress_var.set(progress)
                    self.progress_label_var.set(f"{progress}%")
                    
                    # 리뷰 내용 가져오기
                    review_text = str(row[review_col])
                    if not review_text or review_text.lower() == 'nan' or len(review_text.strip()) == 0:
                        continue
                    
                    # 리뷰 분석
                    sentiment, pos_words, neg_words = analyzer.analyze_review(review_text)
                    
                    # 결과 저장
                    df.at[idx, '감성분석'] = sentiment
                    df.at[idx, '긍정단어'] = ', '.join(pos_words) if pos_words else ''
                    df.at[idx, '부정단어'] = ', '.join(neg_words) if neg_words else ''
                    
                    # 감성에 따라 카운트
                    if sentiment == 'positive':
                        positive_count += 1
                        tag = 'positive'
                    elif sentiment == 'negative':
                        negative_count += 1
                        tag = 'negative'
                    else:
                        neutral_count += 1
                        tag = 'neutral'
                    
                    # 결과를 트리뷰에 추가
                    values = (
                        idx + 1,
                        row[rating_col] if rating_col and not pd.isna(row[rating_col]) else '',
                        sentiment,
                        df.at[idx, '긍정단어'],
                        df.at[idx, '부정단어']
                    )
                    self.result_tree.insert('', 'end', values=values, tags=(tag,))
                    
                    # 로그 업데이트 (10개마다)
                    if (idx + 1) % 10 == 0 or idx == total_rows - 1:
                        self.add_log(f"진행 중: {idx + 1}/{total_rows} 완료 ({progress}%)")
                
                # 최종 결과 저장
                output_file = self.output_file_var.get()
                if not output_file:
                    # 입력 파일과 같은 위치에 _analyzed 접미사 추가
                    file_name, file_ext = os.path.splitext(input_file)
                    output_file = f"{file_name}_analyzed{file_ext}"
                    self.output_file_var.set(output_file)
                
                # 저장 폴더가 없으면 생성
                output_dir = os.path.dirname(output_file)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir)
                
                # 파일 저장
                if output_file.lower().endswith('.csv'):
                    df.to_csv(output_file, index=False, encoding='utf-8-sig')
                else:
                    df.to_excel(output_file, index=False, engine='openpyxl')
                
                # 분석 완료 메시지
                self.add_log(f"분석 완료: 긍정({positive_count}), 부정({negative_count}), 중립({neutral_count})")
                self.add_log(f"결과가 저장되었습니다: {output_file}")
                
                # 결과 요약 표시
                total_analyzed = positive_count + negative_count + neutral_count
                positive_percent = (positive_count / total_analyzed * 100) if total_analyzed > 0 else 0
                negative_percent = (negative_count / total_analyzed * 100) if total_analyzed > 0 else 0
                neutral_percent = (neutral_count / total_analyzed * 100) if total_analyzed > 0 else 0
                
                summary = f"""
                ===== 감성 분석 결과 요약 =====
                
                • 분석 파일: {os.path.basename(input_file)}
                • 총 리뷰 수: {total_rows}개
                • 분석된 리뷰: {total_analyzed}개
                
                ◆ 감성 분포:
                • 긍정 리뷰: {positive_count}개 ({positive_percent:.1f}%)
                • 부정 리뷰: {negative_count}개 ({negative_percent:.1f}%)
                • 중립 리뷰: {neutral_count}개 ({neutral_percent:.1f}%)
                
                ◆ 결과 파일: {os.path.basename(output_file)}
                """
                
                self.update_summary(summary)
                
                # 결과 탭으로 이동
                self.tab_control.select(1)  # 분석 요약 탭으로 전환
                
                # 완료 메시지
                self.parent.after(0, lambda: messagebox.showinfo("완료", f"감성 분석이 완료되었습니다.\n긍정: {positive_count}개, 부정: {negative_count}개, 중립: {neutral_count}개"))
                
            except Exception as e:
                self.add_log(f"파일 분석 중 오류 발생: {str(e)}")
                self.parent.after(0, lambda: messagebox.showerror("오류", f"파일 분석 중 오류가 발생했습니다.\n{str(e)}"))
        except Exception as e:
            self.add_log(f"분석 중 오류 발생: {str(e)}")
            self.parent.after(0, lambda: messagebox.showerror("오류", f"분석 중 오류가 발생했습니다.\n{str(e)}"))
        finally:
            # 분석 완료 후 UI 상태 복원
            self.is_analyzing = False
            self.parent.after(0, self.enable_ui)
    
    def update_summary(self, message):
        """요약 텍스트 영역에 메시지 추가"""
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.insert(tk.END, message)
        self.summary_text.see(tk.END)
        self.summary_text.config(state=tk.DISABLED)
    
    def display_analysis_results(self, df):
        """분석 결과를 트리뷰에 표시"""
        # 기존 항목 삭제
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)
        
        # 데이터 추가
        for idx, row in df.iterrows():
            values = (
                idx + 1,
                row.get('별점', ''),
                row.get('감성분석', ''),
                row.get('긍정단어', ''),
                row.get('부정단어', '')
            )
            self.result_tree.insert('', 'end', values=values, tags=(row.get('감성분석', ''),))
        
        # 항목 색상 설정
        self.result_tree.tag_configure('positive', background='#E6F5E6')  # 연한 녹색
        self.result_tree.tag_configure('negative', background='#F5E6E6')  # 연한 빨간색
        self.result_tree.tag_configure('neutral', background='#F5F5F5')   # 연한 회색
    
    def display_analysis_summary(self, summary):
        """감성 분석 요약 결과 표시"""
        # 요약 텍스트 초기화
        self.summary_text.config(state=tk.NORMAL)
        self.summary_text.delete(1.0, tk.END)
        
        # 요약 정보 추가
        self.summary_text.insert(tk.END, "=== 감성 분석 요약 ===\n\n")
        self.summary_text.insert(tk.END, f"전체 리뷰: {summary['전체리뷰수']}개\n")
        self.summary_text.insert(tk.END, f"긍정 리뷰: {summary['긍정리뷰수']}개 ({summary['긍정비율']*100:.1f}%)\n")
        self.summary_text.insert(tk.END, f"부정 리뷰: {summary['부정리뷰수']}개 ({summary['부정비율']*100:.1f}%)\n")
        self.summary_text.insert(tk.END, f"중립 리뷰: {summary['중립리뷰수']}개 ({summary['중립비율']*100:.1f}%)\n")
        
        if '평균별점' in summary and summary['평균별점'] is not None:
            self.summary_text.insert(tk.END, f"평균 별점: {summary['평균별점']:.2f}점\n")
        
        self.summary_text.insert(tk.END, "\n=== 주요 긍정 단어 ===\n")
        for word, count in summary['주요긍정단어'].items():
            self.summary_text.insert(tk.END, f"{word}: {count}회\n")
        
        self.summary_text.insert(tk.END, "\n=== 주요 부정 단어 ===\n")
        for word, count in summary['주요부정단어'].items():
            self.summary_text.insert(tk.END, f"{word}: {count}회\n")
        
        self.summary_text.config(state=tk.DISABLED)
    
    def show_review_detail(self, event):
        """리뷰 상세 정보 표시"""
        if not self.analysis_results is not None:
            return
        
        # 선택한 항목 가져오기
        selection = self.result_tree.selection()
        if not selection:
            return
        
        # 선택한 항목의 인덱스 가져오기
        item = self.result_tree.item(selection[0])
        index = int(item['values'][0]) - 1
        
        if index < 0 or index >= len(self.analysis_results):
            return
        
        # 리뷰 상세 정보 창 표시
        review_data = self.analysis_results.iloc[index]
        
        detail_window = tk.Toplevel(self.frame)
        detail_window.title("리뷰 상세 정보")
        detail_window.geometry("600x400")
        detail_window.minsize(500, 300)
        
        # 상세 정보 표시
        ttk.Label(detail_window, text="리뷰 상세 정보", font=("Helvetica", 12, "bold")).pack(pady=10)
        
        detail_frame = ttk.Frame(detail_window, padding=10)
        detail_frame.pack(fill=tk.BOTH, expand=True)
        
        # 리뷰 기본 정보
        info_frame = ttk.LabelFrame(detail_frame, text="기본 정보", padding=10)
        info_frame.pack(fill=tk.X, pady=5)
        
        row = 0
        for col in ['순번', '작성자명', '별점', '작성일자', '구매확정', '옵션정보']:
            if col in review_data:
                ttk.Label(info_frame, text=f"{col}:").grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
                ttk.Label(info_frame, text=str(review_data[col])).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
                row += 1
        
        # 감성 분석 결과
        sentiment_frame = ttk.LabelFrame(detail_frame, text="감성 분석 결과", padding=10)
        sentiment_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(sentiment_frame, text="감성:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(sentiment_frame, text=review_data['감성분석']).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(sentiment_frame, text="감성점수:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(sentiment_frame, text=f"{review_data['감성점수']:.2f}").grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(sentiment_frame, text="긍정 단어:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(sentiment_frame, text=str(review_data['긍정단어'])).grid(row=2, column=1, sticky=tk.W, padx=5, pady=2)
        
        ttk.Label(sentiment_frame, text="부정 단어:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Label(sentiment_frame, text=str(review_data['부정단어'])).grid(row=3, column=1, sticky=tk.W, padx=5, pady=2)
        
        # 리뷰 내용
        content_frame = ttk.LabelFrame(detail_frame, text="리뷰 내용", padding=10)
        content_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        content_text = ScrolledText(content_frame, wrap=tk.WORD)
        content_text.pack(fill=tk.BOTH, expand=True)
        
        if '리뷰내용' in review_data and review_data['리뷰내용']:
            content_text.insert(tk.END, str(review_data['리뷰내용']))
        
        content_text.config(state=tk.DISABLED)
        
        # 닫기 버튼
        ttk.Button(detail_window, text="닫기", command=detail_window.destroy).pack(pady=10)
    
    def refresh(self):
        """UI 새로고침"""
        if not self.is_analyzing:
            # 결과 테이블 초기화
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            
            # 요약 텍스트 초기화
            self.summary_text.config(state=tk.NORMAL)
            self.summary_text.delete(1.0, tk.END)
            self.summary_text.config(state=tk.DISABLED)
            
            # 진행 상태바 초기화
            self.progress_var.set(0)
            self.progress_label_var.set("0%") 