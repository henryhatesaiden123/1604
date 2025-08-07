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

from src.model.settings import load_settings, save_settings
from src.view.ui_utils import StatusCircleBar, bind_widget_full_navigation
from src.controller.gto_logic import validate_gto_logic

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
        
        # ... (이전과 동일한 설정 로드 부분) ...
        self.main_vmix_name = self.settings.get("main_vmix_name", "M")
        self.main_ip = self.settings.get("main_ip", "127.0.0.1")
        # ...

        # --- GTO-W 기능 추가 1: 모드 설정 변수 ---
        self.app_mode = tk.StringVar(value=self.settings.get("app_mode", "방송 진행용"))
        self.app_mode.trace_add("write", self.on_app_mode_change)

        # --- 메뉴바 설정 ---
        menubar = tk.Menu(master)
        master.config(menu=menubar)
        
        settings_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="설정", menu=settings_menu)
        settings_menu.add_command(label="IP 관리", command=self.open_settings_window)
        # ... (다른 설정 메뉴들)

        # --- GTO-W 기능 추가 2: 동작 모드 선택 메뉴 ---
        mode_menu = tk.Menu(settings_menu, tearoff=0)
        settings_menu.add_cascade(label="동작 모드", menu=mode_menu)
        mode_menu.add_radiobutton(label="방송 진행용", variable=self.app_mode, value="방송 진행용")
        mode_menu.add_radiobutton(label="GTO-W 감시용", variable=self.app_mode, value="GTO-W 감시용")
        
        settings_menu.add_separator()
        settings_menu.add_command(label="단축키 다시 등록하기", command=self.reload_all_hotkeys)

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
        self.timecode_label = tk.Label(self.left_frame, text="--:--:--", font=("Helvetica", 36, "bold"), fg="#39FF14", bg="black", anchor="center")
        self.timecode_label.pack(pady=(5,1), fill=tk.X, padx=5)
        # ... (나머지 UI)
        self.rail_count = 30 # 임시
        self.lines = [] # 임시
        self.previous_timecode_label_text = ""
        self.target_header_labels = []
        self.input_changer_labels = {}
        self.rebuild_ui() # 이 부분에서 UI가 실제로 생성됩니다.
        # ... (기타 초기화)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        # ...

    def on_app_mode_change(self, *args):
        mode = self.app_mode.get()
        self.push_error(f"동작 모드가 '{mode}'(으)로 변경되었습니다.")
        if mode == "GTO-W 감시용":
            validate_gto_logic(self)
        else:
            # GTO-W 모드가 아닐 때 모든 B열 배경색 초기화
            for line in self.line_entries:
                line["button"].config(bg="#333333") # 기본 배경색

    def rebuild_ui(self):
        # ... (기존 rebuild_ui 코드 시작)
        for widget in self.left_frame.winfo_children():
            if widget not in [self.timecode_label]: # 필요한 위젯 제외하고 삭제
                widget.destroy()

        self.line_entries = []
        # ... (중략)
        for i in range(self.rail_count):
            # ... (e_time, e_preview 등 다른 위젯 생성)
            e_btn = tk.Entry(self.line_frame, width=3, justify='center', bg="#333", fg="white")
            e_btn.insert(0, self.lines[i]["button"])
            e_btn.grid(row=i+1, column=3, padx=1)
            self.widget_matrix[i][3] = e_btn

            # --- GTO-W 기능 추가 3: B열 수정 시 검사 함수 호출 ---
            e_btn.bind("<FocusOut>", lambda event, app=self: validate_gto_logic(app))
            e_btn.bind("<Return>", lambda event, app=self: validate_gto_logic(app))

            # ... (이하 나머지 위젯 생성 및 바인딩)

    def save_all_settings(self):
        # ... (기존 저장 로직)
        # --- GTO-W 기능 추가 4: 모드 설정 저장 ---
        settings = {
            "app_mode": self.app_mode.get(),
            # ... (이하 기존 저장 항목들)
        }
        save_settings(settings)
    
    # ... (이하 기존의 모든 다른 함수들은 여기에 위치합니다)
    # on_close, status_check_worker, get_connection_status, push_error 등...
    # ...
