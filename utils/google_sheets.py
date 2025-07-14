import gspread
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from google.auth.exceptions import GoogleAuthError
import json

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
                self.worksheet = self.spreadsheet.add_worksheet(title="Данные блогеров", rows="1000", cols="10")
            
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
                # Добавляем заголовки согласно ТЗ
                headers = [
                    "Пользователь", "Блогер", "Жалоба", "Тип Жалобы", 
                    "Соцсети", "Проценты возрастных категорий", 
                    "Дата подписки", "Дата окончания подписки"
                ]
                self.worksheet.insert_row(headers, 1)
                logger.info("Headers added to Google Sheets")
                
        except Exception as e:
            logger.error(f"Error ensuring headers: {e}")
    
    async def add_blogger_action(self, user_data: Dict[str, Any], blogger_data: Dict[str, Any], 
                                action_type: str = "add") -> bool:
        """Добавить действие с блогером в Google Sheets"""
        try:
            if not self.worksheet:
                if not await self.initialize():
                    return False
            
            # Форматируем данные пользователя
            user_info = f"{user_data.get('username', 'N/A')} ({user_data.get('role', 'N/A')})"
            
            # Форматируем данные блогера
            blogger_info = f"{blogger_data.get('name', 'N/A')} - {blogger_data.get('url', 'N/A')}"
            
            # Форматируем соцсети
            platforms = blogger_data.get('platforms', [])
            if isinstance(platforms, str):
                try:
                    platforms = json.loads(platforms)
                except:
                    platforms = [platforms]
            social_networks = ", ".join(platforms) if platforms else "N/A"
            
            # Форматируем возрастные категории
            age_categories = []
            if blogger_data.get('audience_13_17_percent'):
                age_categories.append(f"13-17: {blogger_data['audience_13_17_percent']}%")
            if blogger_data.get('audience_18_24_percent'):
                age_categories.append(f"18-24: {blogger_data['audience_18_24_percent']}%")
            if blogger_data.get('audience_25_35_percent'):
                age_categories.append(f"25-35: {blogger_data['audience_25_35_percent']}%")
            if blogger_data.get('audience_35_plus_percent'):
                age_categories.append(f"35+: {blogger_data['audience_35_plus_percent']}%")
            
            age_info = "; ".join(age_categories) if age_categories else "N/A"
            
            # Форматируем даты подписки
            subscription_start = user_data.get('subscription_start_date', 'N/A')
            if subscription_start and subscription_start != 'N/A':
                subscription_start = subscription_start.strftime('%d.%m.%Y') if hasattr(subscription_start, 'strftime') else subscription_start
            
            subscription_end = user_data.get('subscription_end_date', 'N/A')
            if subscription_end and subscription_end != 'N/A':
                subscription_end = subscription_end.strftime('%d.%m.%Y') if hasattr(subscription_end, 'strftime') else subscription_end
            
            # Подготавливаем данные для записи
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            row_data = [
                user_info,  # Пользователь
                blogger_info,  # Блогер
                "Нет",  # Жалоба (по умолчанию нет)
                "",  # Тип Жалобы (пусто)
                social_networks,  # Соцсети
                age_info,  # Проценты возрастных категорий
                subscription_start,  # Дата подписки
                subscription_end  # Дата окончания подписки
            ]
            
            # Добавляем строку в таблицу
            self.worksheet.append_row(row_data)
            
            logger.info(f"Blogger action added to Google Sheets: user={user_info}, blogger={blogger_info}, action={action_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding blogger action to Google Sheets: {e}")
            return False
    
    async def add_complaint(self, blogger_id: int, blogger_name: str, 
                           user_id: int, username: str, reason: str, 
                           status: str = "open") -> bool:
        """Добавить жалобу в Google Sheets"""
        try:
            if not self.worksheet:
                if not await self.initialize():
                    return False
            
            # Получаем все данные
            all_values = self.worksheet.get_all_values()
            
            # Ищем строку с нужным блогером (пропускаем заголовок)
            for i, row in enumerate(all_values[1:], start=2):
                if len(row) >= 2 and blogger_name in row[1]:  # Ищем по имени блогера
                    # Обновляем поля жалобы
                    self.worksheet.update_cell(i, 3, "Да")  # Жалоба
                    self.worksheet.update_cell(i, 4, reason)  # Тип Жалобы
                    logger.info(f"Complaint added to Google Sheets: blogger_id={blogger_id}, user_id={user_id}")
                    return True
            
            # Если блогер не найден, создаем новую строку
            current_time = datetime.now().strftime("%d.%m.%Y %H:%M")
            row_data = [
                f"{username} (buyer)",  # Пользователь
                blogger_name,  # Блогер
                "Да",  # Жалоба
                reason,  # Тип Жалобы
                "N/A",  # Соцсети
                "N/A",  # Проценты возрастных категорий
                "N/A",  # Дата подписки
                "N/A"  # Дата окончания подписки
            ]
            
            self.worksheet.append_row(row_data)
            logger.info(f"New complaint row added to Google Sheets: blogger_id={blogger_id}, user_id={user_id}")
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
                if len(row) >= 4 and row[2] == "Да" and row[3]:  # Есть жалоба
                    # Здесь можно добавить дополнительную логику поиска по пользователю
                    # Пока просто обновляем статус в поле "Тип Жалобы"
                    current_reason = row[3] if len(row) > 3 else ""
                    updated_reason = f"{current_reason} [Статус: {new_status}]"
                    self.worksheet.update_cell(i, 4, updated_reason)
                    logger.info(f"Complaint status updated in Google Sheets: blogger_id={blogger_id}, user_id={user_id}, status={new_status}")
                    return True
            
            logger.warning(f"Complaint not found in Google Sheets: blogger_id={blogger_id}, user_id={user_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error updating complaint status in Google Sheets: {e}")
            return False

# Глобальный экземпляр менеджера
sheets_manager = GoogleSheetsManager()

async def log_blogger_action_to_sheets(user_data: Dict[str, Any], blogger_data: Dict[str, Any], 
                                     action_type: str = "add") -> bool:
    """Функция-обертка для записи действия с блогером в Google Sheets"""
    return await sheets_manager.add_blogger_action(user_data, blogger_data, action_type)

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