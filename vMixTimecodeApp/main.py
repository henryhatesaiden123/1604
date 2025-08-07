import tkinter as tk
import sys
import os

# 프로젝트 루트를 sys.path에 추가하여 src 모듈을 찾을 수 있도록 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.view.app_view import ActiveTimecodeApp

if __name__ == "__main__":
    root = tk.Tk()
    app = ActiveTimecodeApp(root)
    root.mainloop()
