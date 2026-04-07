import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from youtube_transcript_api import YouTubeTranscriptApi

# Твой актуальный токен
API_TOKEN = '8688129970:AAHCOdltYIaVR3WMEYRRxhDH52AZ1up5Ec8'

logging.basicConfig(level=logging.INFO)

# Для 3-й версии aiogram инициализация выглядит так:
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

@dp.message(Command("start", "help"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Пришли мне ссылку на YouTube видео, и я пришлю тебе его текст.")

@dp.message()
async def get_transcript(message: types.Message):
    url = message.text
    video_id = ""

    if "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "be/" in url:
        video_id = url.split("be/")[1].split("?")[0]

    if not video_id:
        return

    await message.answer("⏳ Минутку, достаю субтитры...")

    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru', 'en'])
        full_text = " ".join([entry['text'] for entry in transcript_list])

        if len(full_text) > 4000:
            full_text = full_text[:4000] + "..."

        await message.answer(f"✅ Текст видео:\n\n{full_text}")
    except Exception:
        await message.answer("❌ Не удалось найти субтитры.")

async def main():
    # Очистка очереди и запуск
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен на aiogram 3.x!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
