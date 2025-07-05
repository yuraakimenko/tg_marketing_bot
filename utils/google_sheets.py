import gspread
import logging
from datetime import datetime
from typing import Optional
from google.auth.exceptions import GoogleAuthError

logger = logging.getLogger(__name__)

# ID вашей Google-таблицы
SPREADSHEET_ID = "1ZHOmlxQP1uxMH1koMTXuZotJngeEGevoc8WTrrOUnis"
CREDENTIALS_PATH = "secrets/google-credentials.json"

class GoogleSheetsManager:
    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        
    async def initialize(self):
        """Инициализация подключения к Google Sheets"""
        try:
            # Авторизация через сервисный аккаунт
            self.client = gspread.service_account(filename=CREDENTIALS_PATH)
            
            # Открытие таблицы по ID
            self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
            
            # Получение первого листа (или создание если нет)
            try:
                self.worksheet = self.spreadsheet.sheet1
            except gspread.exceptions.WorksheetNotFound:
                self.worksheet = self.spreadsheet.add_worksheet(title="Жалобы", rows="1000", cols="10")
            
            # Проверяем заголовки, добавляем если нужно
            await self._ensure_headers()
            
            logger.info("Google Sheets connection established successfully")
            return True
            
        except FileNotFoundError:
            logger.error(f"Credentials file not found: {CREDENTIALS_PATH}")
            return False
        except GoogleAuthError as e:
            logger.error(f"Google Auth error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error initializing Google Sheets: {e}")
            return False
    
    async def _ensure_headers(self):
        """Убедиться, что заголовки столбцов установлены"""
        try:
            # Проверяем первую строку
            first_row = self.worksheet.row_values(1)
            
            if not first_row or len(first_row) == 0:
                # Добавляем заголовки
                headers = [
                    "Дата", "ID блогера", "Имя блогера", 
                    "ID пользователя", "Username", "Причина жалобы", "Статус"
                ]
                self.worksheet.insert_row(headers, 1)
                logger.info("Headers added to Google Sheets")
                
        except Exception as e:
            logger.error(f"Error ensuring headers: {e}")
    
    async def add_complaint(self, blogger_id: int, blogger_name: str, 
                           user_id: int, username: str, reason: str, 
                           status: str = "open") -> bool:
        """Добавить жалобу в Google Sheets"""
        try:
            if not self.worksheet:
                if not await self.initialize():
                    return False
            
            # Подготавливаем данные для записи
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            row_data = [
                current_time,
                str(blogger_id),
                blogger_name,
                str(user_id),
                username,
                reason,
                status
            ]
            
            # Добавляем строку в таблицу
            self.worksheet.append_row(row_data)
            
            logger.info(f"Complaint added to Google Sheets: blogger_id={blogger_id}, user_id={user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding complaint to Google Sheets: {e}")
            return False
    
    async def update_complaint_status_by_blogger_and_user(self, blogger_id: int, 
                                                         user_id: int, new_status: str) -> bool:
        """Обновить статус жалобы в Google Sheets"""
        try:
            if not self.worksheet:
                if not await self.initialize():
                    return False
            
            # Получаем все данные
            all_values = self.worksheet.get_all_values()
            
            # Ищем строку с нужной жалобой (пропускаем заголовок)
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) >= 7 and row[1] == str(blogger_id) and row[3] == str(user_id):
                    # Обновляем статус (колонка G = индекс 6)
                    self.worksheet.update_cell(i, 7, new_status)
                    logger.info(f"Complaint status updated in Google Sheets: blogger_id={blogger_id}, user_id={user_id}, status={new_status}")
                    return True
            
            logger.warning(f"Complaint not found in Google Sheets: blogger_id={blogger_id}, user_id={user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error updating complaint status in Google Sheets: {e}")
            return False

# Глобальный экземпляр менеджера
sheets_manager = GoogleSheetsManager()

async def log_complaint_to_sheets(blogger_id: int, blogger_name: str, 
                                 user_id: int, username: str, reason: str) -> bool:
    """Функция-обертка для записи жалобы в Google Sheets"""
    return await sheets_manager.add_complaint(
        blogger_id=blogger_id,
        blogger_name=blogger_name,
        user_id=user_id,
        username=username,
        reason=reason,
        status="open"
    ) 