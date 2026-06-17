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
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

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


def main_menu_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Уникализировать музыку", callback_data="select_audio")],
        [InlineKeyboardButton(text="🎬 Уникализировать видео", callback_data="select_video")],
        [InlineKeyboardButton(text="🖼 Уникализировать картинку", callback_data="select_image")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ])


def file_action_kb(filetype):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Очистить метаданные", callback_data=f"do_clean_{filetype}")],
        [InlineKeyboardButton(text="✏️ Установить свои данные", callback_data=f"do_set_all_{filetype}")],
        [InlineKeyboardButton(text="🔄 Другой файл", callback_data="back")],
    ])


def meta_kb(action, saved):
    buttons = []
    if 'author' not in saved:
        buttons.append([InlineKeyboardButton(text="👤 Имя автора", callback_data=f"input_author_{action}")])
    if 'title' not in saved:
        buttons.append([InlineKeyboardButton(text="📝 Название", callback_data=f"input_title_{action}")])
    if 'album' not in saved and action == 'audio':
        buttons.append([InlineKeyboardButton(text="💿 Альбом", callback_data=f"input_album_{action}")])

    if saved:
        buttons.append([InlineKeyboardButton(text="✅ Применить", callback_data=f"finish_set_{action}")])
        buttons.append([InlineKeyboardButton(text="🗑 Сбросить", callback_data=f"do_clean_{action}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def done_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё файл", callback_data="back")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="home")],
    ])


def file_size_warn_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


async def send_result(user_id, result_path, caption):
    size = get_file_size(result_path)
    if size > MAX_FILE_SIZE:
        os.remove(result_path)
        await bot.send_message(
            user_id,
            f"❌ Файл слишком большой ({size // 1024 // 1024}MB). Лимит Telegram — 50MB.",
            reply_markup=file_size_warn_kb()
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
        "1. Отправь файл (музыку, видео или картинку)\n"
        "2. Бот определит тип автоматически\n"
        "3. Нажми кнопку нужного действия\n"
        "4. Получи обработанный файл\n\n"
        "Кнопки:\n"
        "🧹 Очистить — удалит все старые метаданные\n"
        "✏️ Установить — пропишет имя и название\n\n"
        "Поддержка: mp3, wav, flac, ogg, m4a, mp4, webm, avi, mov, jpg, jpeg, png, webp\n"
        "Лимит файла: 50MB\n\n"
        "Выбери действие или сразу отправь файл:",
        reply_markup=main_menu_kb()
    )


@dp.callback_query(F.data.in_({"home", "back"}))
async def cb_home(callback: CallbackQuery):
    user_data[callback.from_user.id] = {}
    await callback.message.edit_text(
        "Отправь файл или выбери тип:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@dp.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 Помощь\n\n"
        "1. Отправь файл (музыку, видео или картинку)\n"
        "2. Бот определит тип автоматически\n"
        "3. Выбери действие:\n"
        "   🧹 Очистить — удалит все метаданные\n"
        "   ✏️ Установить — пропишет твои данные\n\n"
        "Форматы:\n"
        "🎵 mp3, wav, flac, ogg, m4a\n"
        "🎬 mp4, webm, avi, mov\n"
        "🖼 jpg, jpeg, png, webp\n\n"
        "Лимит: 50MB",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("select_"))
async def cb_select(callback: CallbackQuery):
    action = callback.data.replace("select_", "")
    user_id = callback.from_user.id
    user_data[user_id] = user_data.get(user_id, {})
    user_data[user_id]['waiting_type'] = action

    labels = {"audio": "🎵 Музыка", "video": "🎬 Видео", "image": "🖼 Картинка"}
    await callback.message.edit_text(
        f"{labels[action]}\n\nОтправь файл:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("do_clean_"))
async def cb_do_clean(callback: CallbackQuery):
    action = callback.data.replace("do_clean_", "")
    user_id = callback.from_user.id

    if user_id not in user_data or 'file' not in user_data[user_id]:
        await callback.answer("⚠️ Сначала отправь файл!", show_alert=True)
        return

    file_path = user_data[user_id]['file']
    logger.info(f"Cleaning file: {file_path}")
    await callback.message.edit_text("⏳ Очищаю метаданные...")
    await callback.answer()

    try:
        result = await process_file(file_path, clean=True)
        if result:
            await send_result(user_id, result, "✅ Метаданные очищены!")
        else:
            await bot.send_message(user_id, "❌ Не удалось обработать файл", reply_markup=done_kb())
    except Exception as e:
        logger.exception(f"Clean error: {e}")
        await bot.send_message(user_id, f"❌ Ошибка: {e}", reply_markup=done_kb())


@dp.callback_query(F.data.startswith("do_set_all_"))
async def cb_do_set_all(callback: CallbackQuery):
    action = callback.data.replace("do_set_all_", "")
    user_id = callback.from_user.id

    if user_id not in user_data or 'file' not in user_data[user_id]:
        await callback.answer("⚠️ Сначала отправь файл!", show_alert=True)
        return

    user_data[user_id]['meta'] = {}
    user_data[user_id]['current_action'] = action
    kb = meta_kb(action, {})
    await callback.message.edit_text("Настрой метаданные:\nВыбери поле:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data.startswith("input_"))
async def cb_input(callback: CallbackQuery):
    parts = callback.data.split("_")
    field = parts[1]
    action = parts[2]
    user_id = callback.from_user.id

    user_data[user_id]['waiting_for'] = field
    user_data[user_id]['current_action'] = action

    labels = {'author': '👤 имя автора', 'title': '📝 название', 'album': '💿 альбом'}
    await callback.message.edit_text(f"Введи {labels[field]}:")
    await callback.answer()


@dp.callback_query(F.data.startswith("finish_set_"))
async def cb_finish_set(callback: CallbackQuery):
    action = callback.data.replace("finish_set_", "")
    user_id = callback.from_user.id

    meta = user_data.get(user_id, {}).get('meta', {})
    if not meta:
        await callback.answer("⚠️ Укажи хотя бы одно поле!", show_alert=True)
        return

    file_path = user_data[user_id]['file']
    logger.info(f"Setting metadata on {file_path}: {meta}")
    await callback.message.edit_text("⏳ Сохраняю...")
    await callback.answer()

    try:
        result = await process_file(file_path, metadata=meta)
        if result:
            await send_result(user_id, result, "✅ Метаданные обновлены!")
        else:
            await bot.send_message(user_id, "❌ Не удалось обработать файл", reply_markup=done_kb())
    except Exception as e:
        logger.exception(f"Set metadata error: {e}")
        await bot.send_message(user_id, f"❌ Ошибка: {e}", reply_markup=done_kb())


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
            reply_markup=main_menu_kb()
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
            reply_markup=file_action_kb(detected_type)
        )
    else:
        await message.reply(
            f"✅ Файл: {file_name}\n\nВыбери действие:",
            reply_markup=main_menu_kb()
        )


@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    waiting_for = user_data.get(user_id, {}).get('waiting_for')

    if not waiting_for:
        await message.reply("Отправь файл или выбери действие:", reply_markup=main_menu_kb())
        return

    user_data[user_id]['meta'] = user_data[user_id].get('meta', {})
    user_data[user_id]['meta'][waiting_for] = message.text
    user_data[user_id]['waiting_for'] = None
    action = user_data[user_id].get('current_action', 'audio')
    saved = user_data[user_id].get('meta', {})

    kb = meta_kb(action, saved)
    await message.reply(f"✅ {message.text}\n\nНастрой ещё:", reply_markup=kb)


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
