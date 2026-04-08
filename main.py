import logging, asyncio, os, re, yt_dlp, g4f
import speech_recognition as sr
from pydub import AudioSegment
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# КОНФИГУРАЦИЯ (Новый токен вставлен)
API_TOKEN = '8713594420:AAHTSBGJ0cro8CnoBKWVLRPOkyQlCGizqTY'
bot, dp, rec = Bot(token=API_TOKEN), Dispatcher(), sr.Recognizer()

async def get_ai_translate(text):
    """Умный перебор бесплатных провайдеров ИИ (GPT)"""
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
                messages=[{"role": "user", "content": f"Переведи на русский и сделай подробный конспект этого текста (тезисы, важные мысли): {text}"}],
            )
            if response and len(str(response)) > 20:
                return response
        except:
            continue
    return "⚠️ (Ошибка блока ИИ: все бесплатные сервера перегружены)"

@dp.message(Command("start"))
async def start(m: types.Message):
    await m.answer("🌍 Бот обновлен! Новый токен активен.\nПришли ссылку на видео (EN/AR), и я сделаю русский конспект.")

@dp.message()
async def process(m: types.Message):
    # Поиск ID видео
    v_id = re.search(r"(?:v=|\/|be\/)([0-9A-Za-z_-]{11})", m.text)
    if not v_id: return
    vid = v_id.group(1)
    msg = await m.answer("⏳ 1/3: Скачиваю аудио дорожку...")

    try:
        # Загрузка через yt-dlp
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
        # Проверка переименования (иногда yt-dlp сохраняет без расширения)
        if not os.path.exists(audio_file) and os.path.exists(vid): 
            os.rename(vid, audio_file)
        
        audio = AudioSegment.from_mp3(audio_file)
        full_text = []

        await msg.edit_text("⏳ 2/3: Распознаю речь (English/Arabic)...")
        # Нарезка по 5 минут (300000 мс)
        for i in range(0, len(audio), 300000):
            chunk_p = f"{vid}_{i}.wav"
            audio[i:i+300000].set_frame_rate(16000).set_channels(1).export(chunk_p, format="wav")
            
            with sr.AudioFile(chunk_p) as src:
                audio_data = rec.record(src)
                try:
                    # Пробуем распознать как английский
                    txt = rec.recognize_google(audio_data, language="en-US")
                except:
                    try: 
                        # Если не вышло, пробуем арабский
                        txt = rec.recognize_google(audio_data, language="ar-SA")
                    except: 
                        txt = ""
                if txt: full_text.append(txt)
            
            if os.path.exists(chunk_p): os.remove(chunk_p)
            # Обновляем статус каждые 15 минут видео
            if (i // 300000) % 3 == 0:
                await msg.edit_text(f"⏳ Обработано {i//60000} мин. видео...")

        await msg.edit_text("⏳ 3/3: Нейросеть готовит русский отчет...")
        
        # Суммаризация блоками (чтобы не превысить лимиты ИИ)
        final_results = []
        for i in range(0, len(full_text), 3):
            block = " ".join(full_text[i:i+3])
            if block.strip():
                res = await get_ai_translate(block)
                final_results.append(res)

        # Сборка итогового текста
        report = "\n\n".join(final_results)
        
        if not report.strip():
            await m.answer("❌ Не удалось распознать речь в этом видео.")
        elif len(report) > 4000:
            # Если текст слишком длинный для одного сообщения
            with open("summary.txt", "w", encoding="utf-8") as f: f.write(report)
            await m.answer_document(types.FSInputFile("summary.txt"), caption="✅ Конспект готов (файл)")
        else:
            await m.answer(f"✅ **Результат (RU):**\n\n{report}")

    except Exception as e:
        await m.answer(f"❌ Произошла ошибка: {str(e)[:100]}")
    finally:
        # Очистка мусора
        if os.path.exists(f"{vid}.mp3"):
