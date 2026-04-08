import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ТОКЕН БОТА
API_TOKEN = '8171908778:AAH9Jcs4KtEVoadkbf7aQ2aPrAjAYJ8pmmw'

bot, dp, rec = Bot(token=API_TOKEN), Dispatcher(), sr.Recognizer()

async def get_ai_translate(text):
    """Генерация конспекта через ИИ с автоматическим выбором провайдера"""
    # Очищаем текст от лишних пробелов и ограничиваем длину для стабильности
    clean_text = " ".join(text.split())[:6000]
    
    # Попытка №1: Автоматический выбор лучшего доступного провайдера
    try:
        response = await g4f.ChatCompletion.create_async(
            model=g4f.models.default,
            messages=[{"role": "user", "content": f"Сделай подробный русский конспект этой расшифровки видео: {clean_text}"}],
        )
        if response and len(str(response)) > 50:
            return response
    except Exception as e:
        logging.error(f"Ошибка ИИ (Авто): {e}")

    # Попытка №2: Прямое обращение к базовой модели gpt-3.5
    try:
        response = await g4f.ChatCompletion.create_async(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Сделай краткий конспект на русском: {clean_text}"}],
        )
        if response and len(str(response)) > 50:
            return response
    except Exception as e:
        logging.error(f"Ошибка ИИ (Запасная): {e}")

    return f"⚠️ ИИ временно недоступен, но текст успешно распознан. Вот начало:\n\n{clean_text[:1000]}..."

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🚀 Бот обновлен! Ошибка ИИ исправлена. Теперь всё должно работать. Присылай ссылку!")

@dp.message()
async def process(m: types.Message):
    # Поиск ID видео
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id:
        return
    
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Загрузка аудио через защищенный канал...")

    try:
        # Настройки скачивания
        ydl_opts = {
            'format': 'bestaudio/best', 
            'outtmpl': f'{vid}.%(ext)s',
            'noplaylist': True,
            'cookiefile': 'cookies.txt',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'quiet': True,
            'nocheckcertificate': True,
            'extractor_args': {'youtube': {'player_client': ['android', 'web']}},
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(m.text, download=True)
            except:
                ydl_opts['format'] = 'worstvideo[ext=mp4]+bestaudio/best'
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_em:
                    info = ydl_em.extract_info(m.text, download=True)
            
            ext = info.get('ext', 'mp4') if info else 'mp4'
            downloaded_file = f"{vid}.{ext}"
        
        if not os.path.exists(downloaded_file):
            for f in os.listdir('.'):
                if f.startswith(vid) and not f.endswith('.wav'):
                    downloaded_file = f
                    break

        if not os.path.exists(downloaded_file):
            raise Exception("YouTube заблокировал скачивание.")

        await msg.edit_text("⏳ 2/3: Распознавание речи (использую FFmpeg)...")
        
        # Обработка аудио
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
            await msg.edit_text(f"⏳ Обработка звука... Минут: {i // 60000}")

        if not full_text:
            await msg.edit_text("❌ В видео не найдена речь.")
            return

        await msg.edit_text("⏳ 3/3: Нейросеть составляет конспект...")
        summary = await get_ai_translate(" ".join(full_text))
        await m.answer(f"✅ **Результат анализа:**\n\n{summary}")

    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)[:150]}")
    finally:
        # Удаление временных файлов
        for f in os.listdir('.'):
            if f.startswith(vid):
                try: os.remove(f)
                except: pass

async def main():
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
