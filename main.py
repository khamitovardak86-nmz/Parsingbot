import logging
import asyncio
import os
import re
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import yt_dlp

API_TOKEN = '8688129970:AAHCOdltYIaVR3WMEYRRxhDH52AZ1up5Ec8'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def extract_video_id(url):
    pattern = r"(?:v=|\/|be\/|live\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Теперь я использую облачное распознавание речи. Пришли ссылку на любое видео!")

@dp.message()
async def process_video(message: types.Message):
    video_id = extract_video_id(message.text)
    if not video_id: return

    status_msg = await message.answer("⏳ Скачиваю аудио дорожку...")

    audio_file = f"{video_id}.mp3"
    wav_file = f"{video_id}.wav"
    
    try:
        # 1. Скачиваем аудио через yt-dlp
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': video_id,
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '128'}],
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])
        
        if not os.path.exists(audio_file) and os.path.exists(video_id):
            os.rename(video_id, audio_file)

        await status_msg.edit_text("⏳ Распознаю речь через облако (это может занять время)...")

        # 2. Конвертируем в WAV (нужно для библиотеки распознавания)
        audio = AudioSegment.from_mp3(audio_file)
        # Берем первые 10 минут, чтобы не перегружать бесплатный сервер
        audio[:600000].export(wav_file, format="wav")

        # 3. Распознавание речи
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            recorded_audio = recognizer.record(source)
            # Используем Google Speech Recognition (бесплатный уровень)
            text = recognizer.recognize_google(recorded_audio, language="ru-RU")

        await status_msg.edit_text(f"✅ Текст из видео:\n\n{text}")

    except Exception as e:
        logging.error(f"Error: {e}")
        await status_msg.edit_text("❌ Ошибка: не удалось распознать речь. Возможно, звук слишком тихий или видео слишком длинное.")
    
    finally:
        for f in [audio_file, wav_file, video_id]:
            if os.path.exists(f): os.remove(f)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
