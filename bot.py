import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
HF_TOKEN = os.getenv("HF_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

client = InferenceClient(token=HF_TOKEN)

SYSTEM_PROMPT = """
Ты — гениальный копирайтер для TikTok. Напиши 5 вариантов подписи к видео, чтобы байтить на комментарии и репосты.
Используй приемы: клиффхэнгер, провокация, поиск ошибки, самоирония.
Пиши коротко. Формат:
1. [Текст]
2. [Текст]
"""


async def transcribe_audio(audio_bytes):
    return await asyncio.to_thread(
        client.audio.transcription,
        audio_bytes,
        model="openai/whisper-large-v3"
    )


async def generate_caption(text):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Текст из видео:\n\n{text}"}
    ]
    response = await asyncio.to_thread(
        client.chat_completion,
        messages=messages,
        model="mistralai/Mistral-7B-Instruct-v0.3"
    )
    return response.choices[0].message.content


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Пришли скачанное видео из TikTok (до 15 МБ), и я выдам огненную подпись 🔥\n\n⚠️ Я бесплатный. Если не отвечаю минуту — значит просыпаюсь, подожди.")


@dp.message(F.video)
async def handle_video(message: types.Message):
    await message.answer("Слушаю видео... Это займет около минуты на бесплатном сервере ⏳")

    try:
        file = await bot.get_file(message.video.file_id)

        if file.file_size > 15 * 1024 * 1024:
            await message.answer("Видео тяжелее 15 МБ. Пришли в худшем качестве, иначе сервер умрет 💀")
            return

        downloaded_file = await bot.download_file(file.file_path)
        audio_bytes = downloaded_file.read()

        transcription = await transcribe_audio(audio_bytes)

        if not transcription.strip():
            await message.answer("Не услышал слов 🤫. Напиши текстом, о чем видео, и я придумаю подпись!")
            return

        result_text = await generate_caption(transcription)
        await message.answer(f"✨ <b>Держи варианты:</b>\n\n{result_text}")

    except Exception as e:
        logging.error(f"Error: {e}")
        await message.answer("Сервер не справился. Попробуй отправить видео еще раз.")


@dp.message(F.text)
async def handle_text(message: types.Message):
    await message.answer("Обрабатываю твой текст... ⏳")
    try:
        result_text = await generate_caption(f"Ситуация в видео (описание пользователем):\n\n{message.text}")
        await message.answer(f"✨ <b>По твоему описанию:</b>\n\n{result_text}")
    except Exception as e:
        await message.answer("Произошла ошибка.")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())