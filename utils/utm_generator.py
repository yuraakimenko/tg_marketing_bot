import re
import urllib.parse
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class UTMParams:
    """Параметры UTM-меток"""
    source: str = "quantori_community"
    medium: str = "social_discord"
    term: str = ""
    campaign: Optional[str] = None
    content: Optional[str] = None


class UTMGenerator:
    """Генератор UTM-меток для вакансий"""
    
    def __init__(self):
        self.base_params = UTMParams()
    
    def normalize_position_name(self, position_name: str) -> str:
        """Нормализация названия позиции для utm_term"""
        # Убираем лишние символы и приводим к нижнему регистру
        normalized = re.sub(r'[^\w\s-]', '', position_name.lower())
        # Заменяем пробелы на подчеркивания
        normalized = re.sub(r'\s+', '_', normalized.strip())
        # Убираем множественные подчеркивания
        normalized = re.sub(r'_+', '_', normalized)
        return normalized
    
    def generate_utm_params(self, position_name: str, company_name: str = None, 
                          location: str = None, job_type: str = None) -> Dict[str, str]:
        """Генерация UTM-параметров для позиции"""
        utm_params = {
            'utm_source': self.base_params.source,
            'utm_medium': self.base_params.medium,
            'utm_term': self.normalize_position_name(position_name)
        }
        
        # Добавляем дополнительные параметры если есть
        if company_name:
            utm_params['utm_campaign'] = self.normalize_position_name(company_name)
        
        if location or job_type:
            content_parts = []
            if location:
                content_parts.append(self.normalize_position_name(location))
            if job_type:
                content_parts.append(self.normalize_position_name(job_type))
            utm_params['utm_content'] = '_'.join(content_parts)
        
        return utm_params
    
    def add_utm_to_url(self, url: str, position_name: str, company_name: str = None,
                      location: str = None, job_type: str = None) -> str:
        """Добавление UTM-меток к URL"""
        utm_params = self.generate_utm_params(position_name, company_name, location, job_type)
        
        # Парсим URL
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        
        # Добавляем UTM-параметры
        for key, value in utm_params.items():
            query_params[key] = [value]
        
        # Собираем URL обратно
        new_query = urllib.parse.urlencode(query_params, doseq=True)
        new_url = urllib.parse.urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            new_query,
            parsed_url.fragment
        ))
        
        return new_url
    
    def generate_utm_string(self, position_name: str, company_name: str = None,
                           location: str = None, job_type: str = None) -> str:
        """Генерация строки UTM-параметров"""
        utm_params = self.generate_utm_params(position_name, company_name, location, job_type)
        return urllib.parse.urlencode(utm_params)


# Примеры использования
if __name__ == "__main__":
    generator = UTMGenerator()
    
    # Пример 1: Простая позиция
    position = "Senior Python Developer"
    utm_string = generator.generate_utm_string(position)
    print(f"UTM для '{position}': {utm_string}")
    
    # Пример 2: С дополнительными параметрами
    position = "Frontend React Developer"
    company = "TechCorp"
    location = "Remote"
    job_type = "Full-time"
    
    utm_string = generator.generate_utm_string(position, company, location, job_type)
    print(f"UTM для '{position}' в '{company}': {utm_string}")
    
    # Пример 3: Добавление к существующему URL
    url = "https://example.com/job/123"
    new_url = generator.add_utm_to_url(url, position, company, location, job_type)
    print(f"URL с UTM: {new_url}") 