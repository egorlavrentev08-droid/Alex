import asyncio
import requests
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from datetime import datetime

# --- НАСТРОЙКИ ---
BOT_TOKEN = "8885099048:AAGryyJjIED0x3LH-SXW0ncTCHdRJUwVx04"
API_KEY = "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"
API_URL = "https://api.groq.com/openai/v1/chat/completions"

YOUR_ID = 6595788533

# МОЩНЫЙ ПРОМПТ ДЛЯ ХАРАКТЕРА
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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# История с метаданными (эмоции, время)
chat_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# Храним последнее эмоциональное состояние (для контекста)
user_mood = "нейтральное"

def get_ai_response(user_text):
    """Отправляет запрос с полной историей и динамической настройкой"""
    global user_mood
    
    # Добавляем сообщение пользователя в историю
    chat_history.append({"role": "user", "content": user_text})
    
    # Ограничиваем историю, чтобы не переполнять (последние 50 сообщений)
    if len(chat_history) > 50:
        # Оставляем system + последние 49 сообщений
        chat_history[:] = [chat_history[0]] + chat_history[-49:]
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "mixtral-8x7b-32768",  # Можно поменять на llama3-70b-8192
        "messages": chat_history,
        "temperature": 0.95,  # Высокая температура = больше креатива и эмоций
        "top_p": 0.9,
        "max_tokens": 500,  # Максимальная длина ответа
        "presence_penalty": 0.6,  # Поощряет новые темы
        "frequency_penalty": 0.3,  # Не даёт повторяться
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=45)
        response.raise_for_status()
        reply = response.json()["choices"][0]["message"]["content"]
        
        # Сохраняем ответ в историю
        chat_history.append({"role": "assistant", "content": reply})
        
        # Анализируем эмоциональный тон (простая эвристика)
        if "бля" in reply.lower() or "нахер" in reply.lower() or "ёба" in reply.lower():
            user_mood = "раздражённый"
        elif "смешно" in reply.lower() or "хаха" in reply.lower():
            user_mood = "весёлый"
        elif "устал" in reply.lower() or "надоело" in reply.lower():
            user_mood = "уставший"
        else:
            user_mood = "нейтральное"
            
        return reply
    except Exception as e:
        return f"Ошибка связи, бля. {str(e)}. Давай попробуем ещё раз."

@dp.message(Command("start"))
async def start(message: types.Message):
    if message.from_user.id != YOUR_ID:
        await message.answer("Извини, я только с хозяином общаюсь.")
        return
    await message.answer("О, привет. Давно не виделись. Как жизнь? Только не говори, что скучно.")

@dp.message(Command("clear"))
async def clear_history(message: types.Message):
    if message.from_user.id != YOUR_ID:
        return
    chat_history.clear()
    chat_history.append({"role": "system", "content": SYSTEM_PROMPT})
    await message.answer("Всё стёр. Начинаем с чистого листа. Хотя я уже скучаю по нашим разговорам.")

@dp.message(Command("mood"))
async def get_mood(message: types.Message):
    if message.from_user.id != YOUR_ID:
        return
    await message.answer(f"Сейчас я в настроении: **{user_mood}**. Хочешь узнать почему? Спроси.")

@dp.message()
async def handle_text(message: types.Message):
    # 1. Только хозяин
    if message.from_user.id != YOUR_ID:
        await message.answer("Ты кто? Я с чужими не разговариваю.")
        return
    
    # 2. Если группа — проверяем, есть ли хозяин
    if message.chat.type in ["group", "supergroup"]:
        try:
            member = await bot.get_chat_member(message.chat.id, YOUR_ID)
            if member.status not in ["member", "administrator", "creator"]:
                return
        except:
            return
    
    # 3. Отвечаем
    await bot.send_chat_action(message.chat.id, "typing")
    reply = get_ai_response(message.text)
    
    # Разбиваем длинные сообщения (если ответ > 4096 символов)
    if len(reply) > 4000:
        parts = [reply[i:i+4000] for i in range(0, len(reply), 4000)]
        for part in parts:
            await message.answer(part)
    else:
        await message.answer(reply)

async def main():
    print("Алекс онлайн. Без цензуры, с душой.")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
