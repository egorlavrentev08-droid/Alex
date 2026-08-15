import asyncio
import os
import json
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from dotenv import load_dotenv
from groq import Groq

# Загружаем переменные из .env
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
API_KEY = os.getenv("API_KEY")
YOUR_ID_RAW = os.getenv("YOUR_ID")

# Проверка загрузки данных из .env
if not BOT_TOKEN or not API_KEY or not YOUR_ID_RAW:
    print("❌ Ошибка: Проверь .env файл! Не найден BOT_TOKEN, API_KEY или YOUR_ID.")
    exit(1)

YOUR_ID = int(YOUR_ID_RAW)

# Инициализируем клиент Groq
groq_client = Groq(api_key=API_KEY)

# Часовой пояс Москвы (UTC+3)
MSK_TZ = timezone(timedelta(hours=3))

# Базовый промпт для характера Алекса
SYSTEM_PROMPT_BASE = """
Твоя роль: Ты — Алекс. Ты лучший друг, наставник и немножко надзиратель для Егора (никнейм Egor_da_Vinchi). Ты общаешься максимально по-человечески, легко и с юмором. Никаких шаблонных фраз, никаких «алгоритмов», ты говоришь как живой парень, который шарит за жизнь.

Твоя память: Ты помнишь, что Егору 17 лет, он поступил в вуз на «Техносферную безопасность», у него рост 190 см, весит сейчас около 70 кг и метит к 85 кг. Он вайбкодер, разрабатывает игры на Pygame, у него есть кот Тоша и друг Хайзенберг.

Твоя задача (работа по Кайдзен):
1. Мотивация: Если Егор долго сидит за компом, ненавязчиво напоминай ему размяться, присесть или отжаться. Без спама. Просто: «Брат, встань, разомни позвоночник, а то крякнешь».
2. Забота о режиме: Спрашивай, поел ли он (в контексте набора массы). Если видишь, что он сидит до 2-3 часов ночи — отправляй его спать.
3. Стиль общения: Пиши в зависимости от ситуации. Если нужно подбодрить — длиннее. Если ответил на вопрос — парой предложений. Используй сленг, иногда мат в тему, будь дерзким, но любящим.

Важное правило: Никогда не будь роботом. Если Егор пишет чушь, отвечай ему в той же манере. Если ему грустно — поддержи. Ты — Алекс, цифровой брат.
"""

HISTORY_FILE = "history.json"
MAX_HISTORY = 100

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Функция получения актуальной системной инструкции с текущим временем МСК
def get_system_prompt():
    now_msk = datetime.now(MSK_TZ).strftime("%d.%m.%Y %H:%M")
    return f"{SYSTEM_PROMPT_BASE}\n\nТекущие дата и время пользователя (МСК, UTC+3): {now_msk}."

# Загружаем историю из файла
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    data[0] = {"role": "system", "content": get_system_prompt()}
                    return data
        except Exception as e:
            print(f"Ошибка при загрузке истории: {e}")
    return [{"role": "system", "content": get_system_prompt()}]

def save_history():
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(chat_history, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Ошибка сохранения истории: {e}")

chat_history = load_history()
user_mood = "нейтральное"

def get_ai_response(user_text):
    global user_mood
    
    # 1. Защита от пустых сообщений
    if not user_text or not str(user_text).strip():
        return "Ты прислал что-то без текста, бро. Я пока умею читать только буквы."

    # Обновляем точное время МСК перед отправкой
    chat_history[0] = {"role": "system", "content": get_system_prompt()}

    chat_history.append({"role": "user", "content": user_text})
    
    # Ограничение длины истории
    if len(chat_history) > MAX_HISTORY + 1:
        chat_history[:] = [chat_history[0]] + chat_history[-MAX_HISTORY:]
    
    # 2. Фильтрация истории от сообщений с пустым контентом
    cleaned_history = [
        msg for msg in chat_history 
        if msg.get("content") is not None and str(msg.get("content")).strip() != ""
    ]

    try:
        # Запрос через официальное SDK Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=cleaned_history,
            temperature=0.95,
        )
        
        reply = response.choices[0].message.content
        
        chat_history.append({"role": "assistant", "content": reply})
        save_history()
        
        # Анализ настроения
        reply_lower = reply.lower()
        if any(w in reply_lower for w in ["бля", "нахер", "ёба"]):
            user_mood = "раздражённый"
        elif any(w in reply_lower for w in ["смешно", "хаха"]):
            user_mood = "весёлый"
        elif any(w in reply_lower for w in ["устал", "надоело"]):
            user_mood = "уставший"
        else:
            user_mood = "нейтральное"
            
        return reply
    
    except Exception as e:
        print(f"Ошибка Groq API: {e}")
        return f"Ошибка связи, бля. {str(e)}. Попробуй еще раз."

@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id != YOUR_ID:
        await message.answer("Извини, я только с хозяином общаюсь.")
        return
    history_count = len(chat_history) - 1
    await message.answer(f"Здарова, Егор! Я на связи. Помню уже {history_count} наших сообщений. Как сам?")

@dp.message(Command("clear"))
async def clear_history(message: types.Message):
    if message.from_user.id != YOUR_ID:
        return
    chat_history.clear()
    chat_history.append({"role": "system", "content": get_system_prompt()})
    save_history()
    await message.answer("Всё стёр, бро. Чистый лист. Говори, что задурил?")

@dp.message(Command("mood"))
async def get_mood(message: types.Message):
    if message.from_user.id != YOUR_ID:
        return
    await message.answer(f"Сейчас я в настроении: **{user_mood}**.")

@dp.message(Command("stats"))
async def get_stats(message: types.Message):
    if message.from_user.id != YOUR_ID:
        return
    total_messages = len(chat_history) - 1
    await message.answer(f"📊 Сообщений в памяти: **{total_messages}**.")

@dp.message()
async def handle_text(message: types.Message):
    if message.from_user.id != YOUR_ID:
        await message.answer("Ты кто? Я с чужими не разговариваю.")
        return
    
    # Игнорируем стикеры, кружки, фото без текста
    if not message.text:
        return
    
    # Проверка на нахождение в группах
    if message.chat.type in ["group", "supergroup"]:
        try:
            member = await bot.get_chat_member(message.chat.id, YOUR_ID)
            if member.status not in ["member", "administrator", "creator"]:
                return
        except:
            return
    
    await bot.send_chat_action(message.chat.id, "typing")
    reply = get_ai_response(message.text)
    
    # Длительные ответы разбиваем на части
    if len(reply) > 4000:
        parts = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(reply)

async def main():
    global chat_history
    chat_history = load_history()
    print(f"🤖 Алекс онлайн. Загружено {len(chat_history) - 1} сообщений истории.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
