#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from konlpy.tag import Okt
from collections import Counter
from wordcloud import WordCloud
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def get_logger():
    """모듈 로거 설정"""
    logger = logging.getLogger("ReviewAnalyzer")
    
    # 이미 로거가 설정되어 있는 경우 기존 로거 반환
    if logger.handlers:
        return logger
    
    # 로그 디렉토리 생성
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file = os.path.join(log_dir, "review_analyzer.log")
    
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


class ReviewAnalyzer:
    """리뷰 분석 클래스"""
    
    def __init__(self):
        """초기화"""
        self.logger = get_logger()
        self.okt = Okt()
        self.results_dir = "results/analysis"
        
        # 결과 저장 디렉토리 생성
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
        
        # 긍정/부정 단어 사전 로드
        self.pos_words = self._load_sentiment_words('positive')
        self.neg_words = self._load_sentiment_words('negative')
        
        self.logger.info("리뷰 분석기 초기화 완료")
    
    def _load_sentiment_words(self, sentiment_type):
        """감성 사전 파일 로드
        
        Args:
            sentiment_type (str): 'positive' 또는 'negative'
            
        Returns:
            set: 감성 단어 집합
        """
        # 감성 사전 파일 경로
        dict_file = os.path.join("data", f"{sentiment_type}_words_ko.txt")
        
        # 감성 사전 디렉토리 및 기본 사전 생성
        if not os.path.exists("data"):
            os.makedirs("data")
        
        # 기본 감성 단어
        default_words = {
            'positive': {
                '좋아요', '만족', '최고', '추천', '훌륭', '맘에들어요', '좋네요', 
                '좋습니다', '굿', '최고', '빠름', '친절', '정확', '편리', '저렴',
                '훌륭', '감사', '감동', '예쁨', '분위기', '특별', '행복', '완벽',
                '깔끔', '가성비', '최상', '신속', '정확', '만족스러움', '깨끗'
            },
            'negative': {
                '별로', '실망', '후회', '비추', '최악', '형편없어요', '안좋아요',
                '불만', '느림', '무성의', '비싸요', '문제', '부족', '불편', '비추천',
                '손상', '늦음', '오배송', '누락', '반품', '환불', '파손', '불량',
                '엉망', '더럽', '형편없음', '실망스러움', '나쁨', '불친절', '오래걸림'
            }
        }
        
        # 파일이 없으면 기본 사전 생성
        if not os.path.exists(dict_file):
            with open(dict_file, 'w', encoding='utf-8') as f:
                for word in default_words[sentiment_type]:
                    f.write(f"{word}\n")
            self.logger.info(f"{sentiment_type} 감성 사전 파일 생성: {dict_file}")
            return default_words[sentiment_type]
        
        # 파일에서 단어 목록 읽기
        try:
            with open(dict_file, 'r', encoding='utf-8') as f:
                words = {line.strip() for line in f if line.strip()}
            self.logger.info(f"{sentiment_type} 감성 사전 로드 완료: {len(words)}개 단어")
            return words
        except Exception as e:
            self.logger.error(f"감성 사전 로드 중 오류: {str(e)}")
            return default_words[sentiment_type]
    
    def add_sentiment_word(self, word, sentiment_type):
        """감성 사전에 단어 추가
        
        Args:
            word (str): 추가할 단어
            sentiment_type (str): 'positive' 또는 'negative'
            
        Returns:
            bool: 성공 여부
        """
        if not word:
            return False
        
        # 감성 사전 파일 경로
        dict_file = os.path.join("data", f"{sentiment_type}_words_ko.txt")
        
        # 현재 사전 로드
        current_dict = getattr(self, f"{sentiment_type[:3]}_words")
        
        # 이미 존재하는 단어인지 확인
        if word in current_dict:
            self.logger.info(f"단어 '{word}'은(는) 이미 {sentiment_type} 사전에 존재합니다.")
            return False
        
        try:
            # 파일에 단어 추가
            with open(dict_file, 'a', encoding='utf-8') as f:
                f.write(f"{word}\n")
            
            # 메모리 사전에도 추가
            current_dict.add(word)
            setattr(self, f"{sentiment_type[:3]}_words", current_dict)
            
            self.logger.info(f"단어 '{word}'을(를) {sentiment_type} 사전에 추가했습니다.")
            return True
            
        except Exception as e:
            self.logger.error(f"감성 사전에 단어 추가 중 오류: {str(e)}")
            return False
    
    def tokenize_text(self, text):
        """텍스트를 형태소 분석하여 명사, 형용사, 동사 추출
        
        Args:
            text (str): 분석할 텍스트
            
        Returns:
            list: 추출된 단어 리스트
        """
        if not text or not isinstance(text, str):
            return []
        
        try:
            # 한글과 영문만 남기고 제거 (특수문자, 이모지 등 제거)
            clean_text = re.sub(r'[^\wㄱ-ㅎㅏ-ㅣ가-힣\s]', ' ', text)
            
            # 형태소 분석
            pos_tagged = self.okt.pos(clean_text)
            
            # 명사, 형용사, 동사 추출 (2글자 이상)
            words = []
            for word, pos in pos_tagged:
                if len(word) >= 2 and pos in ['Noun', 'Adjective', 'Verb']:
                    words.append(word)
            
            return words
            
        except Exception as e:
            self.logger.error(f"텍스트 토큰화 중 오류: {str(e)}")
            return []
    
    def analyze_review_sentiment(self, review_text):
        """리뷰 텍스트의 감성 분석
        
        Args:
            review_text (str): 분석할 리뷰 텍스트
            
        Returns:
            dict: 감성 분석 결과
        """
        if not review_text or not isinstance(review_text, str):
            return {'sentiment': 'neutral', 'score': 0, 'positive_words': [], 'negative_words': []}
        
        try:
            # 형태소 분석
            words = self.tokenize_text(review_text)
            
            # 긍정/부정 단어 추출
            positive_words = [word for word in words if word in self.pos_words]
            negative_words = [word for word in words if word in self.neg_words]
            
            # 감성 점수 계산 (-1 ~ 1)
            pos_count = len(positive_words)
            neg_count = len(negative_words)
            total_count = pos_count + neg_count
            
            if total_count == 0:
                sentiment_score = 0
            else:
                sentiment_score = (pos_count - neg_count) / total_count
            
            # 감성 판단
            if sentiment_score > 0.1:
                sentiment = 'positive'
            elif sentiment_score < -0.1:
                sentiment = 'negative'
            else:
                sentiment = 'neutral'
            
            return {
                'sentiment': sentiment,
                'score': sentiment_score,
                'positive_words': positive_words,
                'negative_words': negative_words
            }
            
        except Exception as e:
            self.logger.error(f"리뷰 감성 분석 중 오류: {str(e)}")
            return {'sentiment': 'error', 'score': 0, 'positive_words': [], 'negative_words': []}
    
    def analyze_reviews_from_file(self, file_path):
        """파일에서 리뷰 데이터를 읽어 감성 분석
        
        Args:
            file_path (str): 리뷰 데이터 파일 경로 (CSV 또는 엑셀)
            
        Returns:
            pd.DataFrame: 분석 결과가 추가된 데이터프레임
        """
        try:
            # 파일 확장자 확인
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # 파일 읽기
            if file_ext == '.xlsx' or file_ext == '.xls':
                df = pd.read_excel(file_path)
            elif file_ext == '.csv':
                df = pd.read_csv(file_path, encoding='utf-8-sig')
            else:
                self.logger.error(f"지원되지 않는 파일 형식: {file_ext}")
                return None
            
            # 리뷰 컬럼 찾기
            review_col = None
            possible_cols = ['리뷰내용', '리뷰', '내용', 'review', 'content']
            
            for col in df.columns:
                if col.lower() in [c.lower() for c in possible_cols]:
                    review_col = col
                    break
            
            if not review_col:
                self.logger.error("리뷰 내용 컬럼을 찾을 수 없습니다.")
                return df
            
            # 결과 저장을 위한 컬럼 추가
            df['감성분석'] = 'neutral'
            df['감성점수'] = 0.0
            df['긍정단어'] = None
            df['부정단어'] = None
            
            # 각 리뷰 분석
            total_rows = len(df)
            self.logger.info(f"총 {total_rows}개의 리뷰 분석 시작")
            
            for idx, row in df.iterrows():
                review_text = row[review_col]
                if pd.isna(review_text) or not review_text:
                    continue
                
                # 감성 분석
                result = self.analyze_review_sentiment(str(review_text))
                
                # 결과 저장
                df.at[idx, '감성분석'] = result['sentiment']
                df.at[idx, '감성점수'] = result['score']
                df.at[idx, '긍정단어'] = ';'.join(result['positive_words'])
                df.at[idx, '부정단어'] = ';'.join(result['negative_words'])
                
                # 진행 상황 로깅
                if (idx + 1) % 100 == 0 or idx + 1 == total_rows:
                    self.logger.info(f"{idx + 1}/{total_rows} 리뷰 분석 완료")
            
            self.logger.info("리뷰 감성 분석 완료")
            return df
            
        except Exception as e:
            self.logger.error(f"리뷰 파일 분석 중 오류: {str(e)}")
            return None
    
    def generate_wordcloud(self, words, width=800, height=400, background_color='white', max_words=100):
        """워드클라우드 생성
        
        Args:
            words (list or str): 단어 리스트 또는 세미콜론으로 구분된 단어 문자열
            width (int): 이미지 너비
            height (int): 이미지 높이
            background_color (str): 배경색
            max_words (int): 최대 표시 단어 수
            
        Returns:
            WordCloud: 생성된 워드클라우드 객체
        """
        try:
            # 단어 문자열을 리스트로 변환
            if isinstance(words, str):
                word_list = [w.strip() for w in words.split(';') if w.strip()]
            else:
                word_list = words
            
            # 단어 빈도수 계산
            word_counts = Counter(word_list)
            
            # 워드클라우드 생성
            font_path = os.path.join('data', 'NanumGothic.ttf')
            
            # 폰트 파일이 없으면 기본 폰트 사용
            if not os.path.exists(font_path):
                self.logger.warning(f"'{font_path}' 폰트 파일이 없습니다. 기본 폰트를 사용합니다.")
                font_path = None
            
            wc = WordCloud(
                font_path=font_path,
                width=width,
                height=height,
                background_color=background_color,
                max_words=max_words,
                prefer_horizontal=0.9
            )
            
            if word_counts:
                wordcloud = wc.generate_from_frequencies(word_counts)
                return wordcloud
            else:
                self.logger.warning("워드클라우드를 생성할 단어가 없습니다.")
                return None
                
        except Exception as e:
            self.logger.error(f"워드클라우드 생성 중 오류: {str(e)}")
            return None
    
    def save_wordcloud_image(self, wordcloud, output_path):
        """워드클라우드 이미지 저장
        
        Args:
            wordcloud (WordCloud): 워드클라우드 객체
            output_path (str): 저장할 파일 경로
            
        Returns:
            bool: 저장 성공 여부
        """
        if wordcloud is None:
            self.logger.error("저장할 워드클라우드가 없습니다.")
            return False
        
        try:
            # 이미지 저장
            plt.figure(figsize=(10, 5))
            plt.imshow(wordcloud, interpolation='bilinear')
            plt.axis('off')
            plt.tight_layout()
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            self.logger.info(f"워드클라우드 이미지 저장 완료: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"워드클라우드 이미지 저장 중 오류: {str(e)}")
            return False
    
    def save_analysis_results(self, df, output_file):
        """분석 결과 저장
        
        Args:
            df (pd.DataFrame): 분석 결과 데이터프레임
            output_file (str): 저장할 파일 경로
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # 출력 파일 확장자 확인 및 저장
            out_ext = os.path.splitext(output_file)[1].lower()
            
            if out_ext == '.xlsx' or out_ext == '.xls':
                df.to_excel(output_file, index=False, engine='openpyxl')
            else:
                # 기본적으로 CSV로 저장
                df.to_csv(output_file, index=False, encoding='utf-8-sig')
            
            self.logger.info(f"분석 결과 저장 완료: {output_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"분석 결과 저장 중 오류: {str(e)}")
            return False
            
    def create_sentiment_summary(self, df):
        """감성 분석 결과 요약
        
        Args:
            df (pd.DataFrame): 감성 분석 결과 데이터프레임
            
        Returns:
            dict: 감성 분석 요약 결과
        """
        try:
            # 감성 분포 계산
            sentiment_counts = df['감성분석'].value_counts()
            total_reviews = len(df)
            
            positive_count = sentiment_counts.get('positive', 0)
            negative_count = sentiment_counts.get('negative', 0)
            neutral_count = sentiment_counts.get('neutral', 0)
            
            # 별점 평균 계산
            rating_col = None
            for col in df.columns:
                if '별점' in col or '평점' in col or 'rating' in col.lower() or 'score' in col.lower():
                    rating_col = col
                    break
            
            avg_rating = None
            if rating_col:
                avg_rating = df[rating_col].mean()
            
            # 긍정/부정 단어 빈도 계산
            all_pos_words = []
            all_neg_words = []
            
            for pos_word_list in df['긍정단어'].dropna():
                if pos_word_list:
                    all_pos_words.extend([w.strip() for w in pos_word_list.split(';') if w.strip()])
            
            for neg_word_list in df['부정단어'].dropna():
                if neg_word_list:
                    all_neg_words.extend([w.strip() for w in neg_word_list.split(';') if w.strip()])
            
            # 가장 빈번한 단어
            top_pos_words = Counter(all_pos_words).most_common(10)
            top_neg_words = Counter(all_neg_words).most_common(10)
            
            # 결과 요약
            summary = {
                '전체리뷰수': total_reviews,
                '긍정리뷰수': positive_count,
                '부정리뷰수': negative_count,
                '중립리뷰수': neutral_count,
                '긍정비율': positive_count / total_reviews if total_reviews > 0 else 0,
                '부정비율': negative_count / total_reviews if total_reviews > 0 else 0,
                '중립비율': neutral_count / total_reviews if total_reviews > 0 else 0,
                '평균별점': avg_rating,
                '주요긍정단어': dict(top_pos_words),
                '주요부정단어': dict(top_neg_words)
            }
            
            return summary
            
        except Exception as e:
            self.logger.error(f"감성 분석 요약 생성 중 오류: {str(e)}")
            return {
                '전체리뷰수': 0,
                '긍정리뷰수': 0,
                '부정리뷰수': 0,
                '중립리뷰수': 0,
                '주요긍정단어': {},
                '주요부정단어': {}
            }


# 테스트 코드
if __name__ == "__main__":
    analyzer = ReviewAnalyzer()
    
    # 테스트용 리뷰
    test_reviews = [
        "정말 좋은 제품이에요. 만족스럽습니다.",
        "배송이 너무 느리고 제품도 기대보다 별로네요.",
        "가격 대비 괜찮은 것 같아요. 그냥 쓸만합니다."
    ]
    
    for review in test_reviews:
        result = analyzer.analyze_review_sentiment(review)
        print(f"리뷰: {review}")
        print(f"감성: {result['sentiment']}, 점수: {result['score']:.2f}")
        print(f"긍정 단어: {result['positive_words']}")
        print(f"부정 단어: {result['negative_words']}")
        print("-" * 50) 