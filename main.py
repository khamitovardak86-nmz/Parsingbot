import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ТОКЕН (Твой актуальный)
API_TOKEN = '8713594420:AAEx948Qr3S425OK0cfL9YeToTbIo3CSS6M'
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
    await m.answer("🌍 Бот готов к работе с Cookies! Пришли ссылку на YouTube видео.")

@dp.message()
async def process(m: types.Message):
    # Ищем ID видео в ссылке
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id:
        return
    
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Скачиваю аудио (авторизация по Cookies)...")

    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': vid,
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '32'}],
            'quiet': True,
            'cookiefile': 'cookies.txt',  # Тот самый файл, который ты создал
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([m.text])
        
        audio_file = f"{vid}.mp3"
        if not os.path.exists(audio_file) and os.path.exists(vid):
            os.rename(vid, audio_file)
        
        # Разбивка и распознавание речи
        audio = AudioSegment.from_mp3(audio_file)
        full_text = []

        await msg.edit_text("⏳ 2/3: Распознаю речь (это может занять время)...")
        # Обработка кусками по 5 минут
        for i in range(0, len(audio), 300000):
            chunk_p = f"{vid}_{i}.wav"
            audio[i:i+300000].set_frame_rate(16000).set_channels(1).export(chunk_p, format="wav")
            
            with sr.AudioFile(chunk_p) as src:
                audio_data = rec.record(src)
                try:
                    # Пробуем английский, если не вышло - арабский (как в твоем примере)
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
            
            # Обновляем статус в ТГ
            current_min = i // 60000
            await msg.edit_text(f"⏳ Распознаю... Обработано минут: {current_min}")

        if not full_text:
            await msg.edit_text("❌ Не удалось распознать речь в этом видео.")
            return

        await msg.edit_text("⏳ 3/3: Нейросеть готовит конспект на русском...")
        
        # Склеиваем текст и отправляем в ИИ
        combined_text = " ".join(full_text)
        # Если текст слишком длинный, берем первые 5000 символов для конспекта
        summary = await get_ai_translate(combined_text[:5000])

        await m.answer(f"✅ **Готовый конспект:**\n\n{summary}")

    except Exception as e:
        await m.answer(f"❌ Произошла ошибка: {str(e)[:100]}")
    finally:
        # Удаляем временный аудиофайл
        if os.path.exists(f"{vid}.mp3"):
            os.remove(f"{vid}.mp3")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
