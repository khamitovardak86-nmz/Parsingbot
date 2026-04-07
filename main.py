import logging
import asyncio
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from youtube_transcript_api import YouTubeTranscriptApi

API_TOKEN = '8688129970:AAHCOdltYIaVR3WMEYRRxhDH52AZ1up5Ec8'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

def extract_video_id(url):
    # Универсальный поиск ID видео (для ссылок /v/, /live/, /embed/, youtube.com, youtu.be)
    pattern = r"(?:v=|\/|be\/|live\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Пришли мне ссылку на YouTube, и я достану текст.")

@dp.message()
async def get_transcript(message: types.Message):
    video_id = extract_video_id(message.text)

    if not video_id:
        await message.answer("⚠️ Не удалось распознать ссылку. Пришли обычную ссылку на видео.")
        return

    await message.answer("⏳ Собираю текст, подожди...")

    try:
        # Пробуем достать русские или английские субтитры
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru', 'en'])
        full_text = " ".join([entry['text'] for entry in transcript_list])

        if len(full_text) > 4000:
            full_text = full_text[:4000] + "..."

        await message.answer(f"✅ Текст видео:\n\n{full_text}")
    except Exception as e:
        logging.error(f"Ошибка для видео {video_id}: {e}")
        await message.answer("❌ Субтитры не найдены. Возможно, они отключены автором или видео еще обрабатывается.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
