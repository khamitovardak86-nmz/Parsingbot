import logging
import asyncio
import os
import re
import sys

# Автоматическая проверка и установка библиотек
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

# ТВОЙ НОВЫЙ ТОКЕН
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
    await message.reply("Бот обновлен с новым ключом! Присылай ссылку на видео.")

@dp.message()
async def process_video(message: types.Message):
    video_id = extract_video_id(message.text)
    if not video_id:
        return

    status_msg = await message.answer("⏳ Начинаю обработку... Ищу аудио-дорожку.")
    audio_file = f"{video_id}.mp3"
    wav_file = f"{video_id}.wav"
    
    try:
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
            'geo_bypass': True,
            'add_header': [
                'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
                'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language: ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7'
            ]
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])
        
        if not os.path.exists(audio_file) and os.path.exists(video_id):
            os.rename(video_id, audio_file)

        # Конвертация (требует ffmpeg в системе)
        audio = AudioSegment.from_mp3(audio_file)
        audio[:600000].export(wav_file, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data, language="ru-RU")
            except:
                text = recognizer.recognize_google(audio_data, language="en-US")

        await status_msg.edit_text(f"✅ Текст извлечен:\n\n{text[:4000]}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Проблема: {str(e)[:150]}")
    
    finally:
        for f in [audio_file, wav_file, video_id]:
            if os.path.exists(f):
                os.remove(f)

async def main():
    # Очистка очереди перед стартом
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен с новым токеном!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
