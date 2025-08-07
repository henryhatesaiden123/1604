import tkinter as tk
import sys
import os
import asyncio

# 프로젝트 루트를 sys.path에 추가하여 src 모듈을 찾을 수 있도록 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.view.app_view import ActiveTimecodeApp

def run_tk_loop(root, interval=100):
    """Tkinter 이벤트 루프를 asyncio 이벤트 루프와 통합"""
    loop = asyncio.get_event_loop()
    
    def _run_loop():
        loop.call_soon(_run_loop)
        loop.run_until_complete(asyncio.sleep(0)) # 비동기 작업 실행
        root.after(interval, _run_loop) # Tkinter 이벤트 루프에 다시 등록

    root.after(interval, _run_loop) # 초기 실행

if __name__ == "__main__":
    root = tk.Tk()
    app = ActiveTimecodeApp(root)

    # Tkinter 이벤트 루프를 asyncio 이벤트 루프와 통합
    run_tk_loop(root)

    # 비동기 작업을 시작 (예: 주기적인 vMix 상태 확인)
    app.controller.start_async_tasks() # 컨트롤러에 비동기 작업 시작 메서드 추가 예정

    root.mainloop()
