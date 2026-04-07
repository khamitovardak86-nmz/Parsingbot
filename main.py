import logging
import asyncio
import os
import re
import sys

# Проверка и установка библиотек, если их не хватает
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

# ТВОЙ НОВЫЙ ТОКЕН (ОБНОВЛЕН)
API_TOKEN = '8688129970:AAH3yWYWT4MSKtWmYSrDedkpBAeaTDkhi2U'

# Настройка логирования
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def extract_video_id(url):
    """Извлекает ID video из ссылки YouTube"""
    pattern = r"(?:v=|\/|be\/|live\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Бот обновлен! Токен заменен. Теперь я использую облачное распознавание речи Google. Присылай ссылку на YouTube!")

@dp.message()
async def process_video(message: types.Message):
    video_id = extract_video_id(message.text)
    if not video_id:
        return

    status_msg = await message.answer("⏳ Начинаю работу. Скачиваю аудио дорожку...")

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
        
        # Поправляем расширение, если нужно
        if not os.path.exists(audio_file) and os.path.exists(video_id):
            os.rename(video_id, audio_file)

        await status_msg.edit_text("⏳ Аудио скачано. Конвертирую и распознаю речь...")

        # 2. Конвертация в WAV (необходима для SpeechRecognition)
        # Обрабатываем первые 10 минут видео (600 000 мс)
        audio = AudioSegment.from_mp3(audio_file)
        audio[:600000].export(wav_file, format="wav")

        # 3. Распознавание через Google Cloud Speech API
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file) as source:
            audio_data = recognizer.record(source)
            # Пытаемся распознать на русском, если не выйдет - на английском
            try:
                text = recognizer.recognize_google(audio_data, language="ru-RU")
            except:
                text = recognizer.recognize_google(audio_data, language="en-US")

        if not text:
            await status_msg.edit_text("❌ Не удалось разобрать слова в этом видео.")
            return

        # Лимит сообщения в Telegram 4096 символов
        if len(text) > 4000:
            text = text[:4000] + "..."

        await status_msg.edit_text(f"✅ Готово! Текст из видео:\n\n{text}")

    except Exception as e:
        logging.error(f"Ошибка процесса: {e}")
        await status_msg.edit_text(f"❌ Произошла ошибка. Проверь наличие ffmpeg на сервере. Текст ошибки: {str(e)[:100]}")
    
    finally:
        # Очистка временных файлов
        for temp_file in [audio_file, wav_file, video_id]:
            if os.path.exists(temp_file):
                os.remove(temp_file)

async def main():
    # Удаляем старые запросы и запускаем
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен с новым токеном!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
