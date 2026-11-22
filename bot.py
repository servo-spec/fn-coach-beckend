import os
import threading
import random
import datetime
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============ НАСТРОЙКА ============
TOKEN = os.environ.get("TELEGRAM_TOKEN", "ВАШ_ТОКЕН")

# ============ ЗАГЛУШКА ДЛЯ RENDER ============
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "Bot is running", 200

# ============ ДАННЫЕ ============
TRAININGS = {
    "aim": {"name": "🎯 Аим и стрельба", "steps": [
        ("Разминка: Creative 1v1 / Aim Lab", "10 мин"),
        ("Тренировка спрея", "15 мин"),
        ("Zone Wars / Box Fights", "15 мин"),
        ("Разбор реплея", "10 мин"),
    ]},
    "build": {"name": "🏗️ Билдинг", "steps": [
        ("90s, рампы, базовые комбо", "10 мин"),
        ("Редактирование + перестройка", "15 мин"),
        ("BHE / Free Build", "15 мин"),
        ("Разбор клипа", "10 мин"),
    ]},
    "game_sense": {"name": "🧠 Игровое мышление", "steps": [
        ("Матч про-игрока с разбором", "20 мин"),
        ("Разбор своих смертей", "15 мин"),
        ("План на 3 ранкед-матча", "10 мин"),
    ]},
    "ranked": {"name": "🏆 Ранкед-сессия", "steps": [
        ("Разминка перед ранкедом", "15 мин"),
        ("Ранкед: фокус на 1 ошибке", "60 мин"),
        ("Перерыв", "15 мин"),
        ("Разбор", "10 мин"),
    ]},
}

RANKED_ADVICE = [
    "Не играй на усталости — 3 поражения подряд = стоп на 30 мин.",
    "Перед ранкедом выбери ОДНУ ошибку и следи только за ней.",
    "Лучший ранг берётся за 2-3 короткие сессии.",
    "Если тильтуешь — закрой игру, разбери 1 смерть в реплее.",
]

# ============ МЕНЮ ============
def main_menu():
    kb = [
        [InlineKeyboardButton("🏋️ Тренировка на сегодня", callback_data="today")],
        [InlineKeyboardButton("📅 Расписание на неделю", callback_data="week")],
        [InlineKeyboardButton("🏆 Когда идти в ранкед", callback_data="ranked")],
    ]
    return InlineKeyboardMarkup(kb)

# ============ БОТ ============
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я твой тренер по Fortnite 🎮\nВыбери действие:",
        reply_markup=main_menu()
    )

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "today":
        keys = ["aim", "build", "game_sense", "ranked", "aim", "build", "rest"]
        k = keys[datetime.date.today().weekday()]
        if k == "rest":
            text = "😴 *Отдых*\n\nСегодня отдыхай или разбери реплеи."
        else:
            plan = TRAININGS[k]
            text = f"*{plan['name']}*\n\n"
            for i, (step, t) in enumerate(plan["steps"], 1):
                text += f"{i}. {step} — _{t}_\n"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

    elif data == "week":
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        keys = ["aim", "build", "game_sense", "ranked", "aim", "build", "rest"]
        text = "📅 *План на неделю*\n\n"
        for d, k in zip(days, keys):
            name = "😴 отдых" if k == "rest" else TRAININGS[k]["name"]
            text += f"*{d}*: {name}\n"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

    elif data == "ranked":
        advice = random.choice(RANKED_ADVICE)
        text = (
            "🏆 *Готов ли ты в ранкед?*\n\n"
            "☑️ Разминка 10-15 мин\n"
            "☑️ Выбрана 1 ошибка для фокуса\n"
            "☑️ Ты не уставший\n"
            "☑️ План: 3 матча → перерыв\n\n"
            f"💡 _{advice}_"
        )
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

def run_bot():
    print("=== БОТ ЗАПУСКАЕТСЯ ===", flush=True)
    try:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button))
        print("=== БОТ УСПЕШНО СОЗДАН ===", flush=True)
        application.run_polling()
    except Exception as e:
        print(f"!!! ОШИБКА БОТА: {e} !!!", flush=True)

# ============ ЗАПУСК ============
if __name__ == "__main__":
    print("=== СТАРТ FLASK ===", flush=True)
    port = int(os.environ.get("PORT", 10000))
    
    # Flask в фоне (чтобы Render видел порт)
    flask_thread = threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    
    # Бот в главном потоке
    run_bot()
