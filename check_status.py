#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт перевірки статусу системи AI-Trader
Перевіряє всі критичні компоненти системи
"""

import os
import sys
import json
import socket
from pathlib import Path
from dotenv import load_dotenv

# Виправлення кодування для Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Завантажуємо змінні середовища
load_dotenv()

class SystemStatusChecker:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.success = []
        
    def check_python_version(self):
        """Перевірка версії Python"""
        print("🐍 Перевірка версії Python...")
        version = sys.version_info
        if version.major >= 3 and version.minor >= 10:
            self.success.append(f"✅ Python {version.major}.{version.minor}.{version.micro} - OK")
            return True
        else:
            self.issues.append(f"❌ Python {version.major}.{version.minor}.{version.micro} - Потрібна версія 3.10+")
            return False
    
    def check_dependencies(self):
        """Перевірка встановлених залежностей"""
        print("📦 Перевірка залежностей...")
        required_packages = [
            ('langchain', 'langchain'),
            ('langchain_openai', 'langchain-openai'),
            ('langchain_mcp_adapters', 'langchain-mcp-adapters'),
            ('fastmcp', 'fastmcp'),
            ('dotenv', 'python-dotenv')
        ]
        
        missing = []
        for import_name, package_name in required_packages:
            try:
                __import__(import_name)
                self.success.append(f"✅ {package_name} - встановлено")
            except ImportError:
                missing.append(package_name)
                self.issues.append(f"❌ {package_name} - не встановлено")
        
        return len(missing) == 0
    
    def check_config_file(self):
        """Перевірка файлу конфігурації"""
        print("⚙️  Перевірка конфігурації...")
        config_path = Path("configs/default_config.json")
        
        if not config_path.exists():
            self.issues.append(f"❌ Файл конфігурації не знайдено: {config_path}")
            return False
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Перевірка основних полів
            required_fields = ['agent_type', 'date_range', 'models', 'agent_config']
            for field in required_fields:
                if field not in config:
                    self.issues.append(f"❌ Відсутнє обов'язкове поле в конфігурації: {field}")
                    return False
            
            # Перевірка активних моделей
            enabled_models = [m for m in config.get('models', []) if m.get('enabled', False)]
            if len(enabled_models) == 0:
                self.warnings.append("⚠️  Немає активних моделей у конфігурації")
            else:
                self.success.append(f"✅ Знайдено {len(enabled_models)} активних моделей")
            
            self.success.append(f"✅ Файл конфігурації валідний: {config_path}")
            return True
            
        except json.JSONDecodeError as e:
            self.issues.append(f"❌ Помилка формату JSON у конфігурації: {e}")
            return False
        except Exception as e:
            self.issues.append(f"❌ Помилка читання конфігурації: {e}")
            return False
    
    def check_env_file(self):
        """Перевірка файлу .env"""
        print("🔐 Перевірка змінних середовища...")
        env_path = Path(".env")
        
        if not env_path.exists():
            self.warnings.append("⚠️  Файл .env не знайдено (може бути використано системні змінні)")
        else:
            self.success.append("✅ Файл .env знайдено")
        
        # Перевірка критичних змінних
        critical_vars = {
            'OPENAI_API_KEY': 'API ключ OpenAI',
            'OPENAI_API_BASE': 'Base URL OpenAI',
        }
        
        optional_vars = {
            'ALPHAADVANTAGE_API_KEY': 'API ключ Alpha Vantage',
            'JINA_API_KEY': 'API ключ Jina AI',
        }
        
        for var, desc in critical_vars.items():
            if not os.getenv(var):
                self.warnings.append(f"⚠️  {desc} ({var}) не встановлено")
            else:
                self.success.append(f"✅ {desc} встановлено")
        
        for var, desc in optional_vars.items():
            if not os.getenv(var):
                self.warnings.append(f"⚠️  {desc} ({var}) не встановлено (опціонально)")
            else:
                self.success.append(f"✅ {desc} встановлено")
    
    def check_data_files(self):
        """Перевірка наявності даних"""
        print("📊 Перевірка даних...")
        data_dir = Path("data")
        
        if not data_dir.exists():
            self.issues.append("❌ Директорія data не знайдена")
            return False
        
        # Перевірка файлів цін
        price_files = list(data_dir.glob("daily_prices_*.json"))
        if len(price_files) == 0:
            self.warnings.append("⚠️  Файли з даними цін не знайдено (може знадобитися запуск get_daily_price.py)")
        else:
            self.success.append(f"✅ Знайдено {len(price_files)} файлів з даними цін")
        
        # Перевірка директорії для даних агентів
        agent_data_dir = data_dir / "agent_data"
        if agent_data_dir.exists():
            self.success.append("✅ Директорія agent_data існує")
        else:
            self.warnings.append("⚠️  Директорія agent_data не існує (буде створена автоматично)")
        
        return True
    
    def check_mcp_services(self):
        """Перевірка стану MCP сервісів"""
        print("🔧 Перевірка MCP сервісів...")
        
        ports = {
            'math': int(os.getenv('MATH_HTTP_PORT', '8000')),
            'search': int(os.getenv('SEARCH_HTTP_PORT', '8001')),
            'trade': int(os.getenv('TRADE_HTTP_PORT', '8002')),
            'price': int(os.getenv('GETPRICE_HTTP_PORT', '8003'))
        }
        
        service_names = {
            'math': 'Math Service',
            'search': 'Search Service',
            'trade': 'Trade Service',
            'price': 'Price Service'
        }
        
        all_running = True
        for service_id, port in ports.items():
            if self.check_port(port):
                self.success.append(f"✅ {service_names[service_id]} працює на порту {port}")
            else:
                self.warnings.append(f"⚠️  {service_names[service_id]} не працює на порту {port}")
                all_running = False
        
        return all_running
    
    def check_port(self, port):
        """Перевірка доступності порту"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result == 0
        except:
            return False
    
    def check_agent_tools(self):
        """Перевірка наявності інструментів агента"""
        print("🛠️  Перевірка інструментів агента...")
        
        required_tools = [
            'agent_tools/tool_math.py',
            'agent_tools/tool_jina_search.py',
            'agent_tools/tool_trade.py',
            'agent_tools/tool_get_price_local.py',
            'agent_tools/start_mcp_services.py'
        ]
        
        all_exist = True
        for tool_path in required_tools:
            if Path(tool_path).exists():
                self.success.append(f"✅ {tool_path} - знайдено")
            else:
                self.issues.append(f"❌ {tool_path} - не знайдено")
                all_exist = False
        
        return all_exist
    
    def check_main_files(self):
        """Перевірка основних файлів"""
        print("📄 Перевірка основних файлів...")
        
        required_files = [
            'main.py',
            'requirements.txt',
            'agent/base_agent/base_agent.py'
        ]
        
        all_exist = True
        for file_path in required_files:
            if Path(file_path).exists():
                self.success.append(f"✅ {file_path} - знайдено")
            else:
                self.issues.append(f"❌ {file_path} - не знайдено")
                all_exist = False
        
        return all_exist
    
    def run_all_checks(self):
        """Запуск всіх перевірок"""
        print("=" * 60)
        print("🔍 ПЕРЕВІРКА СТАТУСУ СИСТЕМИ AI-TRADER")
        print("=" * 60)
        print()
        
        checks = [
            ("Версія Python", self.check_python_version),
            ("Залежності", self.check_dependencies),
            ("Конфігурація", self.check_config_file),
            ("Змінні середовища", self.check_env_file),
            ("Дані", self.check_data_files),
            ("Інструменти агента", self.check_agent_tools),
            ("Основні файли", self.check_main_files),
            ("MCP сервіси", self.check_mcp_services),
        ]
        
        results = {}
        for name, check_func in checks:
            try:
                results[name] = check_func()
                print()
            except Exception as e:
                self.issues.append(f"❌ Помилка під час перевірки {name}: {e}")
                results[name] = False
                print()
        
        return results
    
    def print_summary(self):
        """Виведення підсумку"""
        print("=" * 60)
        print("📊 ПІДСУМОК ПЕРЕВІРКИ")
        print("=" * 60)
        print()
        
        if self.success:
            print("✅ Успішні перевірки:")
            for item in self.success:
                print(f"   {item}")
            print()
        
        if self.warnings:
            print("⚠️  Попередження:")
            for item in self.warnings:
                print(f"   {item}")
            print()
        
        if self.issues:
            print("❌ Проблеми:")
            for item in self.issues:
                print(f"   {item}")
            print()
        
        # Загальний статус
        total_issues = len(self.issues)
        total_warnings = len(self.warnings)
        
        if total_issues == 0 and total_warnings == 0:
            print("🎉 Система готова до роботи!")
            return True
        elif total_issues == 0:
            print(f"✅ Система готова, але є {total_warnings} попереджень")
            return True
        else:
            print(f"⚠️  Знайдено {total_issues} проблем та {total_warnings} попереджень")
            print("   Будь ласка, виправте проблеми перед запуском системи")
            return False

def main():
    checker = SystemStatusChecker()
    checker.run_all_checks()
    is_ready = checker.print_summary()
    
    sys.exit(0 if is_ready else 1)

if __name__ == "__main__":
    main()
