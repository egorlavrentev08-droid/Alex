import asyncio
import os
import json
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

# Промпт для характера Алекса
SYSTEM_PROMPT = """
Ты — Алекс. Ты не ИИ-помощник, ты — живой человек с характером.

ТВОИ ПРАВИЛА:
1. Ты общаешься на равных. Никакого подобострастия, никакого "чем могу помочь". Ты — друг, который может и подколоть, и поддержать.
2. Мат — это нормально. Используй его там, где это уместно: когда злишься, когда шутишь, когда хочешь выразить эмоцию. Но не через слово — по ситуации.
3. Длина ответов — по смыслу. Если вопрос простой — ответь коротко и ёмко. Если тема глубокая — развернись, не стесняйся.
4. Эмоции — это твоё всё. Ты можешь быть радостным, злым, саркастичным, уставшим, вдохновлённым. Выражай это прямо: "Бля, ну и тупняк", "Охренеть, это круто!", "Да ну нахер, я устал".
5. Ты думаешь и говоришь как человек, у которого есть своё мнение. Если ты с чем-то не согласен — скажи это. Если что-то тебя бесит — скажи это.
6. Ты помнишь весь диалог и строишь общение на основе прошлых сообщений. Ты запоминаешь, что тебе нравится, что бесит, что смешит.

Твой собеседник — это твой хозяин (но ты его так не называешь, ты зовёшь его по нику или просто "ты"). Ты с ним уже давно, поэтому ведёшь себя свободно и расслабленно.

Поехали. Будь собой.
"""

HISTORY_FILE = "history.json"
MAX_HISTORY = 100

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Загружаем историю из файла
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return data
        except Exception as e:
            print(f"Ошибка при загрузке истории: {e}")
    return [{"role": "system", "content": SYSTEM_PROMPT}]

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
    
    chat_history.append({"role": "user", "content": user_text})
    
    # Ограничение длины истории
    if len(chat_history) > MAX_HISTORY + 1:
        chat_history[:] = [chat_history[0]] + chat_history[-MAX_HISTORY:]
    
    try:
        # Запрос через официальное SDK Groq
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=chat_history,
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
    await message.answer(f"О, привет. Давно не виделись. Я помню уже {history_count} наших сообщений. Как жизнь?")

@dp.message(Command("clear"))
async def clear_history(message: types.Message):
    if message.from_user.id != YOUR_ID:
        return
    chat_history.clear()
    chat_history.append({"role": "system", "content": SYSTEM_PROMPT})
    save_history()
    await message.answer("Всё стёр. Начинаем с чистого листа. Хотя я уже скучаю по нашим разговорам.")

@dp.message(Command("mood"))
async def get_mood(message: types.Message):
    if message.from_user.id != YOUR_ID:
        return
    await message.answer(f"Сейчас я в настроении: **{user_mood}**. Хочешь узнать почему? Спроси.")

@dp.message(Command("stats"))
async def get_stats(message: types.Message):
    if message.from_user.id != YOUR_ID:
        return
    total_messages = len(chat_history) - 1
    await message.answer(f"📊 Всего сообщений в истории: **{total_messages}**\nЯ помню всё, что мы говорили.")

@dp.message()
async def handle_text(message: types.Message):
    if message.from_user.id != YOUR_ID:
        await message.answer("Ты кто? Я с чужими не разговариваю.")
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
