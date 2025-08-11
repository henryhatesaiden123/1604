import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import requests
import keyboard
import asyncio
import aiohttp # For async HTTP requests
import xml.etree.ElementTree as ET
import threading

from src.controller.gto_logic import validate_gto_logic
from src.model.settings import save_settings
from src.utils.logger import app_logger

class AppController:
    def __init__(self, app_view):
        self.app_view = app_view
        self.vmix_status = [0, 0, 0] # vMix 연결 상태 (0: 초기, 1: 오류, 2: 정상)
        self.status_check_task = None # 비동기 작업 참조
        self.loop = None
        self.thread = None
        self.loop_started = threading.Event()

    def on_app_mode_change(self, *args):
        mode = self.app_view.app_mode.get()
        app_logger.info(f"동작 모드가 '{mode}'(으)로 변경되었습니다.")
        if mode == "GTO-W 감시용":
            self.validate_gto_logic_from_view(self.app_view)
        else:
            if hasattr(self.app_view, 'line_entries'):
                for line in self.app_view.line_entries:
                    line["button"].config(bg="#333333")

    def save_all_settings(self):
        settings = {
            "app_mode": self.app_view.app_mode.get(),
            "main_vmix_name": self.app_view.main_vmix_name,
            "main_ip": self.app_view.main_ip,
        }
        save_settings(settings)
        app_logger.info("설정이 저장되었습니다.")
        messagebox.showinfo("설정", "설정이 저장되었습니다.")

    def validate_gto_logic_from_view(self, app_instance):
        validate_gto_logic(app_instance, app_instance.line_data_model, app_instance.app_mode.get())

    def open_settings_window(self):
        app_logger.info("설정 창을 엽니다.")
        messagebox.showinfo("설정", "설정 창을 엽니다. (구현 예정)")

    def reload_all_hotkeys(self):
        app_logger.info("단축키를 다시 등록합니다.")
        messagebox.showinfo("단축키", "단축키를 다시 등록합니다. (구현 예정)")

    async def get_connection_status(self):
        vmix_ip = self.app_view.main_ip
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{vmix_ip}:8088/api/?Function=GetActiveInput", timeout=1) as response:
                    return response.status == 200
        except Exception:
            return False

    async def status_check_worker(self):
        while self.loop.is_running():
            vmix_connected = await self.get_connection_status()
            self.vmix_status[0] = 2 if vmix_connected else 1

            if self.app_view.master.winfo_exists():
                self.app_view.master.after(0, self.app_view.status_bar.update_status)
            
            await asyncio.sleep(5)

    def start_async_tasks(self):
        if self.thread is None or not self.thread.is_alive():
            self.loop = asyncio.new_event_loop()
            self.loop_started.clear()
            self.thread = threading.Thread(target=self.run_async_loop, daemon=True)
            self.thread.start()
            self.loop_started.wait() # Wait for the loop to be ready

        self.status_check_task = asyncio.run_coroutine_threadsafe(self.status_check_worker(), self.loop)

    def run_async_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop_started.set() # Signal that the loop is running
        try:
            self.loop.run_forever()
        finally:
            self.loop.close()

    def stop_async_tasks(self):
        if self.status_check_task:
            self.status_check_task.cancel()
        
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)
