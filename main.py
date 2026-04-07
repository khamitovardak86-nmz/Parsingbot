import logging
import asyncio
import os
import re
import sys

# Попытка импорта библиотек
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

# Твой актуальный токен
API_TOKEN = '8713594420:AAF80KdIxlsVMNTIONQ2kuXe_jFDwJCOcj4'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def extract_video_id(url):
    pattern = r"(?:v=|\/|be\/|live\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Бот готов! Пришли ссылку, и я постараюсь извлечь текст.")

@dp.message()
async def process_video(message: types.Message):
    video_id = extract_video_id(message.text)
    if not video_id:
        return

    status_msg = await message.answer("⏳ Работаю над видео...")
    audio_file = f"{video_id}.mp3"
    wav_file = f"{video_id}.wav"
    
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': video_id,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '64', # Снизил качество для экономии памяти
            }],
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'add_header': [
                'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36'
            ]
        }
        
        # Скачивание
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])
        
        if not os.path.exists(audio_file) and os.path.exists(video_id):
            os.rename(video_id, audio_file)

        # Конвертация в WAV (здесь нужен ffmpeg)
        audio = AudioSegment.from_mp3(audio_file)
        # Берем только первые 3 минуты для теста, чтобы не "уронить" сервер
        audio[:180000].export(wav_file, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language="ru-RU")

        await status_msg.edit_text(f"✅ Результат:\n\n{text[:4000]}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: {str(e)[:150]}")
    
    finally:
        for f in [audio_file, wav_file, video_id]:
            if os.path.exists(f):
                try: os.remove(f)
                except: pass

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
