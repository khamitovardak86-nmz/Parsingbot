import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ТОКЕН
API_TOKEN = '8713594420:AAEdNV1YrgNwRuQA9M8ZVXSy_9FaJT3Z7JI'
bot, dp, rec = Bot(token=API_TOKEN), Dispatcher(), sr.Recognizer()

async def get_ai_translate(text):
    """Функция для создания конспекта через нейросеть"""
    providers = [g4f.Provider.Blackbox, g4f.Provider.ChatGptEs, g4f.Provider.DarkAI]
    for provider in providers:
        try:
            response = await g4f.ChatCompletion.create_async(
                model="gpt-3.5-turbo",
                provider=provider,
                messages=[{"role": "user", "content": f"Сделай подробный конспект на русском языке: {text}"}],
            )
            if response and len(str(response)) > 20:
                return response
        except:
            continue
    return "⚠️ (Ошибка ИИ: сервис временно недоступен)"

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🌍 Бот готов! Режим максимальной совместимости включен. Присылай ссылку!")

@dp.message()
async def process(m: types.Message):
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id:
        return
    
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Скачиваю аудио (любой доступный формат)...")

    try:
        # МАКСИМАЛЬНО ГИБКИЕ НАСТРОЙКИ
        ydl_opts = {
            'format': 'bestaudio/best', # Просто лучшее из того, что есть
            'outtmpl': vid,
            'noplaylist': True,
            'quiet': True,
            'cookiefile': 'cookies.txt',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'extract_flat': False,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
            # Добавляем игнорирование ошибок форматов
            'ignoreerrors': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([m.text])
        
        audio_file = f"{vid}.mp3"
        # Проверяем, появился ли файл (иногда yt-dlp сохраняет с расширением .m4a перед конвертацией)
        if not os.path.exists(audio_file):
            for f in os.listdir('.'):
                if f.startswith(vid) and f.endswith(('.mp3', '.m4a', '.webm')):
                    os.rename(f, audio_file)
                    break

        if not os.path.exists(audio_file):
            raise Exception("Файл не был скачан")

        audio = AudioSegment.from_file(audio_file)
        full_text = []

        await msg.edit_text("⏳ 2/3: Распознаю речь...")
        # Обработка по 5 минут
        for i in range(0, len(audio), 300000):
            chunk_p = f"{vid}_{i}.wav"
            audio[i:i+300000].set_frame_rate(16000).set_channels(1).export(chunk_p, format="wav")
            
            with sr.AudioFile(chunk_p) as src:
                audio_data = rec.record(src)
                try:
                    txt = rec.recognize_google(audio_data, language="en-US")
                except:
                    try:
                        txt = rec.recognize_google(audio_data, language="ar-SA")
                    except:
                        txt = ""
                if txt:
                    full_text.append(txt)
            
            if os.path.exists(chunk_p):
                os.remove(chunk_p)
            
            await msg.edit_text(f"⏳ Распознаю... Минут: {i // 60000}")

        if not full_text:
            await msg.edit_text("❌ Речь не обнаружена или не распознана.")
            return

        await msg.edit_text("⏳ 3/3: Нейросеть пишет конспект...")
        summary = await get_ai_translate(" ".join(full_text)[:6000])
        await m.answer(f"✅ **Результат:**\n\n{summary}")

    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)[:150]}")
    finally:
        if os.path.exists(audio_file):
            os.remove(audio_file)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
