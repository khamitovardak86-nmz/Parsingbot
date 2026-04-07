import logging
import asyncio
from aiogram import Bot, Dispatcher, types
from youtube_transcript_api import YouTubeTranscriptApi

# Твой самый свежий токен
API_TOKEN = '8688129970:AAHCOdltYIaVR3WMEYRRxhDH52AZ1up5Ec8'

# Настройка логирования, чтобы видеть работу в Railway
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    await message.reply("Привет! Пришли мне ссылку на YouTube видео, и я пришлю тебе его текст.")

@dp.message_handler()
async def get_transcript(message: types.Message):
    url = message.text
    video_id = ""

    # Извлекаем ID видео из разных форматов ссылок
    if "v=" in url:
        video_id = url.split("v=")[1].split("&")[0]
    elif "be/" in url:
        video_id = url.split("be/")[1].split("?")[0]

    if not video_id:
        await message.reply("Пожалуйста, пришли рабочую ссылку на YouTube.")
        return

    await message.answer("⏳ Минутку, достаю субтитры...")

    try:
        # Пытаемся найти русские или английские субтитры
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['ru', 'en'])
        
        full_text = " ".join([entry['text'] for entry in transcript_list])

        # Ограничение Telegram на длину сообщения (4096 символов)
        if len(full_text) > 4000:
            full_text = full_text[:4000] + "..."

        await message.answer(f"✅ Текст видео:\n\n{full_text}")
    
    except Exception as e:
        await message.answer("❌ Не удалось найти субтитры. Попробуй другое видео.")

async def main():
    # Очищаем очередь старых сообщений и запускаем бота
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен!")
    await dp.start_polling()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
