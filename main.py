import logging
import asyncio
import os
import re
import sys

# Проверка и установка библиотек
try:
    import speech_recognition as sr
    from pydub import AudioSegment
    import yt_dlp
except ImportError:
    os.system(f"{sys.executable} -m pip install yt-dlp SpeechRecognition pydub")
    import speech_recognition as sr
    from pydub import AudioSegment
    import yt_dlp

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ТВОЙ АБСОЛЮТНО НОВЫЙ ТОКЕН
API_TOKEN = '8713594420:AAExQByQgqCInIUWdvLU2rOvPFuZCILDdiM'

# Настройка логирования
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def extract_video_id(url):
    """Извлекает ID видео из ссылки YouTube"""
    pattern = r"(?:v=|\/|be\/|live\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Это твой новый Parsing Bot 777. Присылай ссылку на YouTube, и я попробую превратить видео в текст!")

@dp.message()
async def process_video(message: types.Message):
    video_id = extract_video_id(message.text)
    if not video_id:
        return

    status_msg = await message.answer("⏳ Начинаю работу со свежим токеном! Скачиваю звук...")

    audio_file = f"{video_id}.mp3"
    wav_file = f"{video_id}.wav"
    
    try:
        # 1. Скачивание аудио
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': video_id,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])
        
        if not os.path.exists(audio_file) and os.path.exists(video_id):
            os.rename(video_id, audio_file)

        await status_msg.edit_text("⏳ Звук получен. Конвертирую и расшифровываю...")

        # 2. Конвертация в WAV
        audio = AudioSegment.from_mp3(audio_file)
        audio[:600000].export(wav_file, format="wav")

        # 3. Распознавание
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language="ru-RU")
            except:
                text = recognizer.recognize_google(audio_data, language="en-US")

        if not text:
            await status_msg.edit_text("❌ Не удалось найти речь в этом видео.")
            return

        if len(text) > 4000:
            text = text[:4000] + "..."

        await status_msg.edit_text(f"✅ Готово!\n\n{text}")

    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await status_msg.edit_text(f"❌ Ошибка: {str(e)[:100]}. Проверь, добавлен ли ffmpeg в Nixpacks.")
    
    finally:
        for temp_file in [audio_file, wav_file, video_id]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

async def main():
    # Очистка очереди сообщений перед запуском
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("НОВЫЙ БОТ ЗАПУЩЕН!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
