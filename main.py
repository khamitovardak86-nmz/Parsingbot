import logging
import asyncio
import os
import re
import whisper
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import yt_dlp

API_TOKEN = '8688129970:AAHCOdltYIaVR3WMEYRRxhDH52AZ1up5Ec8'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Загружаем модель при старте (tiny - самая быстрая и легкая)
model = whisper.load_model("tiny")

def extract_video_id(url):
    pattern = r"(?:v=|\/|be\/|live\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Теперь я не просто ищу субтитры, я СЛУШАЮ видео. Пришли ссылку!")

@dp.message()
async def process_video(message: types.Message):
    video_id = extract_video_id(message.text)
    if not video_id: return

    status_msg = await message.answer("⏳ Скачиваю аудио и начинаю расшифровку (это может занять 1-2 минуты)...")

    file_path = f"{video_id}.mp3"
    
    try:
        # Скачиваем только аудио
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': file_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])

        # Нейросеть распознает текст
        result = model.transcribe(file_path)
        text = result['text']

        if len(text) > 4000:
            text = text[:4000] + "..."

        await status_msg.edit_text(f"✅ Готово! Текст видео:\n\n{text}")

    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text("❌ Ошибка при обработке видео. Возможно, оно слишком длинное для сервера.")
    
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
