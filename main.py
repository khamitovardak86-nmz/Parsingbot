import logging
import asyncio
import os
import re
import sys

# Принудительная установка whisper, если сервер его потеряет
try:
    import whisper
except ImportError:
    os.system(f"{sys.executable} -m pip install openai-whisper")
    import whisper

import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Твой токен
API_TOKEN = '8688129970:AAHCOdltYIaVR3WMEYRRxhDH52AZ1up5Ec8'

# Настройка логирования
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Загружаем самую легкую модель нейросети (tiny)
# Она скачается один раз при первом запуске
model = whisper.load_model("tiny")

def extract_video_id(url):
    """Извлекает ID видео из любой ссылки YouTube"""
    pattern = r"(?:v=|\/|be\/|live\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я теперь использую нейросеть Whisper. Я скачаю аудио из видео и сам превращу его в текст. Присылай ссылку!")

@dp.message()
async def process_video(message: types.Message):
    video_id = extract_video_id(message.text)
    if not video_id:
        return

    # Отправляем статус пользователю
    status_msg = await message.answer("⏳ Начинаю глубокую обработку. Сначала скачиваю аудио...")

    # Имя временного файла
    file_path = f"{video_id}.mp3"
    
    try:
        # Настройки для скачивания только аудиодорожки
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': video_id, # yt-dlp сам добавит расширение
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            'quiet': True
        }
        
        # Скачивание
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([message.text])
        
        # Если файл скачался без расширения в названии, поправляем
        if not os.path.exists(file_path) and os.path.exists(video_id):
            os.rename(video_id, file_path)

        await status_msg.edit_text("⏳ Аудио получено. Нейросеть Whisper начинает расшифровку...")

    except Exception as e:
        logging.error(f"Ошибка при скачивании: {e}")
        await status_msg.edit_text("❌ Не удалось скачать аудио из видео.")
        return

    try:
        # Распознавание текста нейросетью
        # task="transcribe" — просто пишет текст на языке оригинала
        result = model.transcribe(file_path)
        full_text = result.get('text', '').strip()

        if not full_text:
            await status_msg.edit_text("❌ Нейросеть не смогла разобрать речь в этом видео.")
            return

        # Ограничение длины сообщения в Telegram
        if len(full_text) > 4000:
            full_text = full_text[:4000] + "...\n\n[Текст слишком длинный и был обрезан]"

        await status_msg.edit_text(f"✅ Готово! Текст из видео:\n\n{full_text}")

    except Exception as e:
        logging.error(f"Ошибка Whisper: {e}")
        await status_msg.edit_text("❌ Ошибка при работе нейросети.")
    
    finally:
        # Всегда удаляем файл после работы, чтобы не забивать память сервера
        if os.path.exists(file_path):
            os.remove(file_path)
        elif os.path.exists(video_id):
            os.remove(video_id)

async def main():
    # Удаляем старые сообщения (webhook) и запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот запущен и готов слушать видео через Whisper!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
