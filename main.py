import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# ТОКЕН (Твой актуальный)
API_TOKEN = '8271265279:AAETCLSKA_jSKdpUbsCn-dHrHXwSwOmWtgw'
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
    # Ищем ID видео
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id:
        return
    
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Скачиваю аудио (универсальный метод)...")

    try:
        # УЛУЧШЕННЫЕ НАСТРОЙКИ (Решают проблему Requested format is not available)
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
            info = ydl.extract_info(m.text, download=True)
            # Авто-поиск скачанного файла
            ext = info.get('ext', 'm4a')
            downloaded_file = f"{vid}.{ext}"
        
        if not os.path.exists(downloaded_file):
            # Если файл не нашелся по имени, ищем любой файл, начинающийся на ID видео
            for file in os.listdir('.'):
                if file.startswith(vid):
                    downloaded_file = file
                    break

        await msg.edit_text("⏳ 2/3: Распознаю речь (RU/EN/AR)...")
        
        audio = AudioSegment.from_file(downloaded_file)
        full_text = []

        # Обработка кусками по 5 минут
        for i in range(0, len(audio), 300000):
            chunk_p = f"{vid}_temp.wav"
            audio[i:i+300000].set_frame_rate(16000).set_channels(1).export(chunk_p, format="wav")
            
            with sr.AudioFile(chunk_p) as src:
                audio_data = rec.record(src)
                try:
                    # Очередь: RU -> EN -> AR
                    txt = rec.recognize_google(audio_data, language="ru-RU")
                except:
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
            
            await msg.edit_text(f"⏳ Распознаю... Обработано минут: {i // 60000}")

        if not full_text:
            await msg.edit_text("❌ Не удалось распознать речь в этом видео.")
            return

        await msg.edit_text("⏳ 3/3: Нейросеть готовит конспект...")
        
        combined_text = " ".join(full_text)
        summary = await get_ai_translate(combined_text[:6000])

        await m.answer(f"✅ **Готовый конспект:**\n\n{summary}")

    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)[:100]}")
    finally:
        # Удаляем любые файлы, связанные с этим видео
        for file in os.listdir('.'):
            if file.startswith(vid):
                try: os.remove(file)
                except: pass

async def main():
    try:
        await bot.get_me()
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
