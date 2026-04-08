import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

API_TOKEN = '8713594420:AAF80KdIxlsVMNTIONQ2kuXe_jFDwJCOcj4'
bot, dp, rec = Bot(token=API_TOKEN), Dispatcher(), sr.Recognizer()

async def get_ai_translate(text):
    """ИИ переводит любой текст (EN/AR) в русский конспект"""
    try:
        return await g4f.ChatCompletion.create_async(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": f"Изучи этот текст (он может быть на английском или арабском). Переведи его на русский и сделай подробный структурированный конспект: {text}"}]
        )
    except: return "⚠️ Ошибка ИИ"

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🌍 Бот-переводчик готов! Пришли ссылку на видео (English или Arabic). Сделаю конспект на русском.")

@dp.message()
async def process(m: types.Message):
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id: return
    vid = v_id.group(1)
    msg = await m.answer("⏳ Начинаю обработку...")

    try:
        with yt_dlp.YoutubeDL({'format':'bestaudio','outtmpl':vid,'postprocessors':[{'key':'FFmpegExtractAudio','preferredcodec':'mp3','preferredquality':'32'}],'quiet':True}).download([m.text])
        
        audio = AudioSegment.from_mp3(f"{vid}.mp3")
        full_text = []

        # Режем по 5 минут
        for i in range(0, len(audio), 300000):
            chunk_p = f"{vid}_{i}.wav"
            audio[i:i+300000].set_frame_rate(16000).set_channels(1).export(chunk_p, format="wav")
            
            with sr.AudioFile(chunk_p) as src:
                audio_data = rec.record(src)
                # Сначала пробуем английский, если пусто — арабский
                try:
                    txt = rec.recognize_google(audio_data, language="en-US")
                except:
                    try:
                        txt = rec.recognize_google(audio_data, language="ar-SA")
                    except:
                        txt = ""
                full_text.append(txt)
            
            if os.path.exists(chunk_p): os.remove(chunk_p)
            await msg.edit_text(f"⏳ Обработано {i//60000} мин...")

        # Суммаризация блоками
        await msg.edit_text("🧠 ИИ создает русский конспект...")
        final_results = []
        for i in range(0, len(full_text), 4):
            block = " ".join(full_text[i:i+4])
            if block.strip():
                res = await get_ai_translate(block)
                final_results.append(res)

        await m.answer(f"✅ **Результат (RU):**\n\n" + "\n\n".join(final_results))

    except Exception as e: await m.answer(f"❌ Ошибка: {str(e)[:50]}")
    finally:
        if os.path.exists(f"{vid}.mp3"): os.remove(f"{vid}.mp3")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__': asyncio.run(main())
