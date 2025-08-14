import logging
import json
import os
import random
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import Command

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
API_TOKEN = "8138806291:AAE4PYZjKkBd4La8DSjfmqL8mg1JrnU1APM"  # Замените на свой токен от BotFather
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Файл для хранения ключевых слов и ID администраторов
KEYWORDS_FILE = "keywords.json"
DEFAULT_REACTION = "⚠️ Обнаружено ключевое слово!"

# Структура данных по умолчанию
default_data = {
    "admins": [],  # Список имен пользователей-администраторов
    "keywords": {},  # Словарь ключевых слов, их реакций и вероятностей
    "default_reaction": DEFAULT_REACTION,  # Реакция по умолчанию для новых слов
    "default_probability": 100,  # Вероятность реакции по умолчанию (в процентах)
    "voice_reactions": {}  # Словарь голосовых реакций (ключ: keyword, значение: file_id)
}

# Путь к файлу с именами администраторов
ADMINS_FILE = "admis.json"

# Загрузка списка администраторов из файла
def load_admins():
    if os.path.exists(ADMINS_FILE):
        with open(ADMINS_FILE, "r", encoding="utf-8") as file:
            try:
                # Пробуем загрузить как JSON
                return json.load(file)
            except json.JSONDecodeError:
                # Если не получилось, считаем, что это текстовый файл со списком имен
                file.seek(0)  # Возвращаемся в начало файла
                return [line.strip() for line in file if line.strip()]
    else:
        return []

# Загрузка данных из файла
def load_data():
    if os.path.exists(KEYWORDS_FILE):
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as file:
            try:
                return json.load(file)
            except json.JSONDecodeError:
                return default_data.copy()
    else:
        return default_data.copy()

# Сохранение данных в файл
def save_data(data):
    with open(KEYWORDS_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

# Состояния для FSM (конечного автомата)
class Form(StatesGroup):
    add_keyword = State()  # Состояние добавления ключевого слова
    add_keyword_reaction = State()  # Состояние добавления реакции для слова
    add_keyword_probability = State()  # Состояние добавления вероятности для слова
    remove_keyword = State()  # Состояние удаления ключевого слова
    set_reaction = State()  # Состояние установки реакции для слова
    set_probability = State()  # Состояние установки вероятности для слова
    select_keyword_for_reaction = State()  # Выбор слова для изменения реакции
    select_keyword_for_probability = State()  # Выбор слова для изменения вероятности
    set_default_reaction = State()  # Установка реакции по умолчанию
    set_default_probability = State()  # Установка вероятности по умолчанию
    add_admin = State()  # Состояние добавления администратора
    waiting_for_voice = State()  # Ожидание голосового сообщения для реакции
    select_keyword_for_voice = State()  # Выбор ключевого слова для голосовой реакции

# Проверка на администратора
def is_admin(message):
    # Получаем имя пользователя
    username = message.from_user.username
    
    # Если имя пользователя не задано, используем ID как строку
    if not username:
        username = str(message.from_user.id)
    
    # Загружаем список администраторов из файла
    admins_from_file = load_admins()
    
    # Проверяем, есть ли пользователь в списке администраторов из файла
    if username in admins_from_file:
        return True
    
    # Проверяем в основных данных
    data = load_data()
    
    # Если список администраторов пуст, первый пользователь становится администратором
    if not data["admins"]:
        data["admins"].append(username)
        save_data(data)
        return True
        
    return username in data["admins"]

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Привет! Я бот для отслеживания ключевых слов в чате.\n\n"
        "Если вы администратор, вы можете использовать следующие команды:\n"
        "/add_keyword - Добавить ключевое слово\n"
        "/remove_keyword - Удалить ключевое слово\n"
        "/list_keywords - Показать список ключевых слов\n"
        "/set_reaction - Изменить реакцию для конкретного слова\n"
        "/set_probability - Изменить вероятность реакции для слова\n"
        "/set_default - Установить реакцию по умолчанию\n"
        "/set_default_prob - Установить вероятность по умолчанию\n"
        "/set_voice_reaction - Установить голосовую реакцию для слова\n"
        "/add_admin - Добавить нового администратора\n"
        "/help - Показать справку"
    )

# Обработчик команды /help
@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer(
        "📚 Справка по командам:\n\n"
        "/add_keyword - Добавить ключевое слово\n"
        "/remove_keyword - Удалить ключевое слово\n"
        "/list_keywords - Показать список ключевых слов\n"
        "/set_reaction - Изменить реакцию для конкретного слова\n"
        "/set_probability - Изменить вероятность реакции для слова\n"
        "/set_default - Установить реакцию по умолчанию\n"
        "/set_default_prob - Установить вероятность по умолчанию\n"
        "/set_voice_reaction - Установить голосовую реакцию для слова\n"
        "/add_admin - Добавить нового администратора\n"
        "/help - Показать эту справку"
    )

# Обработчик команды /add_keyword
@dp.message(Command("add_keyword"))
async def cmd_add_keyword(message: types.Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await state.set_state(Form.add_keyword)
    await message.answer("📝 Введите ключевое слово или фразу для добавления:")

# Обработчик ввода нового ключевого слова
@dp.message(Form.add_keyword)
async def process_add_keyword(message: types.Message, state: FSMContext):
    keyword = message.text.lower().strip()
    
    # Сохраняем ключевое слово в состоянии для следующего шага
    await state.update_data(keyword=keyword)
    
    data = load_data()
    if keyword in data["keywords"]:
        await message.answer(f"⚠️ Ключевое слово '{keyword}' уже существует.")
        await state.clear()
    else:
        await state.set_state(Form.add_keyword_reaction)
        await message.answer(f"📝 Введите реакцию для ключевого слова '{keyword}':")

# Обработчик ввода реакции для нового ключевого слова
@dp.message(Form.add_keyword_reaction)
async def process_add_keyword_reaction(message: types.Message, state: FSMContext):
    reaction = message.text
    
    # Получаем ключевое слово из состояния
    user_data = await state.get_data()
    keyword = user_data["keyword"]
    
    # Сохраняем реакцию в состоянии для следующего шага
    await state.update_data(reaction=reaction)
    
    await state.set_state(Form.add_keyword_probability)
    await message.answer(
        f"📊 Введите вероятность реакции для ключевого слова '{keyword}' (от 1 до 100 процентов):"
    )

# Обработчик ввода вероятности для нового ключевого слова
@dp.message(Form.add_keyword_probability)
async def process_add_keyword_probability(message: types.Message, state: FSMContext):
    try:
        probability = int(message.text.strip())
        if probability < 1 or probability > 100:
            await message.answer("⚠️ Вероятность должна быть от 1 до 100 процентов. Попробуйте снова:")
            return
        
        # Получаем данные из состояния
        user_data = await state.get_data()
        keyword = user_data["keyword"]
        reaction = user_data["reaction"]
        
        data = load_data()
        data["keywords"][keyword] = {
            "reaction": reaction,
            "probability": probability
        }
        save_data(data)
        
        await message.answer(
            f"✅ Ключевое слово '{keyword}' успешно добавлено:\n"
            f"• Реакция: {reaction}\n"
            f"• Вероятность: {probability}%"
        )
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Ошибка: вероятность должна быть числом. Попробуйте снова:")

# Обработчик команды /remove_keyword
@dp.message(Command("remove_keyword"))
async def cmd_remove_keyword(message: types.Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    data = load_data()
    if not data["keywords"]:
        await message.answer("⚠️ Список ключевых слов пуст.")
        return
    
    await state.set_state(Form.remove_keyword)
    
    # Создаем клавиатуру в новом формате
    buttons = []
    for keyword in data["keywords"]:
        buttons.append([types.KeyboardButton(text=keyword)])
    buttons.append([types.KeyboardButton(text="Отмена")])
    
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("🗑️ Выберите ключевое слово для удаления:", reply_markup=keyboard)

# Обработчик удаления ключевого слова
@dp.message(Form.remove_keyword)
async def process_remove_keyword(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("❌ Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return
    
    keyword = message.text.lower().strip()
    data = load_data()
    
    if keyword in data["keywords"]:
        del data["keywords"][keyword]
        save_data(data)
        await message.answer(f"✅ Ключевое слово '{keyword}' успешно удалено.",
                            reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer(f"⚠️ Ключевое слово '{keyword}' не найдено.",
                            reply_markup=types.ReplyKeyboardRemove())
    
    await state.clear()

# Обработчик команды /list_keywords
@dp.message(Command("list_keywords"))
async def cmd_list_keywords(message: types.Message):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    data = load_data()
    if not data["keywords"]:
        await message.answer("📋 Список ключевых слов пуст.")
    else:
        keywords_text = []
        for keyword, info in data["keywords"].items():
            if isinstance(info, dict):
                reaction = info.get("reaction", "Не задана")
                probability = info.get("probability", 100)
                keywords_text.append(f"• {keyword}: {reaction} (вероятность: {probability}%)")
            else:
                # Для обратной совместимости со старым форматом
                keywords_text.append(f"• {keyword}: {info} (вероятность: 100%)")
        
        default_reaction = data.get("default_reaction", DEFAULT_REACTION)
        default_probability = data.get("default_probability", 100)
        
        await message.answer(
            f"📋 Список ключевых слов и их реакций:\n\n"
            f"{chr(10).join(keywords_text)}\n\n"
            f"Реакция по умолчанию: {default_reaction}\n"
            f"Вероятность по умолчанию: {default_probability}%"
        )

# Обработчик команды /set_reaction
@dp.message(Command("set_reaction"))
async def cmd_set_reaction(message: types.Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    data = load_data()
    if not data["keywords"]:
        await message.answer("⚠️ Список ключевых слов пуст. Сначала добавьте ключевые слова.")
        return
    
    await state.set_state(Form.select_keyword_for_reaction)
    
    # Создаем клавиатуру в новом формате
    buttons = []
    for keyword in data["keywords"]:
        buttons.append([types.KeyboardButton(text=keyword)])
    buttons.append([types.KeyboardButton(text="Отмена")])
    
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("📝 Выберите ключевое слово, для которого нужно изменить реакцию:",
                        reply_markup=keyboard)

# Обработчик выбора ключевого слова для изменения реакции
@dp.message(Form.select_keyword_for_reaction)
async def process_select_keyword(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("❌ Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return
    
    keyword = message.text.lower().strip()
    data = load_data()
    
    if keyword in data["keywords"]:
        if isinstance(data["keywords"][keyword], dict):
            current_reaction = data["keywords"][keyword].get("reaction", "Не задана")
        else:
            # Для обратной совместимости со старым форматом
            current_reaction = data["keywords"][keyword]
            
        await state.update_data(keyword=keyword)
        await state.set_state(Form.set_reaction)
        await message.answer(f"📝 Текущая реакция для '{keyword}': {current_reaction}\n\n"
                            f"Введите новую реакцию:", reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer(f"⚠️ Ключевое слово '{keyword}' не найдено.",
                            reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

# Обработчик установки новой реакции для ключевого слова
@dp.message(Form.set_reaction)
async def process_set_reaction(message: types.Message, state: FSMContext):
    new_reaction = message.text
    
    # Получаем ключевое слово из состояния
    user_data = await state.get_data()
    keyword = user_data["keyword"]
    
    data = load_data()
    
    # Проверяем формат данных и обновляем соответственно
    if isinstance(data["keywords"].get(keyword), dict):
        data["keywords"][keyword]["reaction"] = new_reaction
    else:
        # Преобразуем в новый формат
        old_reaction = data["keywords"].get(keyword, "")
        data["keywords"][keyword] = {
            "reaction": new_reaction,
            "probability": 100  # По умолчанию 100%
        }
    
    save_data(data)
    
    await message.answer(f"✅ Реакция для ключевого слова '{keyword}' успешно изменена на: {new_reaction}")
    await state.clear()

# Обработчик команды /set_probability
@dp.message(Command("set_probability"))
async def cmd_set_probability(message: types.Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    data = load_data()
    if not data["keywords"]:
        await message.answer("⚠️ Список ключевых слов пуст. Сначала добавьте ключевые слова.")
        return
    
    await state.set_state(Form.select_keyword_for_probability)
    
    # Создаем клавиатуру в новом формате
    buttons = []
    for keyword in data["keywords"]:
        buttons.append([types.KeyboardButton(text=keyword)])
    buttons.append([types.KeyboardButton(text="Отмена")])
    
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("📝 Выберите ключевое слово, для которого нужно изменить вероятность реакции:",
                        reply_markup=keyboard)

# Обработчик выбора ключевого слова для изменения вероятности
@dp.message(Form.select_keyword_for_probability)
async def process_select_keyword_for_probability(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("❌ Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return
    
    keyword = message.text.lower().strip()
    data = load_data()
    
    if keyword in data["keywords"]:
        # Получаем текущую вероятность
        if isinstance(data["keywords"][keyword], dict):
            current_probability = data["keywords"][keyword].get("probability", 100)
        else:
            # Для обратной совместимости
            current_probability = 100
            
        await state.update_data(keyword=keyword)
        await state.set_state(Form.set_probability)
        await message.answer(f"📊 Текущая вероятность реакции для '{keyword}': {current_probability}%\n\n"
                            f"Введите новую вероятность (от 1 до 100):",
                            reply_markup=types.ReplyKeyboardRemove())
    else:
        await message.answer(f"⚠️ Ключевое слово '{keyword}' не найдено.",
                            reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

# Обработчик установки новой вероятности для ключевого слова
@dp.message(Form.set_probability)
async def process_set_probability(message: types.Message, state: FSMContext):
    try:
        new_probability = int(message.text.strip())
        if new_probability < 1 or new_probability > 100:
            await message.answer("⚠️ Вероятность должна быть от 1 до 100 процентов. Попробуйте снова:")
            return
        
        # Получаем ключевое слово из состояния
        user_data = await state.get_data()
        keyword = user_data["keyword"]
        
        data = load_data()
        
        # Проверяем формат данных и обновляем соответственно
        if isinstance(data["keywords"].get(keyword), dict):
            data["keywords"][keyword]["probability"] = new_probability
        else:
            # Преобразуем в новый формат
            old_reaction = data["keywords"].get(keyword, "")
            data["keywords"][keyword] = {
                "reaction": old_reaction,
                "probability": new_probability
            }
        
        save_data(data)
        
        await message.answer(f"✅ Вероятность реакции для ключевого слова '{keyword}' успешно изменена на: {new_probability}%")
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Ошибка: вероятность должна быть числом. Попробуйте снова:")

# Обработчик команды /set_default
@dp.message(Command("set_default"))
async def cmd_set_default_reaction(message: types.Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await state.set_state(Form.set_default_reaction)
    
    data = load_data()
    current_default = data.get("default_reaction", DEFAULT_REACTION)
    
    await message.answer(f"📝 Текущая реакция по умолчанию: {current_default}\n\n"
                        f"Введите новую реакцию по умолчанию:")

# Обработчик установки новой реакции по умолчанию
@dp.message(Form.set_default_reaction)
async def process_set_default_reaction(message: types.Message, state: FSMContext):
    new_default = message.text
    
    data = load_data()
    data["default_reaction"] = new_default
    save_data(data)
    
    await message.answer(f"✅ Реакция по умолчанию успешно изменена на: {new_default}")
    await state.clear()

# Обработчик команды /set_default_prob
@dp.message(Command("set_default_prob"))
async def cmd_set_default_probability(message: types.Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await state.set_state(Form.set_default_probability)
    
    data = load_data()
    current_default_prob = data.get("default_probability", 100)
    
    await message.answer(f"📊 Текущая вероятность реакции по умолчанию: {current_default_prob}%\n\n"
                        f"Введите новую вероятность по умолчанию (от 1 до 100):")

# Обработчик установки новой вероятности по умолчанию
@dp.message(Form.set_default_probability)
async def process_set_default_probability(message: types.Message, state: FSMContext):
    try:
        new_default_prob = int(message.text.strip())
        if new_default_prob < 1 or new_default_prob > 100:
            await message.answer("⚠️ Вероятность должна быть от 1 до 100 процентов. Попробуйте снова:")
            return
        
        data = load_data()
        data["default_probability"] = new_default_prob
        save_data(data)
        
        await message.answer(f"✅ Вероятность реакции по умолчанию успешно изменена на: {new_default_prob}%")
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Ошибка: вероятность должна быть числом. Попробуйте снова:")

# Обработчик команды /add_admin
@dp.message(Command("add_admin"))
async def cmd_add_admin(message: types.Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    await state.set_state(Form.add_admin)
    await message.answer("📝 Введите имя пользователя (username) без символа @, которого нужно сделать администратором:")

# Обработчик добавления нового администратора
@dp.message(Form.add_admin)
async def process_add_admin(message: types.Message, state: FSMContext):
    admin_username = message.text.strip()
    
    # Удаляем символ @ в начале, если он есть
    if admin_username.startswith('@'):
        admin_username = admin_username[1:]
    
    data = load_data()
    if admin_username in data["admins"]:
        await message.answer(f"⚠️ Пользователь @{admin_username} уже является администратором.")
    else:
        data["admins"].append(admin_username)
        save_data(data)
        await message.answer(f"✅ Пользователь @{admin_username} успешно добавлен как администратор.")
    
    await state.clear()

# Обработчик команды /reload_admins
@dp.message(Command("reload_admins"))
async def cmd_reload_admins(message: types.Message):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    try:
        admins_from_file = load_admins()
        if not admins_from_file:
            await message.answer("⚠️ Файл с администраторами пуст или не существует.")
            return
            
        await message.answer(f"📋 Загружено {len(admins_from_file)} администраторов из файла.")
    except Exception as e:
        await message.answer(f"⚠️ Ошибка при загрузке администраторов: {str(e)}")

# Обработчик команды /set_voice_reaction
@dp.message(Command("set_voice_reaction"))
async def cmd_set_voice_reaction(message: types.Message, state: FSMContext):
    if not is_admin(message):
        await message.answer("⛔ У вас нет прав администратора.")
        return
    
    data = load_data()
    if not data["keywords"]:
        await message.answer("⚠️ Список ключевых слов пуст. Сначала добавьте ключевые слова.")
        return
    
    await state.set_state(Form.select_keyword_for_voice)
    
    # Создаем клавиатуру в новом формате
    buttons = []
    for keyword in data["keywords"]:
        buttons.append([types.KeyboardButton(text=keyword)])
    buttons.append([types.KeyboardButton(text="Отмена")])
    
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)
    
    await message.answer("🎤 Выберите ключевое слово, для которого нужно установить голосовую реакцию:",
                        reply_markup=keyboard)

# Обработчик выбора ключевого слова для голосовой реакции
@dp.message(Form.select_keyword_for_voice)
async def process_select_keyword_for_voice(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("❌ Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return
    
    keyword = message.text.lower().strip()
    data = load_data()
    
    if keyword in data["keywords"]:
        await state.update_data(keyword=keyword)
        await state.set_state(Form.waiting_for_voice)
        
        # Проверяем, есть ли уже голосовая реакция для этого ключевого слова
        voice_file_id = data.get("voice_reactions", {}).get(keyword)
        
        if voice_file_id:
            await message.answer(f"🎤 Для ключевого слова '{keyword}' уже установлена голосовая реакция.\n\n"
                                f"Отправьте новое голосовое сообщение, чтобы заменить его, или нажмите 'Отмена':",
                                reply_markup=types.ReplyKeyboardMarkup(
                                    keyboard=[[types.KeyboardButton(text="Отмена")]],
                                    resize_keyboard=True,
                                    one_time_keyboard=True
                                ))
        else:
            await message.answer(f"🎤 Отправьте голосовое сообщение, которое будет использоваться как реакция на ключевое слово '{keyword}':",
                                reply_markup=types.ReplyKeyboardMarkup(
                                    keyboard=[[types.KeyboardButton(text="Отмена")]],
                                    resize_keyboard=True,
                                    one_time_keyboard=True
                                ))
    else:
        await message.answer(f"⚠️ Ключевое слово '{keyword}' не найдено.",
                            reply_markup=types.ReplyKeyboardRemove())
        await state.clear()

# Обработчик голосового сообщения для установки реакции
@dp.message(Form.waiting_for_voice)
async def process_voice_reaction(message: types.Message, state: FSMContext):
    if message.text == "Отмена":
        await message.answer("❌ Операция отменена.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        return
    
    # Проверяем, что это голосовое сообщение
    if not message.voice:
        await message.answer("⚠️ Пожалуйста, отправьте голосовое сообщение или нажмите 'Отмена'.")
        return
    
    # Получаем ключевое слово из состояния
    user_data = await state.get_data()
    keyword = user_data["keyword"]
    
    # Получаем file_id голосового сообщения
    voice_file_id = message.voice.file_id
    
    data = load_data()
    
    # Создаем словарь для голосовых реакций, если его еще нет
    if "voice_reactions" not in data:
        data["voice_reactions"] = {}
    
    # Сохраняем голосовую реакцию
    data["voice_reactions"][keyword] = voice_file_id
    save_data(data)
    
    await message.answer(f"✅ Голосовая реакция для ключевого слова '{keyword}' успешно установлена.",
                        reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

# Обработчик всех текстовых сообщений
@dp.message()
async def check_keywords(message: types.Message):
    # Проверяем, что это текстовое сообщение
    if not message.text:
        return
        
    data = load_data()
    message_text = message.text.lower()
    
    # Проверяем наличие ключевых слов в сообщении
    for keyword, info in data["keywords"].items():
        if keyword.lower() in message_text:
            # Определяем реакцию и вероятность
            if isinstance(info, dict):
                reaction = info.get("reaction", data.get("default_reaction", DEFAULT_REACTION))
                probability = info.get("probability", data.get("default_probability", 100))
            else:
                # Для обратной совместимости со старым форматом
                reaction = info
                probability = data.get("default_probability", 100)
            
            # Проверяем, должен ли бот отреагировать на основе вероятности
            if random.randint(1, 100) <= probability:
                # Проверяем, есть ли голосовая реакция для этого ключевого слова
                voice_file_id = data.get("voice_reactions", {}).get(keyword)
                
                if voice_file_id:
                    # Отправляем голосовое сообщение
                    try:
                        await message.answer_voice(voice_file_id)
                    except Exception as e:
                        logging.error(f"Ошибка при отправке голосового сообщения: {e}")
                        # Если не удалось отправить голосовое, отправляем текстовую реакцию
                        await message.reply(reaction)
                else:
                    # Отправляем текстовую реакцию
                    await message.reply(reaction)
            
            return  # Прерываем после первого найденного ключевого слова
    
    # Если нужно проверять все ключевые слова и реагировать на каждое,
    # можно убрать return и использовать список найденных слов

# Запуск бота
async def main():
    # Регистрируем все обработчики
    # (они уже зарегистрированы через декораторы)
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())