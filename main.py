import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ТОКЕН
API_TOKEN = '8713594420:AAE1Bm4fyhpXnis4AhE95WNWqmIhtjgMCc4'
bot, dp, rec = Bot(token=API_TOKEN), Dispatcher(), sr.Recognizer()

async def get_ai_translate(text):
    """Функция для создания конспекта через нейросеть"""
    providers = [g4f.Provider.Blackbox, g4f.Provider.ChatGptEs, g4f.Provider.DarkAI]
    for provider in providers:
        try:
            response = await g4f.ChatCompletion.create_async(
                model="gpt-3.5-turbo",
                provider=provider,
                messages=[{"role": "user", "content": f"Сделай подробный русский конспект этого текста: {text}"}],
            )
            if response and len(str(response)) > 20:
                return response
        except:
            continue
    return "⚠️ (Ошибка ИИ: сервер временно недоступен)"

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🌍 Бот готов к работе! Пришли ссылку на YouTube видео.")

@dp.message()
async def process(m: types.Message):
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id:
        return
    
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Скачиваю аудио...")

    try:
        # ОБНОВЛЕННЫЕ НАСТРОЙКИ (Исправлена ошибка Requested format is not available)
        ydl_opts = {
            'format': 'm4a/bestaudio/best',  # Берем m4a или любое лучшее аудио
            'outtmpl': vid,
            'noplaylist': True,
            'quiet': True,
            'cookiefile': 'cookies.txt',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',
            }],
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([m.text])
        
        audio_file = f"{vid}.mp3"
        if not os.path.exists(audio_file) and os.path.exists(vid):
            os.rename(vid, audio_file)
        
        audio = AudioSegment.from_mp3(audio_file)
        full_text = []

        await msg.edit_text("⏳ 2/3: Распознаю речь...")
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
            
            await msg.edit_text(f"⏳ Распознаю... Минут обработано: {i // 60000}")

        if not full_text:
            await msg.edit_text("❌ Не удалось распознать речь.")
            return

        await msg.edit_text("⏳ 3/3: ИИ готовит конспект...")
        
        combined_text = " ".join(full_text)
        summary = await get_ai_translate(combined_text[:5000])

        await m.answer(f"✅ **Готовый конспект:**\n\n{summary}")

    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)[:100]}")
    finally:
        if os.path.exists(f"{vid}.mp3"):
            os.remove(f"{vid}.mp3")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
