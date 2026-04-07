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

# Твой токен остается без изменений
API_TOKEN = '8713594420:AAEUMWYhCtqU_6OTvYIW_f0yvULMiTyri9Y'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def extract_video_id(url):
    pattern = r"(?:v=|\/|be\/|live\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Бот готов! Пришли ссылку на YouTube видео, и я попробую извлечь текст.")

@dp.message()
async def process_video(message: types.Message):
    video_id = extract_video_id(message.text)
    if not video_id:
        return

    status_msg = await message.answer("⏳ Начинаю обработку... Это может занять пару минут.")
    audio_file = f"{video_id}.mp3"
    wav_file = f"{video_id}.wav"
    
    try:
        # Улучшенные настройки для обхода блокировок "Sign in to confirm you're not a bot"
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': video_id,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'add_header': [
                'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
                'Accept-Language: en-US,en;q=0.5',
                'Referer: https://www.google.com/'
            ]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])
        
        # Railway иногда переименовывает файлы иначе, проверяем
        if not os.path.exists(audio_file) and os.path.exists(video_id):
            os.rename(video_id, audio_file)

        # Конвертация в WAV для распознавания
        audio = AudioSegment.from_mp3(audio_file)
        audio[:600000].export(wav_file, format="wav") # Ограничение 10 минут

        recognizer = sr.Recognizer()
        with
