# Metadata Tool

Инструмент для очистки и обновления метаданных аудио, видео и изображений.

## Установка

```bash
pip install -r requirements.txt
```

Также нужен `ffmpeg` для видео:
```bash
sudo apt install ffmpeg
```

## CLI использование

```bash
# Очистить метаданные
python cli.py input.mp3 -c

# Установить автора
python cli.py input.mp3 --author "Моё Имя" --title "Моя Песня"

# Указать выходной файл
python cli.py input.mp3 -c -o output.mp3
```

## Telegram бот

1. Получите токен у @BotFather
2. Запустите:
```bash
export BOT_TOKEN="ваш_токен"
python bot.py
```

3. Использование в боте:
   - Отправьте файл
   - `/clean` - очистить метаданные
   - `/set author=Имя title=Название` - установить данные

## Поддерживаемые форматы

- **Аудио**: mp3, wav, flac, ogg, m4a
- **Видео**: mp4, webm, avi, mov
- **Изображения**: jpg, jpeg, png, webp
