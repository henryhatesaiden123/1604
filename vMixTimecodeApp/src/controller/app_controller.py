import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import requests
import keyboard
import asyncio
import aiohttp # For async HTTP requests
import xml.etree.ElementTree as ET

from src.controller.gto_logic import validate_gto_logic
from src.model.settings import save_settings
from src.utils.logger import app_logger

class AppController:
    def __init__(self, app_view):
        self.app_view = app_view
        self.vmix_status = [0, 0, 0] # vMix 연결 상태 (0: 초기, 1: 오류, 2: 정상)
        self.status_check_task = None # 비동기 작업 참조

    def on_app_mode_change(self, *args):
        mode = self.app_view.app_mode.get()
        app_logger.info(f"동작 모드가 '{mode}'(으)로 변경되었습니다.")
        if mode == "GTO-W 감시용":
            self.validate_gto_logic_from_view(self.app_view)
        else:
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
        # vMix 연결 상태를 비동기적으로 확인
        vmix_ip = self.app_view.main_ip
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{vmix_ip}:8088/api/?Function=GetActiveInput", timeout=2) as response:
                    if response.status == 200:
                        xml_content = await response.text()
                        root = ET.fromstring(xml_content)
                        # 실제 vMix 응답에 따라 파싱 로직 변경 필요
                        # 여기서는 단순히 연결 성공 여부만 확인
                        return True
                    else:
                        app_logger.warning(f"vMix API 응답 오류: {response.status}")
                        return False
        except aiohttp.ClientError as e:
            app_logger.error(f"vMix 연결 오류: {e}")
            return False
        except asyncio.TimeoutError:
            app_logger.warning("vMix 연결 시간 초과.")
            return False
        except Exception as e:
            app_logger.error(f"알 수 없는 vMix 연결 오류: {e}")
            return False

    async def status_check_worker(self):
        while True:
            # vMix 연결 상태 확인
            vmix_connected = await self.get_connection_status()
            if vmix_connected:
                self.vmix_status[0] = 2 # vMix 연결 정상
                app_logger.info("vMix 연결 상태: 정상")
            else:
                self.vmix_status[0] = 1 # vMix 연결 오류
                app_logger.warning("vMix 연결 상태: 오류")

            # UI 업데이트 (메인 스레드에서 실행되도록 Tkinter의 after 사용)
            self.app_view.master.after(0, lambda: self.app_view.status_bar.update_status()) # status_bar는 app_view에 있다고 가정

            await asyncio.sleep(5) # 5초마다 상태 확인

    def start_async_tasks(self):
        # 비동기 작업 시작
        if self.status_check_task is None or self.status_check_task.done():
            self.status_check_task = asyncio.create_task(self.status_check_worker())
            app_logger.info("비동기 상태 확인 작업 시작.")

    def stop_async_tasks(self):
        # 비동기 작업 중지
        if self.status_check_task and not self.status_check_task.done():
            self.status_check_task.cancel()
            app_logger.info("비동기 상태 확인 작업 중지 요청.")
            # 작업이 실제로 취소될 때까지 기다릴 수 있음 (선택 사항)
            # try:
            #     await self.status_check_task
            # except asyncio.CancelledError:
            #     app_logger.info("비동기 상태 확인 작업이 취소되었습니다.")
