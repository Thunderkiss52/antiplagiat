#!/usr/bin/env python3
"""Telegram bot for metadata cleaning."""
import os
import tempfile
import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile

from utils.audio_metadata import clean_audio, set_audio_metadata
from utils.video_metadata import clean_video, set_video_metadata
from utils.image_metadata import clean_image, set_image_metadata

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_data = {}


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.reply(
        "Бот для очистки метаданных\n\n"
        "Команды:\n"
        "/clean - очистить метаданные\n"
        "/set - установить свои данные\n\n"
        "Отправьте файл, затем команду"
    )


@dp.message(Command('clean'))
async def cmd_clean(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data or 'file' not in user_data[user_id]:
        await message.reply("Сначала отправьте файл")
        return

    file_info = user_data[user_id]['file']
    await message.reply("Обработка...")

    try:
        result = await process_file(file_info, clean=True)
        if result:
            await message.answer_document(
                FSInputFile(result),
                caption="Файл очищен"
            )
            os.remove(result)
    except Exception as e:
        await message.reply(f"Ошибка: {e}")


@dp.message(Command('set'))
async def cmd_set(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_data or 'file' not in user_data[user_id]:
        await message.reply("Сначала отправьте файл")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.reply(
            "Формат: /set author=Имя title=Название\n"
            "Пример: /set author=МоёИмя title=МояПесня"
        )
        return

    metadata = {}
    for part in args[1].split():
        if '=' in part:
            k, v = part.split('=', 1)
            metadata[k] = v

    if not metadata:
        await message.reply("Неверный формат. Используйте key=value")
        return

    await message.reply("Обработка...")

    try:
        file_info = user_data[user_id]['file']
        result = await process_file(file_info, metadata=metadata)
        if result:
            await message.answer_document(
                FSInputFile(result),
                caption="Метаданные обновлены"
            )
            os.remove(result)
    except Exception as e:
        await message.reply(f"Ошибка: {e}")


@dp.message(F.document)
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    doc = message.document

    supported = ('.mp3', '.wav', '.flac', '.ogg', '.m4a',
                 '.mp4', '.webm', '.avi', '.mov',
                 '.jpg', '.jpeg', '.png', '.webp')

    if not any(doc.file_name.endswith(ext) for ext in supported):
        await message.reply("Формат не поддерживается")
        return

    file = await bot.get_file(doc.file_id)
    tmp = tempfile.mktemp(suffix=Path(doc.file_name).suffix)
    await bot.download_file(file.file_path, tmp)

    user_data[user_id] = {
        'file': tmp,
        'name': doc.file_name
    }

    await message.reply(
        f"Файл принят: {doc.file_name}\n\n"
        "Команды:\n"
        "/clean - очистить все метаданные\n"
        "/set author=Имя title=Название - установить свои данные"
    )


async def process_file(file_path: str, clean=False, metadata=None):
    ext = Path(file_path).suffix.lower()
    output = file_path + '_processed' + ext

    is_audio = ext in ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
    is_video = ext in ('.mp4', '.webm', '.avi', '.mov')
    is_image = ext in ('.jpg', '.jpeg', '.png', '.webp')

    if clean:
        if is_audio:
            clean_audio(file_path, output)
        elif is_video:
            clean_video(file_path, output)
        elif is_image:
            clean_image(file_path, output)
    elif metadata:
        if is_audio:
            set_audio_metadata(file_path, output, metadata)
        elif is_video:
            set_video_metadata(file_path, output, metadata)
        elif is_image:
            set_image_metadata(file_path, output, metadata)

    return output if os.path.exists(output) else None


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
