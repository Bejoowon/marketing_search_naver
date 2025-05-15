#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
네이버 크롤러 GUI 애플리케이션

이 프로그램은 두 가지 독립적인 기능을 제공합니다:
1. 카페 외부노출 키워드 찾기: modules/search_crawler 모듈 사용
2. 구매평 수집기: modules/review_crawler 모듈 사용

각 모듈은 독립적으로 설계되어 있으며, 
한 모듈의 변경이 다른 모듈에 영향을 주지 않습니다.
"""

import os
import sys
import tkinter as tk
from modules.gui.app import main

# 애플리케이션 실행
if __name__ == "__main__":
    main() 