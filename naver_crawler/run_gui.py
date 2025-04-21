#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
네이버 검색 크롤러 GUI 실행 스크립트
"""

import sys
import os
import tkinter as tk

# 필요한 모듈 확인
try:
    import selenium
    import pandas
    import bs4
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError as e:
    print(f"오류: 필요한 모듈이 설치되지 않았습니다. {e}")
    print("다음 명령으로 필요한 모듈을 설치하세요:")
    print("pip install -r requirements.txt")
    sys.exit(1)

# 현재 파일 경로 기준으로 모듈 import
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from naver_crawler_gui import NaverCrawlerGUI
except ImportError:
    print("오류: naver_crawler_gui.py 파일을 찾을 수 없습니다.")
    sys.exit(1)

def main():
    """GUI 애플리케이션 실행"""
    print("네이버 검색 크롤러 GUI를 시작합니다...")
    root = tk.Tk()
    app = NaverCrawlerGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 