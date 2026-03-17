# План добавления поддержки GIF-анимаций в Telegram Keyword Bot

## Анализ текущей структуры

### Существующие типы реакций:
1. **text** - текстовые сообщения
2. **voice** - голосовые сообщения

### Текущая структура данных:
```json
{
    "keywords": {
        "keyword": {
            "reaction": "текст",
            "probability": 100,
            "reaction_type": "text|voice"
        }
    },
    "voice_reactions": {
        "keyword": "voice_file_id"
    }
}
```

## Методы aiogram для работы с GIF

В aiogram GIF-анимации обрабатываются как:
1. **Animation** - для GIF файлов (message.animation)
2. **Document** - для других анимированных файлов
3. **answer_animation()** - для отправки GIF

### Основные методы:
- `message.answer_animation(animation_file_id)` - отправка GIF по file_id
- `message.animation.file_id` - получение file_id из GIF сообщения
- `message.document.file_id` - для документов (включая некоторые GIF)

## Изменения в структуре данных

### Новая структура:
```json
{
    "keywords": {
        "keyword": {
            "reaction": "текст",
            "probability": 100,
            "reaction_type": "text|voice|gif"
        }
    },
    "voice_reactions": {
        "keyword": "voice_file_id"
    },
    "gif_reactions": {
        "keyword": "animation_file_id"
    }
}
```

## Необходимые изменения в коде

### 1. Обновление default_data
```python
default_data = {
    "admins": [],
    "keywords": {},
    "default_reaction": DEFAULT_REACTION,
    "default_probability": 100,
    "voice_reactions": {},
    "gif_reactions": {}  # Новое поле
}
```

### 2. Новые FSM состояния
```python
class Form(StatesGroup):
    # ... существующие состояния ...
    add_keyword_gif = State()  # Состояние добавления GIF реакции для слова
    waiting_for_gif = State()  # Ожидание GIF сообщения для реакции
    select_keyword_for_gif = State()  # Выбор ключевого слова для GIF реакции
```

### 3. Обновление команд
- Добавить "GIF" в выбор типа реакции
- Создать команду `/set_gif_reaction`
- Обновить справку и список команд

### 4. Обработчики GIF
```python
# Обработчик GIF сообщения для нового ключевого слова
@dp.message(Form.add_keyword_gif)
async def process_add_keyword_gif(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("❌ Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return
    
    # Проверяем, что это GIF анимация
    if not message.animation:
        await message.answer("⚠️ Пожалуйста, отправьте GIF анимацию или нажмите 'Отмена'.")
        return
    
    # Получаем данные из состояния
    user_data = await state.get_data()
    keyword = user_data["keyword"]
    
    # Получаем file_id GIF анимации
    gif_file_id = message.animation.file_id
    
    # Сохраняем GIF реакцию в состоянии для следующего шага
    await state.update_data(gif_file_id=gif_file_id)
    
    await state.set_state(Form.add_keyword_probability)
    await message.answer(
        f"📊 Введите вероятность реакции для ключевого слова '{keyword}' (от 1 до 100 процентов):",
        reply_markup=types.ReplyKeyboardRemove()
    )
```

### 5. Обновление логики отправки реакций
```python
# В функции check_keywords()
if reaction_type == "gif":
    # Проверяем, есть ли GIF реакция для этого ключевого слова
    gif_file_id = data.get("gif_reactions", {}).get(keyword)
    
    if gif_file_id:
        # Отправляем GIF анимацию
        try:
            await message.answer_animation(gif_file_id)
        except Exception as e:
            logging.error(f"Ошибка при отправке GIF: {e}")
            # Если не удалось отправить GIF, отправляем текстовую реакцию
            await message.reply(reaction)
    else:
        # Если GIF реакции нет, отправляем текстовую
        await message.reply(reaction)
```

## Новые команды

### /set_gif_reaction
Команда для установки GIF реакции для существующего ключевого слова.

### Обновленная справка
```python
"/set_gif_reaction - Установить GIF реакцию для слова\n"
"/set_reaction_type - Выбрать тип реакции (текст/голос/GIF)\n"
```

## Обновление выбора типа реакции

### В процессе добавления ключевого слова:
```python
buttons = [
    [types.KeyboardButton(text="Текст")],
    [types.KeyboardButton(text="Голос")],
    [types.KeyboardButton(text="GIF")],  # Новая опция
    [types.KeyboardButton(text="Отмена")]
]
```

### В логике обработки:
```python
if reaction_type not in ["текст", "голос", "gif"]:
    await message.answer("⚠️ Пожалуйста, выберите 'Текст', 'Голос' или 'GIF'.")
    return

reaction_type_mapped = {
    "текст": "text",
    "голос": "voice", 
    "gif": "gif"
}[reaction_type]
```

## Обновление отображения списка ключевых слов

```python
# В cmd_list_keywords()
has_gif = keyword in data.get("gif_reactions", {})

if reaction_type == "gif" and has_gif:
    reaction_type_text = "🎬 GIF"
elif reaction_type == "voice" and has_voice:
    reaction_type_text = "🔊 Голос"
else:
    reaction_type_text = "📝 Текст"
```

## Особенности реализации

### 1. Проверка типа файла
- GIF файлы могут приходить как `animation` или `document`
- Нужно проверять оба типа

### 2. Размер файлов
- Telegram имеет ограничения на размер файлов
- GIF файлы могут быть большими

### 3. Обратная совместимость
- Существующие данные должны продолжать работать
- Добавить миграцию данных при необходимости

### 4. Обработка ошибок
- GIF файлы могут быть недоступны
- Fallback на текстовую реакцию при ошибках

## Тестирование

1. Добавление ключевого слова с GIF реакцией
2. Изменение типа реакции на GIF
3. Установка GIF реакции для существующего слова
4. Проверка срабатывания GIF реакций
5. Обработка ошибок при недоступных GIF