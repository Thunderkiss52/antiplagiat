#!/usr/bin/env python3
"""Telegram bot for metadata cleaning."""
import os
import tempfile
import asyncio
from pathlib import Path

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from utils.audio_metadata import clean_audio, set_audio_metadata
from utils.video_metadata import clean_video, set_video_metadata
from utils.image_metadata import clean_image, set_image_metadata

BOT_TOKEN = os.getenv('BOT_TOKEN')
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

user_data = {}

AUDIO_EXTS = ('.mp3', '.wav', '.flac', '.ogg', '.m4a')
VIDEO_EXTS = ('.mp4', '.webm', '.avi', '.mov')
IMAGE_EXTS = ('.jpg', '.jpeg', '.png', '.webp')


def get_type_from_ext(ext):
    ext = ext.lower()
    if ext in AUDIO_EXTS:
        return 'audio'
    elif ext in VIDEO_EXTS:
        return 'video'
    elif ext in IMAGE_EXTS:
        return 'image'
    return None


def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Уникализировать музыку", callback_data="select_audio")],
        [InlineKeyboardButton(text="🎬 Уникализировать видео", callback_data="select_video")],
        [InlineKeyboardButton(text="🖼 Уникализировать картинку", callback_data="select_image")],
        [InlineKeyboardButton(text="❓ Помощь", callback_data="help")],
    ])


def get_file_keyboard(detected_type=None):
    if detected_type:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧹 Очистить всё", callback_data=f"do_clean_{detected_type}")],
            [InlineKeyboardButton(text="✏️ Установить имя", callback_data=f"do_set_author_{detected_type}")],
            [InlineKeyboardButton(text="📝 Установить название", callback_data=f"do_set_title_{detected_type}")],
            [InlineKeyboardButton(text="📋 Установить всё", callback_data=f"do_set_all_{detected_type}")],
            [InlineKeyboardButton(text="🔄 Другой файл", callback_data="back")],
        ])
    return get_main_keyboard()


def get_meta_input_keyboard(action, saved):
    buttons = []
    if 'author' not in saved:
        buttons.append([InlineKeyboardButton(text="👤 Имя автора", callback_data=f"input_author_{action}")])
    if 'title' not in saved:
        buttons.append([InlineKeyboardButton(text="📝 Название", callback_data=f"input_title_{action}")])
    if 'album' not in saved:
        buttons.append([InlineKeyboardButton(text="💿 Альбом", callback_data=f"input_album_{action}")])

    if saved:
        summary = "Сохранено:\n"
        if 'author' in saved:
            summary += f"  👤 {saved['author']}\n"
        if 'title' in saved:
            summary += f"  📝 {saved['title']}\n"
        if 'album' in saved:
            summary += f"  💿 {saved['album']}\n"

        buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data=f"finish_set_{action}")])
        buttons.append([InlineKeyboardButton(text="🗑 Очистить всё", callback_data=f"do_clean_{action}")])

    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back")])

    return InlineKeyboardMarkup(inline_keyboard=buttons), buttons


def get_after_done_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Ещё файл", callback_data="back")],
        [InlineKeyboardButton(text="🏠 В меню", callback_data="home")],
    ])


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user_data[message.from_user.id] = {}
    await message.reply(
        "Привет! Я бот для уникализации файлов.\n\n"
        "Отправь мне файл или выбери тип:",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "home")
async def cb_home(callback: CallbackQuery):
    user_data[callback.from_user.id] = {}
    await callback.message.edit_text(
        "Выбери действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "back")
async def cb_back(callback: CallbackQuery):
    user_data[callback.from_user.id] = {}
    await callback.message.edit_text(
        "Отправь файл или выбери тип:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "help")
async def cb_help(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 Помощь\n\n"
        "1. Отправь файл (музыку, видео или картинку)\n"
        "2. Бот автоматически определит тип\n"
        "3. Выбери действие:\n"
        "   - 🧹 Очистить всё — удалит все метаданные\n"
        "   - ✏️ Установить имя — пропишет твоё имя\n"
        "   - 📝 Установить название — пропишет название\n"
        "   - 📋 Установить всё — введёшь все данные\n\n"
        "Поддерживаемые форматы:\n"
        "🎵 mp3, wav, flac, ogg, m4a\n"
        "🎬 mp4, webm, avi, mov\n"
        "🖼 jpg, jpeg, png, webp",
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

    file_info = user_data[user_id]['file']
    await callback.message.edit_text("⏳ Очищаю метаданные...")
    await callback.answer()

    try:
        result = await process_file(file_info, clean=True)
        if result:
            await bot.send_document(
                user_id,
                FSInputFile(result),
                caption="✅ Готово! Метаданные очищены."
            )
            os.remove(result)
            await bot.send_message(
                user_id,
                "Что дальше?",
                reply_markup=get_after_done_keyboard()
            )
    except Exception as e:
        await bot.send_message(user_id, f"❌ Ошибка: {e}")


@dp.callback_query(F.data.startswith("do_set_author_"))
async def cb_do_set_author(callback: CallbackQuery):
    action = callback.data.replace("do_set_author_", "")
    user_id = callback.from_user.id

    if user_id not in user_data or 'file' not in user_data[user_id]:
        await callback.answer("⚠️ Сначала отправь файл!", show_alert=True)
        return

    user_data[user_id]['meta'] = {}
    user_data[user_id]['waiting_for'] = 'author'
    user_data[user_id]['current_action'] = action
    await callback.message.edit_text("👤 Введи имя автора:")
    await callback.answer()


@dp.callback_query(F.data.startswith("do_set_title_"))
async def cb_do_set_title(callback: CallbackQuery):
    action = callback.data.replace("do_set_title_", "")
    user_id = callback.from_user.id

    if user_id not in user_data or 'file' not in user_data[user_id]:
        await callback.answer("⚠️ Сначала отправь файл!", show_alert=True)
        return

    user_data[user_id]['meta'] = {}
    user_data[user_id]['waiting_for'] = 'title'
    user_data[user_id]['current_action'] = action
    await callback.message.edit_text("📝 Введи название:")
    await callback.answer()


@dp.callback_query(F.data.startswith("do_set_all_"))
async def cb_do_set_all(callback: CallbackQuery):
    action = callback.data.replace("do_set_all_", "")
    user_id = callback.from_user.id

    if user_id not in user_data or 'file' not in user_data[user_id]:
        await callback.answer("⚠️ Сначала отправь файл!", show_alert=True)
        return

    user_data[user_id]['meta'] = {}
    user_data[user_id]['current_action'] = action
    kb, _ = get_meta_input_keyboard(action, {})
    await callback.message.edit_text(
        "Настрой метаданные:\nВыбери поле для ввода:",
        reply_markup=kb
    )
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

    file_info = user_data[user_id]['file']
    await callback.message.edit_text("⏳ Сохраняю метаданные...")
    await callback.answer()

    try:
        result = await process_file(file_info, metadata=meta)
        if result:
            await bot.send_document(
                user_id,
                FSInputFile(result),
                caption="✅ Метаданные обновлены!"
            )
            os.remove(result)
            await bot.send_message(
                user_id,
                "Что дальше?",
                reply_markup=get_after_done_keyboard()
            )
    except Exception as e:
        await bot.send_message(user_id, f"❌ Ошибка: {e}")


@dp.message(F.document)
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    doc = message.document

    all_exts = AUDIO_EXTS + VIDEO_EXTS + IMAGE_EXTS
    if not any(doc.file_name.endswith(ext) for ext in all_exts):
        await message.reply("❌ Формат не поддерживается")
        return

    file = await bot.get_file(doc.file_id)
    ext = Path(doc.file_name).suffix.lower()
    tmp = tempfile.mktemp(suffix=ext)
    await bot.download_file(file.file_path, tmp)

    user_data[user_id] = user_data.get(user_id, {})
    user_data[user_id]['file'] = tmp
    user_data[user_id]['name'] = doc.file_name

    detected_type = get_type_from_ext(ext)

    if detected_type:
        user_data[user_id]['current_action'] = detected_type
        type_labels = {'audio': '🎵 Музыка', 'video': '🎬 Видео', 'image': '🖼 Картинка'}
        await message.reply(
            f"✅ Файл принят: {doc.file_name}\n"
            f"Тип: {type_labels[detected_type]}\n\n"
            "Что сделать?",
            reply_markup=get_file_keyboard(detected_type)
        )
    else:
        await message.reply(
            f"✅ Файл принят: {doc.file_name}\n\nВыбери действие:",
            reply_markup=get_main_keyboard()
        )


@dp.message()
async def handle_text(message: types.Message):
    user_id = message.from_user.id
    waiting_for = user_data.get(user_id, {}).get('waiting_for')

    if waiting_for:
        user_data[user_id]['meta'] = user_data[user_id].get('meta', {})
        user_data[user_id]['meta'][waiting_for] = message.text
        user_data[user_id]['waiting_for'] = None
        action = user_data[user_id].get('current_action', 'audio')
        saved = user_data[user_id].get('meta', {})

        kb, _ = get_meta_input_keyboard(action, saved)
        await message.reply(
            f"✅ Сохранено: {message.text}\n\nНастрой ещё:",
            reply_markup=kb
        )


async def process_file(file_path: str, clean=False, metadata=None):
    ext = Path(file_path).suffix.lower()
    output = file_path + '_processed' + ext

    is_audio = ext in AUDIO_EXTS
    is_video = ext in VIDEO_EXTS
    is_image = ext in IMAGE_EXTS

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
