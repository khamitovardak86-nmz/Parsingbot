import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ТОКЕН (Проверь его еще раз перед вставкой)
API_TOKEN = '8271265279:AAGYIIzuyzg2ilM_bj8EQSSbgvI_4NpYt7U'

bot, dp, rec = Bot(token=API_TOKEN), Dispatcher(), sr.Recognizer()

async def get_ai_translate(text):
    """Генерация конспекта через LLM"""
    providers = [g4f.Provider.Blackbox, g4f.Provider.ChatGptEs, g4f.Provider.DarkAI]
    for provider in providers:
        try:
            response = await g4f.ChatCompletion.create_async(
                model="gpt-3.5-turbo",
                provider=provider,
                messages=[{"role": "user", "content": f"Сделай подробный русский конспект этой расшифровки видео: {text}"}],
            )
            if response and len(str(response)) > 20:
                return response
        except:
            continue
    return "⚠️ (Ошибка ИИ: сервисы временно недоступны)"

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🚀 Бот запущен со всеми инструментами! Присылай ссылку.")

@dp.message()
async def process(m: types.Message):
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id:
        return
    
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Скачиваю аудио (использую Node.js и FFmpeg)...")

    try:
        ydl_opts = {
            'format': 'bestaudio/best', 
            'outtmpl': f'{vid}.%(ext)s',
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'quiet': True,
            'nocheckcertificate': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(m.text, download=True)
            except Exception:
                ydl_opts['format'] = 'worstvideo+bestaudio/best'
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_em:
                    info = ydl_em.extract_info(m.text, download=True)
            
            ext = info.get('ext', 'm4a')
            downloaded_file = f"{vid}.{ext}"
        
        if not os.path.exists(downloaded_file):
            for f in os.listdir('.'):
                if f.startswith(vid) and not f.endswith('.wav'):
                    downloaded_file = f
                    break

        await msg.edit_text("⏳ 2/3: Распознаю речь (RU/EN/AR)...")
        
        audio = AudioSegment.from_file(downloaded_file)
        full_text = []

        for i in range(0, len(audio), 300000):
            chunk_p = f"{vid}_temp.wav"
            audio[i:i+300000].set_frame_rate(16000).set_channels(1).export(chunk_p, format="wav")
            
            with sr.AudioFile(chunk_p) as src:
                audio_data = rec.record(src)
                try:
                    txt = rec.recognize_google(audio_data, language="ru-RU")
                except:
                    try: txt = rec.recognize_google(audio_data, language="en-US")
                    except: txt = ""
                if txt: full_text.append(txt)
            
            if os.path.exists(chunk_p): os.remove(chunk_p)
            await msg.edit_text(f"⏳ Распознаю... Минут: {i // 60000}")

        if not full_text:
            await msg.edit_text("❌ Голос не обнаружен.")
            return

        await msg.edit_text("⏳ 3/3: Нейросеть пишет конспект...")
        summary = await get_ai_translate(" ".join(full_text)[:6000])
        await m.answer(f"✅ **Конспект:**\n\n{summary}")

    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)[:150]}")
    finally:
        for f in os.listdir('.'):
            if f.startswith(vid):
                try: os.remove(f)
                except: pass

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
