#!/usr/bin/env python
# coding: utf-8

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
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='app.log',
    filemode='w'
)

logging.info("Application starting")

SETTINGS_FILE = "settings.json"

def save_settings(settings):
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

class LineMonitor:
    def __init__(self):
        self.running = False
        self.executed = False

def is_focusable_widget(w):
    return isinstance(w, (tk.Entry, tk.Button, tk.Checkbutton))

# (이전과 동일한 UI 헬퍼 함수들은 여기에 위치합니다)
# bind_entry_extended_events, set_tc_cursor, tc_shift_move, ... 등
def bind_entry_extended_events(entry, mode="timecode"):
    entry._drag_y = None
    entry._drag_in_progress = False
    entry._tc_idx = 2
    entry._tc_positions = [2, 5, 8]
    entry._tc_mode = (mode in ["timecode", "set_time"])

    def select_all(event):
        entry.after(1, lambda: entry.select_range(0, tk.END))
        entry.after(1, lambda: entry.icursor(tk.END))
    entry.bind("<FocusIn>", select_all, add="+")

    if entry._tc_mode:
        entry.bind("<FocusIn>", lambda e: set_tc_cursor(entry), add="+")
        entry.bind("<Shift-Left>", lambda e: tc_shift_move(entry, -1))
        entry.bind("<Shift-Right>", lambda e: tc_shift_move(entry, 1))
        entry.bind("<Shift-Up>", lambda e: tc_shift_incdec(entry, 1))
        entry.bind("<Shift-Down>", lambda e: tc_shift_incdec(entry, -1))
        entry.bind("<Return>", lambda e, en=entry: timecode_zero_autofill(en, app_instance=en.winfo_toplevel().nametowidget(".")))
    elif mode == "button":
        entry.bind("<Shift-Up>", lambda e: button_incdec(entry, 1))
        entry.bind("<Shift-Down>", lambda e: button_incdec(entry, -1))

def set_tc_cursor(entry):
    val = entry.get()
    if not val or len(val) != 8:
        return
    idx = getattr(entry, "_tc_idx", 2)
    pos = [2, 5, 8][idx]
    entry.icursor(pos)

def tc_shift_move(entry, delta):
    if entry.cget("state") in ("readonly", "disabled"):
        return "break"
    idx = getattr(entry, "_tc_idx", 2)
    idx = (idx + delta) % 3
    entry._tc_idx = idx
    set_tc_cursor(entry)
    return "break"

def tc_shift_incdec(entry, delta):
    if entry.cget("state") in ("readonly", "disabled"):
        return "break"
    val = entry.get()
    if not val or len(val) != 8 or val[2] != ":" or val[5] != ":":
        return "break"
    
    idx = getattr(entry, "_tc_idx", 2)
    try:
        h, m, s = map(int, val.split(":"))
    except ValueError:
        return "break"

    if idx == 0:
        h = (h + delta) % 24
    elif idx == 1:
        m = (m + delta) % 60
    else:
        s = (s + delta) % 60
    
    new_tc = f"{h:02d}:{m:02d}:{s:02d}"
    entry.delete(0, tk.END)
    entry.insert(0, new_tc)
    set_tc_cursor(entry)
    return "break"

def button_incdec(entry, delta):
    if entry.cget("state") in ("readonly", "disabled"):
        return "break"
    val = entry.get().strip()
    v = 0
    if val.isdigit():
        v = int(val)
    
    v = max(0, v + delta)
    entry.delete(0, tk.END)
    entry.insert(0, str(v))
    return "break"

def timecode_zero_autofill(entry, app_instance=None):
    if entry.cget("state") in ("readonly", "disabled"):
        return "break"
    val = entry.get().strip()

    if len(val) == 6 and val.isdigit():
        try:
            h = int(val[0:2])
            m = int(val[2:4])
            s = int(val[4:6])
            if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= s <= 59):
                if app_instance and hasattr(app_instance, 'push_error'):
                    app_instance.push_error(f"시간 값 오류: {h:02d}:{m:02d}:{s:02d}")
                return None
            
            formatted_val = f"{val[0:2]}:{val[2:4]}:{val[4:6]}"
            entry.delete(0, tk.END)
            entry.insert(0, formatted_val)
            entry.icursor(tk.END)
            return "break"
        except ValueError:
            return None

    if val == "0":
        entry.delete(0, tk.END)
        entry.insert(0, "00:00:00")
        entry.icursor(tk.END)
        return "break"

    return None

def bind_widget_full_navigation(widget, row_idx, col_idx, app):
    def on_key(event):
        dir_map = {
            "Up":    (-1, 0), "Down":  (1, 0),
            "Left":  (0, -1), "Right": (0, 1)
        }
        if event.state & 0x1: return None
        if event.keysym in dir_map:
            dr, dc = dir_map[event.keysym]
            r, c = row_idx, col_idx
            max_rows = len(app.widget_matrix)
            max_cols = len(app.widget_matrix[0]) if max_rows > 0 else 0
            for _ in range(max_rows * max_cols):
                r_new, c_new = r + dr, c + dc
                if dr != 0: r_new %= max_rows
                if dc != 0: c_new %= max_cols
                target = app.get_widget_by_rowcol(r_new, c_new)
                if target and target.winfo_ismapped() and target.cget('state') != 'disabled' and is_focusable_widget(target):
                    target.focus_set()
                    if isinstance(target, tk.Entry):
                        target.select_range(0, tk.END)
                        target.icursor(tk.END)
                    return "break"
                r, c = r_new, c_new
            return "break"
    for k in ["<Up>", "<Down>", "<Left>", "<Right>"]:
        widget.bind(k, on_key)

class StatusCircleBar(tk.Frame):
    # ... (이전과 동일)
    def __init__(self, master, get_status_callback, status_items, *args, **kwargs):
        super().__init__(master, bg="black", *args, **kwargs)
        self.get_status = get_status_callback
        self.status_items = status_items
        self.labels = []
        self._create_widgets()
        self.update_status()

    def _create_widgets(self):
        for lbl, canvas in self.labels:
            lbl.destroy()
            canvas.destroy()
        self.labels.clear()
        
        for short, _ in self.status_items:
            lbl = tk.Label(self, text=short, fg="white", bg="black", font=("Helvetica", 13), width=2)
            canvas = tk.Canvas(self, width=16, height=16, bg="black", highlightthickness=0)
            lbl.pack(side=tk.LEFT, padx=(2,0))
            canvas.pack(side=tk.LEFT, padx=(0,10))
            self.labels.append((lbl, canvas))

    def update_labels(self, new_status_items):
        self.status_items = new_status_items
        self._create_widgets()

    def update_status(self):
        status = self.get_status()
        colors = {0: "yellow", 1: "red", 2: "lime"}
        for idx, (_, canvas) in enumerate(self.labels):
            color = colors.get(status[idx] if idx < len(status) else 0, "yellow")
            canvas.delete("all")
            canvas.create_oval(2, 2, 14, 14, fill=color, outline="gray")
        self.after(1000, self.update_status)

class ActiveTimecodeApp:
    def __init__(self, master):
        logging.info("Initializing ActiveTimecodeApp")
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
        self.lines = [{"button": ""} for _ in range(self.rail_count)] # 임시
        self.previous_timecode_label_text = ""
        self.target_header_labels = []
        self.input_changer_labels = {}
        self.widget_matrix = []
        self.rebuild_ui() # 이 부분에서 UI가 실제로 생성됩니다.
        # ... (기타 초기화)
        self.master.protocol("WM_DELETE_WINDOW", self.on_close)
        # ...

    def on_app_mode_change(self, *args):
        mode = self.app_mode.get()

    def open_settings_window(self):
        logging.info("open_settings_window called")

    def reload_all_hotkeys(self):
        logging.info("reload_all_hotkeys called")

    def on_close(self):
        logging.info("on_close called")
        self.master.destroy()

    def push_error(self, msg):
        logging.error(msg)

    def run_line(self, line_index):
        logging.info(f"Running line {line_index}")

    def stop_line(self, line_index):
        logging.info(f"Stopping line {line_index}")
        self.push_error(f"동작 모드가 '{mode}'(으)로 변경되었습니다.")
        if mode == "GTO-W 감시용":
            self.validate_gto_logic()
        else:
            # GTO-W 모드가 아닐 때 모든 B열 배경색 초기화
            for line in self.line_entries:
                line["button"].config(bg="#333333") # 기본 배경색

    def rebuild_ui(self):
        # ... (기존 rebuild_ui 코드 시작)
        for widget in self.left_frame.winfo_children():
            if widget not in [self.timecode_label]: # 필요한 위젯 제외하고 삭제
                widget.destroy()

        self.line_frame = tk.Frame(self.left_frame, bg="black")
        self.line_frame.pack(fill=tk.BOTH, expand=True)

        self.line_entries = []
        self.widget_matrix = [[None for _ in range(4)] for _ in range(self.rail_count)]
        # ... (중략)
        for i in range(self.rail_count):
            # ... (e_time, e_preview 등 다른 위젯 생성)
            e_btn = tk.Entry(self.line_frame, width=3, justify='center', bg="#333", fg="white")
            e_btn.insert(0, self.lines[i]["button"])
            e_btn.grid(row=i+1, column=3, padx=1)
            self.widget_matrix[i][3] = e_btn

            # --- GTO-W 기능 추가 3: B열 수정 시 검사 함수 호출 ---
            e_btn.bind("<FocusOut>", self.validate_gto_logic)
            e_btn.bind("<Return>", self.validate_gto_logic)

            # ... (이하 나머지 위젯 생성 및 바인딩)

    def validate_gto_logic(self, event=None):
        """GTO-W 모드일 때 모든 GTO 계획의 유효성을 검사하고 UI에 피드백합니다."""
        if self.app_mode.get() != "GTO-W 감시용":
            return

        # 1. 모든 B열 배경색을 기본으로 초기화
        for line in self.line_entries:
            line["button"].config(bg="#333333")

        # 2. B열 값들을 숫자 리스트로 변환
        b_values = []
        for line in self.line_entries:
            val_str = line["button"].get().strip()
            b_values.append(int(val_str) if val_str.isdigit() else 0)

        # 3. GTO 계획 블록 찾기
        gto_blocks = self.find_gto_blocks(b_values)

        # 4. 각 블록을 검사하고 결과 처리
        for block in gto_blocks:
            start, end = block["start"], block["end"]
            plan_sequence = b_values[start : end + 1]
            
            is_valid, message, error_indices = self.check_single_gto_plan(plan_sequence)

            if is_valid:
                for i in range(start, end + 1):
                    self.line_entries[i]["button"].config(bg="#2E7D32") # 성공: 녹색
                    self.run_line(i)
            else:
                self.push_error(f"{start+1}번 레일 계획 오류: {message}")
                for i in range(start, end + 1):
                    self.stop_line(i) # 실패 시 실행 중지
                for error_idx in error_indices:
                    # 절대 인덱스로 변환하여 UI에 반영
                    self.line_entries[start + error_idx]["button"].config(bg="#D32F2F") # 실패: 붉은색


    def find_gto_blocks(self, b_values):
        """B열 값 리스트에서 '2'로 시작하고 '1'로 끝나는 모든 GTO 계획 블록의 인덱스를 찾습니다."""
        blocks = []
        i = 0
        while i < len(b_values):
            if b_values[i] == 2:
                start_index = i
                try:
                    # 현재 위치 이후에 '1'이 있는지 찾음
                    end_index = b_values.index(1, start_index + 1)
                    blocks.append({"start": start_index, "end": end_index})
                    i = end_index + 1 # 다음 검색은 이 블록 이후부터
                except ValueError:
                    # '1'을 찾지 못하면 루프 종료
                    i += 1
            else:
                i += 1
        return blocks

    def check_single_gto_plan(self, plan):
        """하나의 GTO 계획 시퀀스를 10가지 규칙에 따라 검사합니다."""
        # 규칙 4 (예외 케이스) 먼저 확인
        if plan == [2, 4, 17, 1]:
            return True, "성공", []

        # 규칙 2, 3 (시작과 끝)
        if plan[:3] != [2, 4, 5]:
            return False, "시작은 반드시 '2-4-5'여야 합니다.", [0, 1, 2]
        if plan[-3:] not in ([5, 8, 1], [6, 17, 1]):
            return False, "마지막은 '5-8-1' 또는 '6-17-1'이어야 합니다.", [len(plan)-3, len(plan)-2, len(plan)-1]

        for i, val in enumerate(plan):
            # 규칙 1 (연속 숫자)
            if i > 0 and val == plan[i-1]:
                return False, f"숫자 '{val}'가 연속으로 나올 수 없습니다.", [i-1, i]
            # 규칙 5 (2의 위치)
            if val == 2 and i != 0:
                return False, "'2'는 계획의 시작에만 올 수 있습니다.", [i]
            # 규칙 6 (4의 위치)
            if val == 4 and i != 1:
                return False, "'4'는 계획의 두 번째에만 올 수 있습니다.", [i]
            # 규칙 10 (8, 17의 위치)
            if val in (8, 17) and i != len(plan) - 2:
                return False, f"'{val}'는 계획의 끝에서 두 번째에만 올 수 있습니다.", [i]
            # 규칙 7 (5의 선행)
            if val == 5 and i > 0 and plan[i-1] not in (4, 6):
                return False, "'5'는 '4' 또는 '6' 다음에만 올 수 있습니다.", [i-1, i]
            # 규칙 8 (6의 선행)
            if val == 6 and i > 0 and plan[i-1] not in (5, 7):
                return False, "'6'는 '5' 또는 '7' 다음에만 올 수 있습니다.", [i-1, i]
            # 규칙 9 (7의 규칙)
            if val == 7:
                if i == 0 or plan[i-1] != 5:
                    return False, "'7'은 반드시 '5' 다음에 와야 합니다.", [i-1, i]
                if i == len(plan) - 1 or plan[i+1] != 6:
                    return False, "'7' 다음에는 반드시 '6'이 와야 합니다.", [i, i+1]

        return True, "성공", []

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


if __name__ == "__main__":
    logging.info("Starting main application")
    root = tk.Tk()
    app = ActiveTimecodeApp(root)
    root.mainloop()