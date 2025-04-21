#!/usr/bin/env python
# -*- coding: utf-8 -*-

import pandas as pd
import argparse
import os

def csv_to_excel(csv_file, excel_file=None):
    """
    CSV 파일을 엑셀 파일로 변환
    
    Args:
        csv_file (str): 입력 CSV 파일 경로
        excel_file (str, optional): 출력 엑셀 파일 경로. 기본값은 CSV 파일과 동일한 이름에 .xlsx 확장자
    """
    if excel_file is None:
        excel_file = os.path.splitext(csv_file)[0] + '.xlsx'
    
    # CSV 파일 읽기
    df = pd.read_csv(csv_file, encoding='utf-8')
    
    # 엑셀 파일로 저장
    df.to_excel(excel_file, index=False)
    
    print(f"CSV 파일이 엑셀 파일로 변환되었습니다: {excel_file}")

def main():
    parser = argparse.ArgumentParser(description='CSV 파일을 엑셀 파일로 변환')
    parser.add_argument('csv_file', type=str, help='변환할 CSV 파일 경로')
    parser.add_argument('--output', '-o', type=str, help='출력 엑셀 파일 경로')
    
    args = parser.parse_args()
    csv_to_excel(args.csv_file, args.output)

if __name__ == "__main__":
    main() 