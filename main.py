import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ТОКЕН БОТА
API_TOKEN = '8171908778:AAHVO5ze_7Lx5vyZfdJ0FTeYkP4VVwlMPwQ'

bot, dp, rec = Bot(token=API_TOKEN), Dispatcher(), sr.Recognizer()

async def get_ai_translate(text):
    """Генерация конспекта с защитой от разрывов и таймаутов"""
    clean_text = " ".join(text.split())[:5000] 
    
    # Список провайдеров для перебора при ошибках связи
    providers = [
        g4f.Provider.Binjie,
        g4f.Provider.Pizzagpt,
        g4f.Provider.Liaobots,
        g4f.Provider.FreeChatgpt
    ]

    for p in providers:
        try:
            # Даем ИИ 60 секунд на ответ
            response = await asyncio.wait_for(
                g4f.ChatCompletion.create_async(
                    model="gpt-3.5-turbo",
                    provider=p,
                    messages=[{"role": "user", "content": f"Сделай подробный русский конспект этой расшифровки видео: {clean_text}"}],
                ),
                timeout=60.0
            )
            if response and len(str(response)) > 50:
                return response
        except Exception as e:
            logging.error(f"Провайдер {p.__name__} не ответил: {e}")
            continue 

    return f"⚠️ ИИ временно перегружен. Вот начало расшифровки:\n\n{clean_text[:1000]}..."

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🚀 Бот обновлен! Куки и защита от разрывов связи настроены. Присылай ссылку на YouTube.")

@dp.message()
async def process(m: types.Message):
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id:
        return
    
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Загрузка через защищенный канал...")

    try:
        ydl_opts = {
            'format': 'bestaudio/best', 
            'outtmpl': f'{vid}.%(ext)s',
            'noplaylist': True,
            'cookiefile': 'cookies.txt', # Использует твои обновленные куки
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
            'quiet': True,
            'nocheckcertificate': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'tv', 'mweb'],
                    'skip': ['hls', 'dash']
                }
            },
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(m.text, download=True)
            except Exception:
                # Если с куками беда, пробуем аварийный режим без них через TV-клиент
                ydl_opts.pop('cookiefile', None)
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_alt:
                    info = ydl_alt.extract_info(m.text, download=True)
            
            ext = info.get('ext', 'mp4') if info else 'mp4'
            downloaded_file = f"{vid}.{ext}"
        
        # Проверка наличия файла
        if not os.path.exists(downloaded_file):
            for f in os.listdir('.'):
                if f.startswith(vid) and not f.endswith('.wav'):
                    downloaded_file = f
                    break

        if not os.path.exists(downloaded_file):
            raise Exception("YouTube заблокировал доступ. Попробуйте обновить cookies.txt позже.")

        await msg.edit_text("⏳ 2/3: Распознавание речи (FFmpeg)...")
        
        audio = AudioSegment.from_file(downloaded_file)
        full_text = []

        # Нарезка по 5 минут
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
            await msg.edit_text("❌ Речь в видео не распознана.")
            return

        await msg.edit_text("⏳ 3/3: Нейросеть пишет конспект...")
        summary = await get_ai_translate(" ".join(full_text))
        await m.answer(f"✅ **Результат анализа:**\n\n{summary}")

    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)[:150]}")
    finally:
        # Очистка файлов
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
