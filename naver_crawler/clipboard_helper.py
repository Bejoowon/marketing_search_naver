#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
클립보드 내용에 접근하기 위한 여러 방법을 제공하는 도우미 모듈
"""

import tkinter as tk
import subprocess
import platform
import os
import sys

def get_clipboard_text_tkinter(root):
    """
    Tkinter를 사용하여 클립보드 내용 가져오기
    
    Args:
        root: tkinter 루트 객체
        
    Returns:
        str: 클립보드 내용
    """
    try:
        return root.clipboard_get()
    except tk.TclError as e:
        print(f"Tkinter 클립보드 접근 오류: {e}")
        return ""

def get_clipboard_text_subprocess():
    """
    운영체제별 명령어를 사용하여 클립보드 내용 가져오기
    
    Returns:
        str: 클립보드 내용
    """
    content = ""
    try:
        system = platform.system()
        if system == 'Darwin':  # macOS
            try:
                # 첫 번째 방법: pbpaste 명령어
                process = subprocess.Popen(
                    ['pbpaste'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, stderr = process.communicate(timeout=1)
                if process.returncode == 0:
                    content = stdout.decode('utf-8', errors='replace')
                    print("pbpaste 명령어로 클립보드 내용을 성공적으로 가져왔습니다.")
                else:
                    print(f"pbpaste 오류: {stderr.decode('utf-8', errors='replace')}")
                    
                    # 두 번째 방법: AppleScript 사용
                    script = 'osascript -e "the clipboard as text"'
                    process = subprocess.Popen(
                        script, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    stdout, stderr = process.communicate(timeout=1)
                    if process.returncode == 0:
                        content = stdout.decode('utf-8', errors='replace')
                        print("AppleScript로 클립보드 내용을 성공적으로 가져왔습니다.")
                    else:
                        print(f"AppleScript 오류: {stderr.decode('utf-8', errors='replace')}")
            except subprocess.TimeoutExpired:
                print("클립보드 명령 실행 시간 초과")
            except Exception as e:
                print(f"macOS 클립보드 접근 오류: {e}")
                
        elif system == 'Windows':
            # Windows에서는 powershell을 사용하여 클립보드 내용 가져오기
            process = subprocess.Popen(
                ['powershell.exe', '-command', 'Get-Clipboard'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            content = process.stdout.read().decode('utf-8', errors='replace')
        elif system == 'Linux':
            # Linux에서는 xclip 또는 xsel 사용
            if os.system('which xclip > /dev/null') == 0:
                process = subprocess.Popen(
                    ['xclip', '-selection', 'clipboard', '-o'],
                    stdout=subprocess.PIPE
                )
                content = process.stdout.read().decode('utf-8')
            elif os.system('which xsel > /dev/null') == 0:
                process = subprocess.Popen(
                    ['xsel', '-b', '-o'],
                    stdout=subprocess.PIPE
                )
                content = process.stdout.read().decode('utf-8')
        
        return content
    except Exception as e:
        print(f"운영체제 클립보드 접근 오류: {e}")
        return ""

def get_clipboard_text(root):
    """
    여러 방법을 시도하여 클립보드 내용 가져오기
    
    Args:
        root: tkinter 루트 객체
        
    Returns:
        str: 클립보드 내용
    """
    # 첫 번째 방법: tkinter 기본 방식
    content = get_clipboard_text_tkinter(root)
    
    # 내용이 없거나 오류 발생 시 다른 방법 시도
    if not content:
        content = get_clipboard_text_subprocess()
    
    return content

def process_excel_content(content):
    """
    Excel에서 복사한 내용을 처리
    
    Args:
        content (str): 원본 클립보드 내용
        
    Returns:
        str: 처리된 내용
    """
    # 내용이 없으면 빈 문자열 반환
    if not content:
        return ""
    
    # 디버깅
    print(f"처리 전 클립보드: {repr(content[:50])}")
    
    # 줄바꿈 문자를 모두 동일한 형식으로 통일
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    
    # Excel 형식 감지
    is_excel_format = False
    if '\t' in content or '\n' in content:
        is_excel_format = True
    
    # Excel 형식이면 처리
    if is_excel_format:
        # 탭을 쉼표로 변환
        content = content.replace('\t', ',')
        
        # 연속된 줄바꿈을 하나로 통일
        while '\n\n' in content:
            content = content.replace('\n\n', '\n')
        
        # 앞뒤 공백과 줄바꿈 제거
        content = content.strip()
        
        print("Excel 형식 처리 완료")
    
    # 디버깅
    print(f"처리 후 클립보드: {repr(content[:50])}")
    
    return content

# 모듈 테스트
if __name__ == "__main__":
    # 테스트 용도 실행 시 현재 클립보드 내용 출력
    root = tk.Tk()
    root.withdraw()  # GUI 창 숨기기
    
    print("=== 클립보드 내용 테스트 ===")
    
    # 방법 1: tkinter
    content1 = get_clipboard_text_tkinter(root)
    print(f"Tkinter 방식: {'성공' if content1 else '실패'}")
    if content1:
        print(f"내용 (첫 50자): {repr(content1[:50])}")
    
    # 방법 2: 운영체제 명령어
    content2 = get_clipboard_text_subprocess()
    print(f"운영체제 명령어 방식: {'성공' if content2 else '실패'}")
    if content2:
        print(f"내용 (첫 50자): {repr(content2[:50])}")
    
    # 통합 방식
    content = get_clipboard_text(root)
    print(f"통합 방식: {'성공' if content else '실패'}")
    if content:
        print(f"원본 내용 (첫 50자): {repr(content[:50])}")
        
        # Excel 형식 처리
        processed = process_excel_content(content)
        print(f"처리 후 내용 (첫 50자): {repr(processed[:50])}")
    
    root.destroy() 