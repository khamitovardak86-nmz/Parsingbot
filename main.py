import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# КОНФИГУРАЦИЯ (Обновленный токен)
API_TOKEN = '8713594420:AAHli0qt3MFpSlK00BvBRa9djmzqjLSexYE'
bot, dp, rec = Bot(token=API_TOKEN), Dispatcher(), sr.Recognizer()

async def get_ai_translate(text):
    """Умный перебор бесплатных провайдеров ИИ"""
    providers = [
        g4f.Provider.Blackbox,
        g4f.Provider.ChatGptEs,
        g4f.Provider.DarkAI,
        g4f.Provider.Liaobots
    ]
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
    return "⚠️ (Ошибка ИИ: сервер сейчас занят, попробуй позже)"

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🌍 Бот запущен с новым токеном! Пришли ссылку на видео (EN/AR).")

@dp.message()
async def process(m: types.Message):
    # Поиск ID видео в ссылке
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id: return
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Скачиваю аудио...")

    try:
        # Настройки для скачивания и обхода блокировок
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': vid,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '32'
            }],
            'quiet': True,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'nocheckcertificate': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([m.text])
        
        audio_file = f"{vid}.mp3"
        if not os.path.exists(audio_file) and os.path.exists(vid): 
            os.rename(vid, audio_file)
        
        audio = AudioSegment.from_mp3(audio_file)
        full_text = []

        await msg.edit_text("⏳ 2/3: Распознаю речь (EN/AR)...")
        # Обработка по 5 минут
        for i in range(0, len(audio), 300000):
            chunk_p = f"{vid}_{i}.wav"
            audio[i:i+300000].set_frame_rate(16000).set_channels(1).export(chunk_p, format="wav")
            
            with sr.AudioFile(chunk_p) as src:
                audio_data = rec.record(src)
                try:
                    # Сначала пробуем английский, затем арабский
                    txt = rec.recognize_google(audio_data, language="en-US")
                except:
                    try:
                        txt = rec.recognize_google(audio_data, language="ar-SA")
                    except:
                        txt = ""
                if txt: full_text.append(txt)
            
            if os.path.exists(chunk_p): os.remove(chunk_p)
            await msg.edit_text(f"⏳ Обработано {i//60000} мин...")

        await msg.edit_text("⏳ 3/3: Нейросеть пишет отчет...")
        
        final_results = []
        for i in range(0, len(full_text), 3):
            block = " ".join(full_text[i:i+3])
            if block.strip():
                res = await get_ai_translate(block)
                final_results.append(res)

        report = "\n\n".join(final_results)
        
        if not report.strip():
            await m.answer("❌ Не удалось распознать текст в этом видео.")
        elif len(report) > 4000:
            with open("report.txt", "w", encoding="utf-8") as f: f.write(report)
            await m.answer_document(types.FSInputFile("report.txt"), caption="✅ Конспект готов!")
        else:
            await m.answer(f"✅ **Результат (RU):**\n\n{report}")

    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)[:100]}")
    finally:
        # Удаляем временный аудиофайл
        if os.path.exists(f"{vid}.mp3"):
            os.remove(f"{vid}.mp3")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
