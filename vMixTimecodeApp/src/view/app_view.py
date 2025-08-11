import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import requests
import xml.etree.ElementTree as ET
import json
import threading
import queue
import os
from datetime import datetime
from PIL import Image, ImageTk
import concurrent.futures
import time
import math
import keyboard
import pyperclip

from src.model.settings import load_settings
from src.model.line_data import LineDataModel # LineDataModel 임포트
from src.view.ui_utils import StatusCircleBar, bind_widget_full_navigation

from src.controller.app_controller import AppController # AppController 임포트
from src.utils.logger import app_logger # 로거 임포트

class LineMonitor:
    def __init__(self):
        self.running = False
        self.executed = False

class ActiveTimecodeApp:
    def __init__(self, master):
        self.master = master
        master.title("vMix ACTIVE Input Timecode v1064")
        master.configure(bg="black")
        
        self.settings = load_settings()
        self.line_data_model = LineDataModel() # LineDataModel 인스턴스 생성
        self.controller = AppController(self) # AppController 인스턴스 생성
        
        # ... (이전과 동일한 설정 로드 부분) ...
        self.main_vmix_name = self.settings.get("main_vmix_name", "M")
        self.main_ip = self.settings.get("main_ip", "127.0.0.1")
        # ...

        # --- GTO-W 기능 추가 1: 모드 설정 변수 ---
        self.app_mode = tk.StringVar(value=self.settings.get("app_mode", "방송 진행용"))
        self.app_mode.trace_add("write", self.controller.on_app_mode_change) # 컨트롤러의 메서드 호출

        # --- 메뉴바 설정 ---
        menubar = tk.Menu(master)
        master.config(menu=menubar)
        
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="설정", menu=settings_menu)
        settings_menu.add_command(label="IP 관리", command=self.controller.open_settings_window) # 컨트롤러의 메서드 호출
        # ... (다른 설정 메뉴들)

        # --- GTO-W 기능 추가 2: 동작 모드 선택 메뉴 ---
        mode_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label="동작 모드", menu=mode_menu)
        mode_menu.add_radiobutton(label="방송 진행용", variable=self.app_mode, value="방송 진행용")
        mode_menu.add_radiobutton(label="GTO-W 감시용", variable=self.app_mode, value="GTO-W 감시용")
        
        settings_menu.add_separator()
        settings_menu.add_command(label="단축키 다시 등록하기", command=self.controller.reload_all_hotkeys) # 컨트롤러의 메서드 호출

        # ... (이하 UI 구성 코드는 대부분 동일) ...
        # PanedWindow, left_frame, timecode_label 등...
        # `rebuild_ui` 함수에서 'B'열 Entry에 `validate_gto_logic` 함수를 바인딩하는 부분만 변경됨
        # (이하 생략된 코드는 1063.py와 동일)
        # ... (UI 구성 코드) ...
        # rebuild_ui 호출 전에 필요한 변수 초기화
        self.paned_window = tk.PanedWindow(master, orient=tk.HORIZONTAL, bg="#333333", sashwidth=5, sashrelief=tk.RAISED)
        self.paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.left_frame = tk.Frame(self.paned_window, bg="black")
        self.paned_window.add(self.left_frame, width=485)
        self.right_frame = tk.Frame(self.paned_window, bg="black")
        self.paned_window.add(self.right_frame)

        status_items = [("M", "Main vMix"), ("S", "Sub vMix"), ("T", "Tally")]
        self.status_bar = StatusCircleBar(self.right_frame, lambda: self.controller.vmix_status, status_items)
        self.status_bar.pack(pady=10)

        self.timecode_label = tk.Label(self.left_frame, text="--:--:--", font=("Helvetica", 36, "bold"), fg="#39FF14", bg="black", anchor="center")
        self.timecode_label.pack(pady=(5,1), fill=tk.X, padx=5)
        # ... (나머지 UI)
        self.previous_timecode_label_text = ""
        self.target_header_labels = []
        self.input_changer_labels = {}
        self.widget_matrix = [] # widget_matrix 초기화
        self.rebuild_ui() # 이 부분에서 UI가 실제로 생성됩니다.
        # ... (기타 초기화)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        self.controller.start_async_tasks() # 비동기 작업 시작

    def rebuild_ui(self):
        # ... (기존 rebuild_ui 코드 시작)
        for widget in self.left_frame.winfo_children():
            if widget not in [self.timecode_label]: # 필요한 위젯 제외하고 삭제
                widget.destroy()

        self.line_entries = []
        self.entry_grid_frame = tk.Frame(self.left_frame, bg="black")
        self.entry_grid_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        header_frame = tk.Frame(self.entry_grid_frame, bg="black")
        header_frame.pack(fill=tk.X)

        headers = ["Time", "Preview", "Button", "Description"]
        for i, header in enumerate(headers):
            label = tk.Label(header_frame, text=header, font=("Helvetica", 10, "bold"), bg="black", fg="white")
            label.pack(side=tk.LEFT, expand=True, fill=tk.X)

        for i in range(self.line_data_model.rail_count): # self.rail_count 대신 model 사용
            line_frame = tk.Frame(self.entry_grid_frame, bg="black")
            line_frame.pack(fill=tk.X, pady=1)

            e_time = tk.Entry(line_frame, width=10, justify='center', bg="#333", fg="white")
            e_time.insert(0, self.line_data_model.lines[i]["time"])
            e_time.pack(side=tk.LEFT, padx=1)
            
            e_preview = tk.Entry(line_frame, width=10, justify='center', bg="#333", fg="white")
            e_preview.insert(0, self.line_data_model.lines[i]["preview"])
            e_preview.pack(side=tk.LEFT, padx=1)

            e_btn = tk.Entry(line_frame, width=3, justify='center', bg="#333", fg="white")
            e_btn.insert(0, self.line_data_model.lines[i]["button"]) # self.lines 대신 model 사용
            e_btn.pack(side=tk.LEFT, padx=1) # grid 대신 pack 사용
            
            e_desc = tk.Entry(line_frame, bg="#333", fg="white")
            e_desc.insert(0, self.line_data_model.lines[i]["description"])
            e_desc.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=1)

            self.widget_matrix.append([e_time, e_preview, e_btn, e_desc])

            # --- GTO-W 기능 추가 3: B열 수정 시 검사 함수 호출 ---
            e_btn.bind("<FocusOut>", lambda event, app=self: self.controller.validate_gto_logic_from_view(app)) # 컨트롤러의 메서드 호출
            e_btn.bind("<Return>", lambda event, app=self: self.controller.validate_gto_logic_from_view(app)) # 컨트롤러의 메서드 호출

            # ... (이하 나머지 위젯 생성 및 바인딩)

    def push_error(self, message):
        # 기존 messagebox.showerror 대신 로깅 사용
        app_logger.error(message)
        messagebox.showerror("오류", message) # 사용자에게도 표시

    def on_close(self):
        self.controller.stop_async_tasks() # 비동기 작업 중지
        app_logger.info("애플리케이션을 종료합니다.")
        self.master.destroy()

    # status_check_worker, get_connection_status 등은 AppController로 이동
    # ...
