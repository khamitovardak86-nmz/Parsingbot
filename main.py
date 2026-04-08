import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ТОКЕН
API_TOKEN = '8713594420:AAHli0qt3MFpSlK00BvBRa9djmzqjLSexYE'
bot, dp, rec = Bot(token=API_TOKEN), Dispatcher(), sr.Recognizer()

async def get_ai_translate(text):
    """Конспект через LLM (нейросеть)"""
    providers = [g4f.Provider.Blackbox, g4f.Provider.ChatGptEs]
    for p in providers:
        try:
            r = await g4f.ChatCompletion.create_async(
                model="gpt-3.5-turbo", provider=p,
                messages=[{"role": "user", "content": f"Сделай подробный русский конспект этого текста: {text}"}],
            )
            if r and len(str(r)) > 20: return r
        except: continue
    return "⚠️ Ошибка ИИ: Сервис временно перегружен."

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🚀 Бот запущен! Отправляй ссылку на YouTube.")

@dp.message()
async def process(m: types.Message):
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id: return
    
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Скачиваю аудио...")

    try:
        ydl_opts = {
            'format': 'bestaudio/best', 
            'outtmpl': f'{vid}.%(ext)s',
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(m.text, download=True)
            # Автоматически находим расширение (m4a, webm или mp3)
            ext = info.get('ext', 'm4a')
            downloaded_file = f"{vid}.{ext}"
        
        if not os.path.exists(downloaded_file):
            raise Exception("Файл не найден после скачивания")

        await msg.edit_text("⏳ 2/3: Распознаю речь...")
        
        audio = AudioSegment.from_file(downloaded_file)
        full_text = []

        # Обработка кусками по 5 минут
        for i in range(0, len(audio), 300000):
            chunk_p = f"{vid}_temp.wav"
            audio[i:i+300000].set_frame_rate(16000).set_channels(1).export(chunk_p, format="wav")
            with sr.AudioFile(chunk_p) as src:
                d = rec.record(src)
                try:
                    t = rec.recognize_google(d, language="en-US")
                except:
                    try: t = rec.recognize_google(d, language="ar-SA")
                    except: t = ""
                if t: full_text.append(t)
            if os.path.exists(chunk_p): os.remove(chunk_p)
            await msg.edit_text(f"⏳ Распознаю... Обработано минут: {i // 60000}")

        if os.path.exists(downloaded_file): os.remove(downloaded_file)

        if not full_text:
            await msg.edit_text("❌ Не удалось распознать голос.")
            return

        await msg.edit_text("⏳ 3/3: Нейросеть пишет конспект...")
        res = await get_ai_translate(" ".join(full_text)[:6000])
        await m.answer(f"✅ **Конспект:**\n\n{res}")

    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)[:100]}")
        # Чистка мусора
        for f in os.listdir('.'):
            if f.startswith(vid): os.remove(f)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
