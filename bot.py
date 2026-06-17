#!/usr/bin/env python3
"""Telegram bot for metadata cleaning."""
import os
import sys
import tempfile
import logging
import subprocess
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from utils.audio_metadata import clean_audio, set_audio_metadata
from utils.video_metadata import clean_video, set_video_metadata
from utils.image_metadata import clean_image, set_image_metadata

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_data = {}

AUDIO_EXTS = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
VIDEO_EXTS = ('.mp4', '.webm', '.avi', '.mov')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp')
ALL_EXTS = AUDIO_EXTS + VIDEO_EXTS + IMAGE_EXTS

MAX_FILE_SIZE = 50 * 1024 * 1024


def get_type_from_ext(ext):
    ext = ext.lower()
    if ext in AUDIO_EXTS:
        return 'audio'
    elif ext in VIDEO_EXTS:
        return 'video'
    elif ext in IMAGE_EXTS:
        return 'image'
    return None


def get_file_size(filepath):
    return os.path.getsize(filepath)


def main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎵 Уникализировать музыку")],
            [KeyboardButton(text="🎬 Уникализировать видео")],
            [KeyboardButton(text="🖼 Уникализировать картинку")],
            [KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True
    )


def action_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧹 Очистить метаданные")],
            [KeyboardButton(text="✏️ Установить свои данные")],
            [KeyboardButton(text="⬅️ Назад")],
        ],
        resize_keyboard=True
    )


def meta_kb(action, saved):
    buttons = []
    if 'author' not in saved:
        buttons.append([KeyboardButton(text="👤 Имя автора")])
    if 'title' not in saved:
        buttons.append([KeyboardButton(text="📝 Название")])
    if 'album' not in saved and action == 'audio':
        buttons.append([KeyboardButton(text="💿 Альбом")])
    if saved:
        buttons.append([KeyboardButton(text="✅ Применить")])
        buttons.append([KeyboardButton(text="🗑 Сбросить")])
    buttons.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def done_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔄 Ещё файл")],
            [KeyboardButton(text="🏠 В меню")],
        ],
        resize_keyboard=True
    )


async def send_result(user_id, result_path, caption):
    size = get_file_size(result_path)
    if size > MAX_FILE_SIZE:
        os.remove(result_path)
        await bot.send_message(
            user_id,
            f"❌ Файл слишком большой ({size // 1024 // 1024}MB). Лимит Telegram — 50MB.",
            reply_markup=main_kb()
        )
        return

    original_name = user_data.get(user_id, {}).get('name', Path(result_path).name)
    await bot.send_document(user_id, FSInputFile(result_path, filename=original_name), caption=caption)
    os.remove(result_path)
    await bot.send_message(user_id, "Что дальше?", reply_markup=done_kb())


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user_data[message.from_user.id] = {}
    await message.reply(
        "Привет! Я бот для уникализации файлов.\n\n"
        "Как это работает:\n"
        "1. Выбери тип файла на клавиатуре ниже\n"
        "2. Отправь файл\n"
        "3. Выбери действие\n"
        "4. Получи обработанный файл\n\n"
        "Поддержка: mp3, wav, flac, ogg, m4a, mp4, webm, avi, mov, jpg, jpeg, png, webp\n"
        "Лимит файла: 50MB",
        reply_markup=main_kb()
    )


@dp.message(F.document | F.video | F.photo)
async def handle_file(message: types.Message):
    user_id = message.from_user.id

    doc = message.document
    if message.video:
        doc = message.video
    if message.photo:
        doc = message.photo[-1]

    file_name = getattr(doc, 'file_name', None) or 'unknown'
    ext = Path(file_name).suffix.lower() if file_name != 'unknown' else ''

    if not ext or ext not in ALL_EXTS:
        if message.photo:
            ext = '.jpg'
            file_name = f"photo_{message.photo[-1].file_id[:8]}.jpg"
        else:
            await message.reply("❌ Формат не поддерживается")
            return

    file_size = getattr(doc, 'file_size', 0) or 0
    if file_size > MAX_FILE_SIZE:
        await message.reply(
            f"❌ Файл слишком большой ({file_size // 1024 // 1024}MB). Лимит 50MB.",
            reply_markup=main_kb()
        )
        return

    try:
        tg_file = await bot.get_file(doc.file_id)
        tmp = tempfile.mktemp(suffix=ext)
        await bot.download_file(tg_file.file_path, tmp)
        logger.info(f"Downloaded: {tmp} ({get_file_size(tmp)} bytes)")
    except Exception as e:
        logger.exception(f"Download error: {e}")
        await message.reply(f"❌ Ошибка скачивания: {e}")
        return

    user_data[user_id] = user_data.get(user_id, {})
    user_data[user_id]['file'] = tmp
    user_data[user_id]['name'] = file_name

    detected_type = get_type_from_ext(ext)
    if detected_type:
        user_data[user_id]['current_action'] = detected_type
        type_labels = {'audio': '🎵 Музыка', 'video': '🎬 Видео', 'image': '🖼 Картинка'}
        await message.reply(
            f"✅ Файл: {file_name}\nТип: {type_labels[detected_type]}\n\nЧто сделать?",
            reply_markup=action_kb()
        )
    else:
        await message.reply(
            f"✅ Файл: {file_name}\n\nВыбери действие:",
            reply_markup=main_kb()
        )


@dp.message(F.text)
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    text = message.text
    state = user_data.get(user_id, {})

    if state.get('waiting_for'):
        field = state['waiting_for']
        action = state.get('current_action', 'audio')

        user_data[user_id]['meta'] = user_data[user_id].get('meta', {})
        user_data[user_id]['meta'][field] = text
        user_data[user_id]['waiting_for'] = None

        saved = user_data[user_id].get('meta', {})
        labels = {'author': '👤 Имя автора', 'title': '📝 Название', 'album': '💿 Альбом'}
        summary = '\n'.join(f"  {labels.get(k, k)}: {v}" for k, v in saved.items())
        await message.answer(
            f"✅ {labels.get(field, field)}: {text}\n\nУже сохранено:\n{summary}\n\nНастрой ещё или нажми «Применить»:",
            reply_markup=meta_kb(action, saved)
        )
        return

    if text == "🏠 В меню":
        user_data[user_id] = {}
        await message.answer("Главное меню:", reply_markup=main_kb())

    elif text == "⬅️ Назад":
        user_data[user_id] = {}
        await message.answer("Выбери действие:", reply_markup=main_kb())

    elif text == "🎵 Уникализировать музыку":
        user_data[user_id] = {'waiting_type': 'audio'}
        await message.answer("🎵 Музыка\n\nОтправь аудиофайл:", reply_markup=ReplyKeyboardRemove())

    elif text == "🎬 Уникализировать видео":
        user_data[user_id] = {'waiting_type': 'video'}
        await message.answer("🎬 Видео\n\nОтправь видеофайл:", reply_markup=ReplyKeyboardRemove())

    elif text == "🖼 Уникализировать картинку":
        user_data[user_id] = {'waiting_type': 'image'}
        await message.answer("🖼 Картинка\n\nОтправь картинку:", reply_markup=ReplyKeyboardRemove())

    elif text == "❓ Помощь":
        await message.answer(
            "📋 Помощь\n\n"
            "1. Выбери тип файла на клавиатуре\n"
            "2. Отправь файл\n"
            "3. Выбери действие:\n"
            "   🧹 Очистить — удалит все метаданные\n"
            "   ✏️ Установить — пропишет твои данные\n\n"
            "Форматы:\n"
            "🎵 mp3, wav, flac, ogg, m4a\n"
            "🎬 mp4, webm, avi, mov\n"
            "🖼 jpg, jpeg, png, webp\n\n"
            "Лимит: 50MB",
            reply_markup=main_kb()
        )

    elif text == "🧹 Очистить метаданные":
        if 'file' not in state:
            await message.answer("⚠️ Сначала отправь файл!", reply_markup=main_kb())
            return

        file_path = state['file']
        logger.info(f"Cleaning file: {file_path}")
        await message.answer("⏳ Очищаю метаданные...")

        try:
            result = await process_file(file_path, clean=True)
            if result:
                await send_result(user_id, result, "✅ Метаданные очищены!")
            else:
                await bot.send_message(user_id, "❌ Не удалось обработать файл", reply_markup=done_kb())
        except Exception as e:
            logger.exception(f"Clean error: {e}")
            await bot.send_message(user_id, f"❌ Ошибка: {e}", reply_markup=done_kb())

    elif text == "✏️ Установить свои данные":
        if 'file' not in state:
            await message.answer("⚠️ Сначала отправь файл!", reply_markup=main_kb())
            return

        action = state.get('current_action', 'audio')
        user_data[user_id]['meta'] = {}
        user_data[user_id]['current_action'] = action
        await message.answer("Настрой метаданные:\nВыбери поле:", reply_markup=meta_kb(action, {}))

    elif text == "👤 Имя автора":
        user_data[user_id]['waiting_for'] = 'author'
        await message.answer("Введи имя автора:", reply_markup=ReplyKeyboardRemove())

    elif text == "📝 Название":
        user_data[user_id]['waiting_for'] = 'title'
        await message.answer("Введи название:", reply_markup=ReplyKeyboardRemove())

    elif text == "💿 Альбом":
        user_data[user_id]['waiting_for'] = 'album'
        await message.answer("Введи альбом:", reply_markup=ReplyKeyboardRemove())

    elif text == "✅ Применить":
        meta = state.get('meta', {})
        if not meta:
            await message.answer("⚠️ Укажи хотя бы одно поле!")
            return

        file_path = state.get('file')
        logger.info(f"Setting metadata on {file_path}: {meta}")
        await message.answer("⏳ Сохраняю...")

        try:
            result = await process_file(file_path, metadata=meta)
            if result:
                await send_result(user_id, result, "✅ Метаданные обновлены!")
            else:
                await bot.send_message(user_id, "❌ Не удалось обработать файл", reply_markup=done_kb())
        except Exception as e:
            logger.exception(f"Set metadata error: {e}")
            await bot.send_message(user_id, f"❌ Ошибка: {e}", reply_markup=done_kb())

    elif text == "🗑 Сбросить":
        file_path = state.get('file')
        if not file_path:
            await message.answer("⚠️ Сначала отправь файл!", reply_markup=main_kb())
            return

        user_data[user_id]['meta'] = {}
        logger.info(f"Cleaning file after reset: {file_path}")
        await message.answer("⏳ Очищаю метаданные...")

        try:
            result = await process_file(file_path, clean=True)
            if result:
                await send_result(user_id, result, "✅ Метаданные очищены!")
            else:
                await bot.send_message(user_id, "❌ Не удалось обработать файл", reply_markup=done_kb())
        except Exception as e:
            logger.exception(f"Clean error: {e}")
            await bot.send_message(user_id, f"❌ Ошибка: {e}", reply_markup=done_kb())

    elif text == "🔄 Ещё файл":
        user_data[user_id] = {}
        await message.answer("Отправь файл или выбери тип:", reply_markup=main_kb())

    else:
        await message.answer("Выбери действие:", reply_markup=main_kb())


async def process_file(file_path: str, clean=False, metadata=None):
    ext = Path(file_path).suffix.lower()
    output = file_path + '_processed' + ext

    logger.info(f"Processing: {file_path} -> {output} (clean={clean}, meta={metadata})")

    try:
        if clean:
            if ext in AUDIO_EXTS:
                clean_audio(file_path, output)
            elif ext in VIDEO_EXTS:
                clean_video(file_path, output)
            elif ext in IMAGE_EXTS:
                clean_image(file_path, output)
        elif metadata:
            if ext in AUDIO_EXTS:
                set_audio_metadata(file_path, output, metadata)
            elif ext in VIDEO_EXTS:
                set_video_metadata(file_path, output, metadata)
            elif ext in IMAGE_EXTS:
                set_image_metadata(file_path, output, metadata)

        if os.path.exists(output):
            logger.info(f"Output created: {output} ({get_file_size(output)} bytes)")
            return output
        else:
            logger.error(f"Output not created: {output}")
            return None
    except Exception as e:
        logger.exception(f"process_file error: {e}")
        raise


async def main():
    logger.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
