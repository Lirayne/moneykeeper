"""
MoneyKeeper Bot - Имитация Telegram-бота для учёта личных финансов
Версия: 0.8-initial (с багами)

Запуск: python bot.py
Команды: /start, /add 150 кофе, /today, /week, /month и т.д.
"""

import json
import os
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# ===== ХРАНЕНИЕ ДАННЫХ В ПАМЯТИ (имитация БД) =====
class InMemoryDB:
    """Имитация базы данных в памяти (без реальной БД)"""

    CATEGORIES_FILE = "categories.json"

    def __init__(self):
        self.users: Dict[int, dict] = {}
        self.expenses: List[dict] = []
        self.categories: Dict[int, List[str]] = self._load_categories()
        self.next_expense_id = 1

    def _load_categories(self) -> Dict[int, List[str]]:
        """Загружает категории из файла"""
        from collections import defaultdict

        if os.path.exists(self.CATEGORIES_FILE):
            try:
                with open(self.CATEGORIES_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    return defaultdict(
                        lambda: ["🍔 Еда", "🚕 Транспорт", "🎬 Развлечения"],
                        {int(k): v for k, v in saved.items()}
                    )
            except (json.JSONDecodeError, ValueError):
                pass

        return defaultdict(lambda: ["🍔 Еда", "🚕 Транспорт", "🎬 Развлечения"])

    def _save_categories(self) -> None:
        """Сохраняет категории в файл"""
        to_save = {str(k): v for k, v in self.categories.items()}
        with open(self.CATEGORIES_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, ensure_ascii=False, indent=2)

    def add_user(self, user_id: int, username: str, first_name: str) -> None:
        if user_id not in self.users:
            self.users[user_id] = {
                "username": username,
                "first_name": first_name,
                "registered_at": datetime.now()
            }

    def add_expense(self, user_id: int, amount: float, category: str, description: str = "") -> int:
        expense = {
            "id": self.next_expense_id,
            "user_id": user_id,
            "amount": amount,
            "category": category,
            "description": description,
            "date": datetime.now()
        }
        self.expenses.append(expense)
        self.next_expense_id += 1
        return expense["id"]

    def get_expenses(self, user_id: int, start_date: datetime = None, end_date: datetime = None) -> List[dict]:
        result = [e for e in self.expenses if e["user_id"] == user_id]

        if start_date:
            result = [e for e in result if e["date"] >= start_date]
        if end_date:
            result = [e for e in result if e["date"] <= end_date]

        return sorted(result, key=lambda x: x["date"], reverse=True)

    def delete_expense(self, expense_id: int, user_id: int) -> bool:
        for i, exp in enumerate(self.expenses):
            if exp["id"] == expense_id and exp["user_id"] == user_id:
                self.expenses.pop(i)
                return True
        return False

    def add_category(self, user_id: int, category_name: str) -> None:
        # БАГ #8 ИСПРАВЛЕН: Категория сохраняется в файл
        if category_name not in self.categories[user_id]:
            self.categories[user_id].append(category_name)
            self._save_categories()

    def get_categories(self, user_id: int) -> List[str]:
        return self.categories[user_id]


# Глобальный экземпляр БД
db = InMemoryDB()
current_user_id = 12345  # Имитация текущего пользователя


# ===== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =====
def get_date_range(period: str) -> Tuple[datetime, datetime]:
    """Возвращает начальную и конечную дату для периода"""
    now = datetime.now()
    
    if period == "today":
        start = datetime(now.year, now.month, now.day, 0, 0, 0)
        end = datetime(now.year, now.month, now.day, 23, 59, 59)
    elif period == "week":
        # БАГ #4: Неправильный расчёт начала недели
        start = now - timedelta(days=now.weekday())
        start = datetime(start.year, start.month, start.day, 0, 0, 0)
        end = now
    elif period == "month":
        start = datetime(now.year, now.month, 1, 0, 0, 0)
        end = now
    else:
        start = now - timedelta(days=30)
        end = now
    
    return start, end


def format_currency(amount: float) -> str:
    """Форматирует сумму с символом рубля"""
    return f"{amount:.2f} ₽"


def format_expense_line(expense: dict, show_date: bool = False) -> str:
    """Форматирует одну запись расхода"""
    time_str = expense["date"].strftime("%H:%M")
    date_str = expense["date"].strftime("%d.%m") if show_date else ""
    desc_str = f" ({expense['description']})" if expense["description"] else ""
    
    if show_date:
        return f"• {date_str} {time_str} - {expense['category']}: {format_currency(expense['amount'])}{desc_str}"
    else:
        return f"• {time_str} - {expense['category']}: {format_currency(expense['amount'])}{desc_str}"


# ===== ОСНОВНЫЕ ФУНКЦИИ БОТА =====
def handle_start():
    """Обработчик /start"""
    db.add_user(current_user_id, "user", "Пользователь")
    
    return (
        "👋 Привет, Пользователь!\n\n"
        "Я помогу тебе вести учёт расходов.\n\n"
        "📌 Доступные команды:\n"
        "/add <сумма> <категория> [описание] - добавить расход\n"
        "/today - показать расходы за сегодня\n"
        "/week - статистика за неделю\n"
        "/month - статистика за текущий месяц\n"
        "/categories - список твоих категорий\n"
        "/add_category <название> - добавить категорию\n"
        "/delete <id> - удалить расход\n"
        "/export - экспорт данных (JSON)\n"
        "/help - помощь"
    )


def handle_add(args: List[str]):
    """
    Добавление расхода: /add 150 кофе
    БАГ #6: Не обрабатывает случай, когда аргументов меньше 2
    БАГ #7: Не проверяет, что сумма — число
    БАГ #2: Не проверяет, что amount > 0
    """
    if len(args) < 2:
        return "❌ Ошибка: нужно указать сумму и категорию.\nПример: /add 150 кофе"

    try:
        amount = float(args[0].replace(",", "."))
        if not math.isfinite(amount):
            raise ValueError
    except ValueError:
        return "❌ Ошибка: сумма должна быть корректным числом"
    
    # БАГ #2: Нет проверки на отрицательную сумму
    category = args[1]
    description = " ".join(args[2:]) if len(args) > 2 else ""
    
    expense_id = db.add_expense(current_user_id, amount, category, description)
    
    return f"✅ Добавлено: {format_currency(amount)} на категорию «{category}»\n#{expense_id}"


def handle_today():
    """Показать расходы за сегодня"""
    start, end = get_date_range("today")
    expenses = db.get_expenses(current_user_id, start, end)
    
    total = sum(e["amount"] for e in expenses)
    
    if not expenses:
        return f"📅 *Расходы за сегодня*: {format_currency(total)}\n\n📭 Нет расходов"
    
    message = f"📅 *Расходы за сегодня*: {format_currency(total)}\n\n"
    message += "\n".join(format_expense_line(e) for e in expenses)
    
    return message


def handle_week():
    """Показать статистику за неделю"""
    start, end = get_date_range("week")
    expenses = db.get_expenses(current_user_id, start, end)
    
    total = sum(e["amount"] for e in expenses)
    
    if not expenses:
        return f"📊 *Неделя*: {format_currency(total)}\n\n📭 Нет расходов"
    
    message = f"📊 *Неделя*: {format_currency(total)}\n\n"
    message += "\n".join(format_expense_line(e, show_date=True) for e in expenses)
    
    return message


def handle_month():
    """
    Показать статистику за месяц
    БАГ #5: Возвращает данные за прошлый месяц
    """
    now = datetime.now()
    # БАГ: показывает прошлый месяц
    first_day_of_month = datetime(now.year, now.month - 1 if now.month > 1 else 12, 1)
    if now.month == 1:
        first_day_of_month = datetime(now.year - 1, 12, 1)
    
    expenses = db.get_expenses(current_user_id, first_day_of_month, now)
    
    # Группировка по категориям
    stats = defaultdict(float)
    for e in expenses:
        stats[e["category"]] += e["amount"]
    
    if not stats:
        return "📭 Нет расходов за месяц"
    
    total = sum(stats.values())
    message = f"📆 *Статистика за месяц*: {format_currency(total)}\n\n"
    
    for category, amount in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        message += f"• {category}: {format_currency(amount)}\n"
    
    return message


def handle_categories():
    """
    Показать список категорий
    БАГ #8: Категории не сохраняются между сессиями (но для имитации ок)
    """
    categories = db.get_categories(current_user_id)
    
    message = "📁 *Твои категории*\n\n" + "\n".join(f"• {cat}" for cat in categories)
    message += "\n\n➕ Добавить новую: /add_category <название>"
    
    return message


def handle_add_category(args: List[str]):
    """Добавить новую категорию"""
    if not args:
        return "❌ Укажи название категории: /add_category <название>"
    
    category_name = " ".join(args)
    db.add_category(current_user_id, category_name)
    
    return f"✅ Категория «{category_name}» добавлена!"


def handle_delete(args: List[str]):
    """
    Удалить расход по ID
    БАГ #10: Нет проверки, что ID существует
    """
    if not args:
        return "❌ Укажи ID расхода: /delete <id>"
    
    try:
        expense_id = int(args[0])
    except ValueError:
        return "❌ ID должен быть числом"
    
    if db.delete_expense(expense_id, current_user_id):
        return f"✅ Расход #{expense_id} удалён"
    else:
        return f"❌ Расход #{expense_id} не найден"


def handle_export():
    """
    Экспорт данных в JSON
    БАГ #9: Экспортирует всё подряд, без фильтрации
    """
    expenses = db.get_expenses(current_user_id)
    
    export_data = {
        "user": db.users.get(current_user_id, {}),
        "expenses": [
            {
                "id": e["id"],
                "amount": e["amount"],
                "category": e["category"],
                "description": e["description"],
                "date": e["date"].isoformat()
            }
            for e in expenses
        ],
        "categories": db.get_categories(current_user_id)
    }
    
    json_str = json.dumps(export_data, indent=2, ensure_ascii=False, default=str)
    
    # Имитация файла
    return f"📄 *Экспорт данных*\n\n```json\n{json_str[:1500]}\n```\n(первые 1500 символов)"


def handle_unknown(command: str):
    """Неизвестная команда"""
    return f"❌ Неизвестная команда: {command}\nНапиши /help для списка команд"


# ===== ОБРАБОТЧИК СООБЩЕНИЙ (как в Telegram) =====
def process_message(text: str) -> str:
    """
    Обрабатывает входящее сообщение и возвращает ответ
    """
    text = text.strip()
    
    if not text:
        return "❌ Пустое сообщение"
    
    # Обработка команд
    if text.startswith("/"):
        parts = text.split()
        command = parts[0].lower()
        args = parts[1:]
        
        if command == "/start":
            return handle_start()
        elif command == "/help":
            return handle_start()  # /help показывает то же, что /start
        elif command == "/add":
            return handle_add(args)
        elif command == "/today":
            return handle_today()
        elif command == "/week":
            return handle_week()
        elif command == "/month":
            return handle_month()
        elif command == "/categories":
            return handle_categories()
        elif command == "/add_category":
            return handle_add_category(args)
        elif command == "/delete":
            return handle_delete(args)
        elif command == "/export":
            return handle_export()
        else:
            return handle_unknown(command)
    else:
        # Обработка обычного сообщения (быстрое добавление)
        # БАГ #11: Не проверяет, что первое слово — число
        parts = text.split(maxsplit=2)
        
        if len(parts) >= 2:
            try:
                amount = float(parts[0])
                category = parts[1]
                description = parts[2] if len(parts) > 2 else ""
                
                expense_id = db.add_expense(current_user_id, amount, category, description)
                return f"✅ Добавлено: {format_currency(amount)} на «{category}»\n#{expense_id}"
            except ValueError:
                return "❌ Не понял. Используй /add или просто «сумма категория»"
        else:
            return "❌ Не понял. Напиши /help для списка команд"


# ===== ЗАПУСК ИМИТАЦИИ БОТА =====
def main():
    """Запуск имитации бота в консоли"""
    print("=" * 50)
    print("🤖 MoneyKeeper Bot (имитация)")
    print("=" * 50)
    print("Вводи команды как в Telegram:")
    print("  /start - начать")
    print("  /add 150 кофе - добавить расход")
    print("  /today - расходы за сегодня")
    print("  /week - за неделю")
    print("  /month - за месяц")
    print("  /categories - список категорий")
    print("  /add_category еда - новая категория")
    print("  /delete 1 - удалить расход")
    print("  /export - выгрузить JSON")
    print("  /exit - выход")
    print("=" * 50)
    print()
    
    # Автоматический /start при запуске
    print(handle_start())
    print()
    
    while True:
        try:
            user_input = input("📱 Вы: ").strip()
            
            if user_input.lower() in ["/exit", "/quit", "exit", "quit"]:
                print("👋 До свидания!")
                break
            
            if not user_input:
                continue
            
            response = process_message(user_input)
            print(f"🤖 Бот: {response}\n")
            
        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            break
        except Exception as e:
            print(f"❌ Ошибка: {e}\n")


if __name__ == "__main__":
    main()