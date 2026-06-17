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


def get_main_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎵 Уникализировать музыку", callback_data="action_audio")],
        [InlineKeyboardButton(text="🎬 Уникализировать видео", callback_data="action_video")],
        [InlineKeyboardButton(text="🖼 Уникализировать картинку", callback_data="action_image")],
    ])


def get_confirm_keyboard(action):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Очистить метаданные", callback_data=f"clean_{action}")],
        [InlineKeyboardButton(text="✏️ Установить свои данные", callback_data=f"set_{action}")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


def get_set_meta_keyboard(action):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Указать имя автора", callback_data=f"meta_{action}_author")],
        [InlineKeyboardButton(text="Указать название", callback_data=f"meta_{action}_title")],
        [InlineKeyboardButton(text="Готово", callback_data=f"meta_{action}_done")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back")],
    ])


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    await message.reply(
        "Привет! Я бот для уникализации файлов.\n\n"
        "Выбери действие:",
        reply_markup=get_main_keyboard()
    )


@dp.callback_query(F.data == "back")
async def cb_back(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выбери действие:",
        reply_markup=get_main_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("action_"))
async def cb_action(callback: CallbackQuery):
    action = callback.data.replace("action_", "")
    user_id = callback.from_user.id

    labels = {
        "audio": "🎵 Музыка",
        "video": "🎬 Видео",
        "image": "🖼 Картинка"
    }

    user_data[user_id] = user_data.get(user_id, {})
    user_data[user_id]['current_action'] = action

    await callback.message.edit_text(
        f"{labels[action]}\n\n"
        "Отправь файл, затем нми на кнопку.",
        reply_markup=get_confirm_keyboard(action)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("clean_"))
async def cb_clean(callback: CallbackQuery):
    action = callback.data.replace("clean_", "")
    user_id = callback.from_user.id

    if user_id not in user_data or 'file' not in user_data[user_id]:
        await callback.answer("Сначала отправь файл!", show_alert=True)
        return

    file_info = user_data[user_id]['file']
    await callback.message.edit_text("⏳ Обработка...")
    await callback.answer()

    try:
        result = await process_file(file_info, clean=True)
        if result:
            await bot.send_document(
                user_id,
                FSInputFile(result),
                caption="✅ Файл очищен"
            )
            os.remove(result)
    except Exception as e:
        await bot.send_message(user_id, f"❌ Ошибка: {e}")


@dp.callback_query(F.data.startswith("set_"))
async def cb_set(callback: CallbackQuery):
    action = callback.data.replace("set_", "")
    user_id = callback.from_user.id

    if user_id not in user_data or 'file' not in user_data[user_id]:
        await callback.answer("Сначала отправь файл!", show_alert=True)
        return

    user_data[user_id]['meta'] = {}
    await callback.message.edit_text(
        "Настрой метаданные:",
        reply_markup=get_set_meta_keyboard(action)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("meta_"))
async def cb_meta(callback: CallbackQuery):
    parts = callback.data.split("_")
    action = parts[1]
    field = parts[2] if len(parts) > 2 else None
    user_id = callback.from_user.id

    if field == "done":
        meta = user_data.get(user_id, {}).get('meta', {})
        if not meta:
            await callback.answer("Укажи хотя бы одно поле!", show_alert=True)
            return

        file_info = user_data[user_id]['file']
        await callback.message.edit_text("⏳ Обработка...")
        await callback.answer()

        try:
            result = await process_file(file_info, metadata=meta)
            if result:
                await bot.send_document(
                    user_id,
                    FSInputFile(result),
                    caption="✅ Метаданные обновлены"
                )
                os.remove(result)
        except Exception as e:
            await bot.send_message(user_id, f"❌ Ошибка: {e}")
        return

    user_data[user_id]['waiting_for'] = field
    user_data[user_id]['current_action'] = action
    await callback.message.edit_text(
        f"Введи {'имя автора' if field == 'author' else 'название'}:"
    )
    await callback.answer()


@dp.message(F.document)
async def handle_document(message: types.Message):
    user_id = message.from_user.id
    doc = message.document

    all_exts = AUDIO_EXTS + VIDEO_EXTS + IMAGE_EXTS
    if not any(doc.file_name.endswith(ext) for ext in all_exts):
        await message.reply("❌ Формат не поддерживается")
        return

    file = await bot.get_file(doc.file_id)
    tmp = tempfile.mktemp(suffix=Path(doc.file_name).suffix)
    await bot.download_file(file.file_path, tmp)

    user_data[user_id] = user_data.get(user_id, {})
    user_data[user_id]['file'] = tmp
    user_data[user_id]['name'] = doc.file_name

    action = user_data[user_id].get('current_action')

    if action:
        await message.reply(
            f"✅ Файл принят: {doc.file_name}",
            reply_markup=get_confirm_keyboard(action)
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

        await message.reply(
            "✅ Сохранено. Настрой ещё или нми «Готово»:",
            reply_markup=get_set_meta_keyboard(action)
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
