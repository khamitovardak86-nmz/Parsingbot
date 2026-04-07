import asyncio
import re
import os
from aiogram import Bot, Dispatcher, F, types
from youtube_transcript_api import YouTubeTranscriptApi
import requests

# ТВОЙ ТОКЕН
API_TOKEN = '8688129970:AAFTQT1rtijdgox08fKQcl55PLMNRlKyBCw'

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def get_summary(text):
    """Отправляем текст нейросети для краткого изложения на РУССКОМ"""
    try:
        # Промпт заставляет нейросеть выдать суть на русском
        prompt = f"Проанализируй этот текст (это субтитры видео) и составь краткий конспект на русском языке. Выдели главные мысли по пунктам. Текст: {text[:5000]}"
        
        response = requests.post(
            "https://api.clashai.eu/v1/chat/completions",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": prompt}]
            },
            timeout=35
        )
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"⚠️ Нейросеть не смогла сделать пересказ, но текст получен. Вот начало:\n\n{text[:500]}..."

@dp.message(F.text.contains("youtube.com/") | F.text.contains("youtu.be/"))
async def handle_video(message: types.Message):
    url = message.text
    # Регулярка для поиска ID видео
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", url)
    
    if not video_id_match:
        await message.answer("❌ Не могу распознать ссылку.")
        return
        
    video_id = video_id_match.group(1)
    status_msg = await message.answer("⏳ Ищу и перевожу субтитры...")

    try:
        # Получаем все доступные субтитры для видео
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        try:
            # 1. Пробуем найти родные русские субтитры
            transcript = transcript_list.find_transcript(['ru'])
        except:
            # 2. Если русских нет, берем ЛЮБЫЕ другие (англ, нем и т.д.) 
            # и просим YouTube перевести их на русский (функция .translate)
            first_transcript = next(iter(transcript_list))
            transcript = first_transcript.translate('ru')

        # Загружаем текст
        data = transcript.fetch()
        full_text = " ".join([i['text'] for i in data])
        
        await status_msg.edit_text("🤖 Перевожу и выделяю суть...")
        
        summary = get_summary(full_text)
        await message.answer(f"📋 **Краткий пересказ видео (на русском):**\n\n{summary}")
        await status_msg.delete()

    except Exception as e:
        print(f"Ошибка: {e}")
        await status_msg.edit_text("❌ У этого видео вообще нет субтитров (даже автоматических). Нечего парсить.")

async def main():
    print("Бот запущен и готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
