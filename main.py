import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from youtube_transcript_api import YouTubeTranscriptApi

# Твой новый токен
API_TOKEN = '8688129970:AAE_UbL_CAd178AWo64E2wqifRs5VH8I1Ag'

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Пришли мне ссылку на YouTube видео, и я попробую достать из него текст.")

@dp.message_handler()
async def get_transcript(message: types.Message):
    url = message.text
    video_id = ""

    # Пытаемся достать ID видео из ссылки
    if "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "be/" in url:
        video_id = url.split("be/")[1].split("?")[0]

    if not video_id:
        await message.reply("Пожалуйста, пришли корректную ссылку на YouTube видео.")
        return

    await message.answer("⏳ Собираю текст видео, подожди немного...")

    try:
        # Пытаемся получить субтитры (сначала на русском, потом на английском)
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru', 'en'])
        
        full_text = ""
        for entry in transcript_list:
            full_text += entry['text'] + " "

        # Если текст слишком длинный, Telegram его не пропустит (лимит 4096 символов)
        if len(full_text) > 4000:
            full_text = full_text[:4000] + "..."

        await message.answer(f"✅ Готово! Вот текст видео:\n\n{full_text}")
    
    except Exception as e:
        await message.answer(f"❌ Не удалось получить текст. Возможно, в видео нет субтитров или они запрещены.")

async def main():
    # Удаляем вебхук перед запуском, чтобы не было конфликтов
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
