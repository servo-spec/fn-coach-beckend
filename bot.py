import os
import threading
import random
import datetime
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import database as db

TOKEN = os.environ.get("TELEGRAM_TOKEN", "ВАШ_ТОКЕН")
WEBAPP_URL = "https://servo-spec.github.io/fn-coach/"

app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "Bot is running", 200

# ... (Все API роуты и TRAININGS оставляем как было) ...
# ВСТАВЬ СЮДА ВСЕ @app.route ИЗ ПРЕДЫДУЩЕГО КОДА (они не меняются)

# ============ БОТ ============
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎮 Открыть Mini App", web_app={"url": WEBAPP_URL})]]
    await update.message.reply_text(
        "Привет! Я твой тренер по Fortnite 🎮\nНажми на кнопку ниже:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def run_bot():
    print(">>> [1] БОТ ЗАПУСКАЕТСЯ В ФОНЕ <<<", flush=True)
    try:
        # Пытаемся создать приложение
        print(">>> [2] ПЫТАЮСЬ ПОДКЛЮЧИТЬСЯ К TELEGRAM... <<<", flush=True)
        application = Application.builder().token(TOKEN).build()
        
        # Добавляем хендлеры
        application.add_handler(CommandHandler("start", start))
        
        print(">>> [3] УСПЕХ! ОТПРАВЛЯЮ ЗАПРОС В TELEGRAM (run_polling) <<<", flush=True)
        # В новых версиях run_polling() - это асинхронная функция, 
        # но библиотека сама её запускает через свой event loop.
        application.run_polling()
        
    except Exception as e:
        # Выводим ошибку ЯРКО и сразу
        print(f"\n\n❌❌❌ ОШИБКА БОТА ❌❌❌", flush=True)
        print(f"ТИП ОШИБКИ: {type(e).__name__}", flush=True)
        print(f"ТЕКСТ ОШИБКИ: {e}", flush=True)
        print(f"❌❌❌ КОНЕЦ ОШИБКИ ❌❌❌\n\n", flush=True)

if __name__ == "__main__":
    print(">>> [0] СТАРТ ПРИЛОЖЕНИЯ (FLASK) <<<", flush=True)
    db.init()
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
