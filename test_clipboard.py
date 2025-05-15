import tkinter as tk
from tkinter import messagebox

class ClipboardTest:
    def __init__(self, root):
        self.root = root
        root.title("클립보드 테스트")
        root.geometry("500x400")
        
        # 레이블 생성
        label = tk.Label(root, text="엑셀에서 복사한 내용을 붙여넣으세요:", font=("맑은 고딕", 12))
        label.pack(pady=10)
        
        # 텍스트 위젯 생성
        self.text_area = tk.Text(root, width=50, height=10, font=("맑은 고딕", 10))
        self.text_area.pack(pady=10, padx=20, fill=tk.BOTH, expand=True)
        
        # 붙여넣기 단축키 바인딩
        self.text_area.bind("<Control-v>", self.paste_text)
        self.text_area.bind("<Command-v>", self.paste_text)  # macOS 지원
        
        # 우클릭 메뉴 생성
        self.create_context_menu()
        
        # 상태 레이블
        self.status_var = tk.StringVar()
        self.status_var.set("준비됨")
        status_label = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W)
        status_label.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 버튼 생성
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10)
        
        paste_button = tk.Button(button_frame, text="붙여넣기", command=lambda: self.paste_text_manual())
        paste_button.pack(side=tk.LEFT, padx=5)
        
        get_clipboard_button = tk.Button(button_frame, text="클립보드 내용 확인", command=self.check_clipboard)
        get_clipboard_button.pack(side=tk.LEFT, padx=5)
        
        clear_button = tk.Button(button_frame, text="내용 지우기", command=self.clear_text)
        clear_button.pack(side=tk.LEFT, padx=5)
    
    def create_context_menu(self):
        """컨텍스트 메뉴 생성"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="붙여넣기", command=self.paste_text_manual)
        self.context_menu.add_command(label="복사", command=self.copy_text)
        self.context_menu.add_command(label="잘라내기", command=self.cut_text)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="모두 선택", command=self.select_all)
        self.context_menu.add_command(label="내용 지우기", command=self.clear_text)
        
        # 우클릭 이벤트 바인딩
        self.text_area.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        """우클릭 메뉴 표시"""
        self.context_menu.post(event.x_root, event.y_root)
    
    def paste_text(self, event=None):
        """키보드 단축키로 붙여넣기 (이벤트 핸들러)"""
        self.paste_text_manual()
        return "break"  # 기본 이벤트 처리 중단
    
    def paste_text_manual(self):
        """버튼이나 메뉴로 붙여넣기"""
        try:
            # 클립보드 내용 가져오기
            clipboard = self.root.clipboard_get()
            
            # 현재 선택된 텍스트 제거
            if self.text_area.tag_ranges(tk.SEL):
                self.text_area.delete(tk.SEL_FIRST, tk.SEL_LAST)
            
            # 엑셀 형식 감지 및 처리
            if '\t' in clipboard or '\r\n' in clipboard:
                # 탭을 쉼표로 변환
                clipboard = clipboard.replace('\t', ',')
                # Windows 줄바꿈 통일
                clipboard = clipboard.replace('\r\n', '\n')
                
                self.status_var.set("Excel 형식 감지: 탭과 줄바꿈을 처리했습니다")
            else:
                self.status_var.set("일반 텍스트 붙여넣기 완료")
                
            # 클립보드 내용 출력 (디버깅용)
            print("클립보드 내용 (바이트 표현):", [ord(c) for c in clipboard[:20]], "..." if len(clipboard) > 20 else "")
            print("원본 클립보드 내용 (앞 20자):", repr(clipboard[:20]), "..." if len(clipboard) > 20 else "")
            
            # 텍스트 삽입
            self.text_area.insert(tk.INSERT, clipboard)
            
        except tk.TclError as e:
            self.status_var.set(f"클립보드 오류: {str(e)}")
            print(f"클립보드 접근 오류: {str(e)}")
        except Exception as e:
            self.status_var.set(f"오류 발생: {str(e)}")
            print(f"예외 발생: {str(e)}")
    
    def check_clipboard(self):
        """클립보드 내용 확인"""
        try:
            clipboard = self.root.clipboard_get()
            messagebox.showinfo("클립보드 내용", f"클립보드 내용 (앞 100자):\n{clipboard[:100]}")
            print("클립보드 내용:", repr(clipboard[:100]))
        except Exception as e:
            self.status_var.set(f"클립보드 확인 오류: {str(e)}")
            messagebox.showerror("오류", f"클립보드를 읽을 수 없습니다: {str(e)}")
    
    def copy_text(self):
        """선택한 텍스트 복사"""
        try:
            if self.text_area.tag_ranges(tk.SEL):
                selected_text = self.text_area.get(tk.SEL_FIRST, tk.SEL_LAST)
                self.root.clipboard_clear()
                self.root.clipboard_append(selected_text)
                self.status_var.set("텍스트가 복사되었습니다")
        except Exception as e:
            self.status_var.set(f"복사 오류: {str(e)}")
    
    def cut_text(self):
        """선택한 텍스트 잘라내기"""
        self.copy_text()
        try:
            if self.text_area.tag_ranges(tk.SEL):
                self.text_area.delete(tk.SEL_FIRST, tk.SEL_LAST)
        except Exception as e:
            self.status_var.set(f"잘라내기 오류: {str(e)}")
    
    def select_all(self):
        """모든 텍스트 선택"""
        self.text_area.tag_add(tk.SEL, "1.0", tk.END)
        self.text_area.mark_set(tk.INSERT, "1.0")
        self.text_area.see(tk.INSERT)
        self.status_var.set("모든 텍스트가 선택되었습니다")
    
    def clear_text(self):
        """텍스트 모두 지우기"""
        self.text_area.delete(1.0, tk.END)
        self.status_var.set("텍스트가 삭제되었습니다")

# 메인 프로그램 실행
if __name__ == "__main__":
    root = tk.Tk()
    app = ClipboardTest(root)
    root.mainloop() 