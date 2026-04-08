import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# КОНФИГУРАЦИЯ
API_TOKEN = '8713594420:AAHTSBGJ0cro8CnoBKWVLRPOkyQlCGizqTY'
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
                messages=[{"role": "user", "content": f"Сделай подробный русский конспект: {text}"}],
            )
            if response and len(str(response)) > 20:
                return response
        except:
            continue
    return "⚠️ (Ошибка ИИ: сервер перегружен)"

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🌍 Бот готов! Пришли ссылку на видео (EN/AR).")

@dp.message()
async def process(m: types.Message):
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id: return
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Скачиваю аудио...")

    try:
        ydl_opts = {
            'format': 'bestaudio',
            'outtmpl': vid,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '32'
            }],
            'quiet': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([m.text])
        
        audio_file = f"{vid}.mp3"
        if not os.path.exists(audio_file) and os.path.exists(vid): 
            os.rename(vid, audio_file)
        
        audio = AudioSegment.from_mp3(audio_file)
        full_text = []

        await msg.edit_text("⏳ 2/3: Распознаю речь (EN/AR)...")
        for i in range(0, len(audio), 300000):
            chunk_p = f"{vid}_{i}.wav"
            audio[i:i+300000].set_frame_rate(16000).set_channels(1).export(chunk_p, format="wav")
            
            with sr.AudioFile(chunk_p) as src:
                audio_data = rec.record(src)
                try:
                    txt = rec.recognize_google(audio_data, language="en-US")
                except:
                    try: txt = rec.recognize_google(audio_data, language="ar-SA")
                    except: txt = ""
                if txt: full_text.append(txt)
            
            if os.path.exists(chunk_p): os.remove(chunk_p)
            if (i // 300000) % 3 == 0:
                await msg.edit_text(f"⏳ Обработано {i//60000} мин...")

        await msg.edit_text("⏳ 3/3: Нейросеть пишет конспект...")
        final_results = []
        for i in range(0, len(full_text), 3):
            block = " ".join(full_text[i:i+3])
            if block.strip():
                res = await get_ai_translate(block)
                final_results.append(res)

        report = "\n\n".join(final_results)
        if not report.strip():
            await m.answer("❌ Текст не найден.")
        elif len(report) > 4000:
            with open("summary.txt", "w", encoding="utf-8") as f: f.write(report)
            await m.answer_document(types.FSInputFile("summary.txt"), caption="✅ Готово!")
        else:
            await m.answer(f"✅ **Результат (RU):**\n\n{report}")

    except Exception as e:
        await m.answer(f"❌ Ошибка: {str(e)[:100]}")
    finally:
        # Тот самый блок, где была ошибка. Теперь всё ровно:
        if os.path.exists(f"{vid}.mp3"):
            os.remove(f"{vid}.mp3")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
