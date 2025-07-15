import os
import hashlib
import logging
from typing import Optional, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Настройки Robokassa
ROBOKASSA_LOGIN = os.getenv('ROBOKASSA_LOGIN', 'test_login')
ROBOKASSA_PASSWORD1 = os.getenv('ROBOKASSA_PASSWORD1', 'test_password1')
ROBOKASSA_PASSWORD2 = os.getenv('ROBOKASSA_PASSWORD2', 'test_password2')
ROBOKASSA_TEST_MODE = os.getenv('ROBOKASSA_TEST_MODE', 'true').lower() == 'true'

# URLs Robokassa
ROBOKASSA_BASE_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"
ROBOKASSA_TEST_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"

class RobokassaPayment:
    """Класс для работы с платежами Robokassa"""
    
    def __init__(self):
        self.login = ROBOKASSA_LOGIN
        self.password1 = ROBOKASSA_PASSWORD1
        self.password2 = ROBOKASSA_PASSWORD2
        self.test_mode = ROBOKASSA_TEST_MODE
        
    def generate_signature(self, amount: float, invoice_id: str, description: str = "") -> str:
        """Генерация подписи для Robokassa"""
        # Формула: md5(MerchantLogin:OutSum:InvId:Password1)
        signature_string = f"{self.login}:{amount}:{invoice_id}:{self.password1}"
        return hashlib.md5(signature_string.encode('utf-8')).hexdigest()
    
    def create_payment_url(self, user_id: int, amount: float, description: str = "Подписка на месяц") -> Dict:
        """Создание URL для оплаты"""
        # Генерируем уникальный ID платежа
        invoice_id = f"sub_{user_id}_{int(datetime.now().timestamp())}"
        
        # Генерируем подпись
        signature = self.generate_signature(amount, invoice_id, description)
        
        # Параметры для URL
        params = {
            'MerchantLogin': self.login,
            'OutSum': str(amount),
            'InvId': invoice_id,
            'Description': description,
            'SignatureValue': signature,
            'Culture': 'ru',
            'Encoding': 'utf-8'
        }
        
        if self.test_mode:
            params['IsTest'] = '1'
        
        # Формируем URL
        url_params = ';'.join([f"{k}={v}" for k, v in params.items()])
        payment_url = f"{ROBOKASSA_BASE_URL}?{url_params}"
        
        logger.info(f"Generated payment URL for user {user_id}, invoice {invoice_id}")
        
        return {
            'payment_url': payment_url,
            'invoice_id': invoice_id,
            'amount': amount,
            'signature': signature
        }
    
    def verify_payment(self, amount: float, invoice_id: str, signature: str) -> bool:
        """Проверка подписи результата оплаты"""
        # Формула: md5(OutSum:InvId:Password2)
        check_string = f"{amount}:{invoice_id}:{self.password2}"
        expected_signature = hashlib.md5(check_string.encode('utf-8')).hexdigest()
        
        is_valid = signature.lower() == expected_signature.lower()
        
        if is_valid:
            logger.info(f"Payment verification successful for invoice {invoice_id}")
        else:
            logger.warning(f"Payment verification failed for invoice {invoice_id}")
            
        return is_valid


# Глобальный экземпляр для использования
robokassa = RobokassaPayment()


def create_subscription_payment(user_id: int, subscription_type: str = "monthly") -> Dict:
    """Создание платежа за подписку"""
    
    # Определяем сумму в зависимости от типа подписки
    amounts = {
        "monthly": 500.0,
        "quarterly": 1350.0,  # 3 месяца со скидкой 10%
        "half_yearly": 2550.0,  # 6 месяцев со скидкой 15%
        "yearly": 5000.0      # 12 месяцев со скидкой 17%
    }
    
    amount = amounts.get(subscription_type, 500.0)
    descriptions = {
        "monthly": "Подписка на 1 месяц - Tinder для блогеров",
        "quarterly": "Подписка на 3 месяца - Tinder для блогеров", 
        "half_yearly": "Подписка на 6 месяцев - Tinder для блогеров",
        "yearly": "Подписка на 12 месяцев - Tinder для блогеров"
    }
    
    description = descriptions.get(subscription_type, "Подписка - Tinder для блогеров")
    
    # В тестовом режиме возвращаем заглушку
    if ROBOKASSA_TEST_MODE:
        return create_mock_payment(user_id, amount, description)
    
    # В продакшене создаем реальный платеж
    return robokassa.create_payment_url(user_id, amount, description)


def create_mock_payment(user_id: int, amount: float, description: str) -> Dict:
    """Создание mock-платежа для тестирования"""
    invoice_id = f"mock_{user_id}_{int(datetime.now().timestamp())}"
    
    logger.info(f"Created mock payment for user {user_id}: {amount}₽")
    
    return {
        'payment_url': f"https://mock-payment.test?amount={amount};user={user_id}",
        'invoice_id': invoice_id,
        'amount': amount,
        'signature': 'mock_signature',
        'is_mock': True
    }


def process_payment_callback(data: Dict) -> Dict:
    """Обработка callback от Robokassa"""
    
    if ROBOKASSA_TEST_MODE:
        # В тестовом режиме всегда успешно
        return {
            'success': True,
            'invoice_id': data.get('InvId', 'mock_invoice'),
            'amount': float(data.get('OutSum', 500)),
            'message': 'Mock payment successful'
        }
    
    # В продакшене проверяем подпись
    try:
        invoice_id = data.get('InvId')
        amount = float(data.get('OutSum'))
        signature = data.get('SignatureValue', '')
        
        if robokassa.verify_payment(amount, invoice_id, signature):
            return {
                'success': True,
                'invoice_id': invoice_id,
                'amount': amount,
                'message': 'Payment verified successfully'
            }
        else:
            return {
                'success': False,
                'error': 'Invalid signature',
                'message': 'Payment verification failed'
            }
            
    except Exception as e:
        logger.error(f"Error processing payment callback: {e}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Payment processing error'
        }


def get_payment_status(invoice_id: str) -> Dict:
    """Получение статуса платежа (заглушка)"""
    
    if ROBOKASSA_TEST_MODE:
        return {
            'status': 'paid',
            'invoice_id': invoice_id,
            'amount': 500.0,
            'paid_at': datetime.now().isoformat()
        }
    
    # TODO: Реализовать реальную проверку статуса через API Robokassa
    return {
        'status': 'unknown',
        'invoice_id': invoice_id,
        'message': 'Status check not implemented'
    } 