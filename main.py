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
    pattern = r"(?:v=|\/|be\/|live\/)([0-9A-Za-z_-]{11})"
    match = re.search(pattern, url)
    return match.group(1) if match else None

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply("Привет! Я работаю в легком режиме. Пришли ссылку на YouTube, и я найду текст (RU/EN).")

@dp.message()
async def get_transcript(message: types.Message):
    video_id = extract_video_id(message.text)
    if not video_id:
        return

    wait_msg = await message.answer("⏳ Ищу текстовую дорожку...")

    try:
        # Получаем все доступные субтитры
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Пытаемся найти русский, если нет - английский
        try:
            transcript = transcript_list.find_transcript(['ru', 'en'])
        except:
            # Если ручных нет, ищем автогенерированные
            transcript = transcript_list.find_generated_transcript(['ru', 'en'])

        data = transcript.fetch()
        full_text = " ".join([entry['text'] for entry in data])

        if len(full_text) > 4000:
            full_text = full_text[:4000] + "..."

        await wait_msg.edit_text(f"✅ Текст ({transcript.language}):\n\n{full_text}")
    
    except Exception as e:
        logging.error(f"Error: {e}")
        await wait_msg.edit_text("❌ К сожалению, на серверах YouTube нет текста для этого видео. Без платного сервера или мощного ИИ это видео не расшифровать.")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
