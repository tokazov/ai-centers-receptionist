#!/usr/bin/env python3
"""
AI Centers Receptionist Bot — Бот-воронка
Встречает пользователя → определяет потребность → направляет к нужному AI-агенту
@ai_centers_bot
"""

import os
import json
import logging
import urllib.request
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "8760464642:AAGsLYjVv-xcfct7F4Q_UuwFiNX9Xi3Ta6g")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# === AI Agents catalog ===
CATEGORIES = {
    "health": {
        "emoji": "🏥",
        "name": {"ru": "Здоровье", "en": "Health", "ka": "ჯანმრთელობა"},
        "agents": [
            {"name": "Psychology Center", "bot": "@Psychology_Center_ai_bot", "desc": {"ru": "AI-психолог, 13 подходов терапии", "en": "AI psychologist, 13 therapy methods"}},
            {"name": "Metabolic Center", "bot": "@metabolic_center_ai_bot", "desc": {"ru": "Метаболическое здоровье, питание", "en": "Metabolic health, nutrition"}},
            {"name": "Fitness Center", "bot": "@fitness_center_ai_bot", "desc": {"ru": "Фитнес, тренировки, программы", "en": "Fitness, workouts, programs"}},
            {"name": "Women's Health", "bot": "@women_health_ai_bot", "desc": {"ru": "Женское здоровье", "en": "Women's health"}},
            {"name": "Symptoms Checker", "bot": "@symptoms_center_ai_bot", "desc": {"ru": "Проверка симптомов", "en": "Symptom checker"}},
            {"name": "Sleep Center", "bot": "@sleep_center_ai_bot", "desc": {"ru": "Здоровый сон", "en": "Healthy sleep"}},
            {"name": "Yoga Center", "bot": "@yoga_center_ai_bot", "desc": {"ru": "Йога и медитация", "en": "Yoga & meditation"}},
        ]
    },
    "business": {
        "emoji": "💼",
        "name": {"ru": "Бизнес", "en": "Business", "ka": "ბიზნესი"},
        "agents": [
            {"name": "Finance Center", "bot": "@finance_center_ai_bot", "desc": {"ru": "Финансы, инвестиции, бюджет", "en": "Finance, investments, budgeting"}},
            {"name": "Legal Center", "bot": "@legal_center_ai_bot", "desc": {"ru": "Юридические вопросы", "en": "Legal questions"}},
            {"name": "Marketing Center", "bot": "@marketing_center_ai_bot", "desc": {"ru": "Маркетинг и SMM", "en": "Marketing & SMM"}},
            {"name": "Sales Center", "bot": "@sales_center_ai_bot", "desc": {"ru": "Продажи и переговоры", "en": "Sales & negotiations"}},
            {"name": "Startup Center", "bot": "@startup_center_ai_bot", "desc": {"ru": "Запуск стартапа", "en": "Launch a startup"}},
            {"name": "Real Estate", "bot": "@real_estate_center_ai_bot", "desc": {"ru": "Недвижимость", "en": "Real estate"}},
        ]
    },
    "education": {
        "emoji": "📚",
        "name": {"ru": "Образование", "en": "Education", "ka": "განათლება"},
        "agents": [
            {"name": "AI Course", "bot": "@ai_course_center_bot", "desc": {"ru": "Курс 'Изучи AI за 3 дня'", "en": "Course 'Learn AI in 3 days'"}},
            {"name": "Education Center", "bot": "@education_center_ai_bot", "desc": {"ru": "Обучение и развитие", "en": "Learning & development"}},
            {"name": "English Center", "bot": "@english_center_ai_bot", "desc": {"ru": "Изучение английского", "en": "Learn English"}},
            {"name": "Math Center", "bot": "@math_center_ai_bot", "desc": {"ru": "Математика", "en": "Mathematics"}},
            {"name": "Code Center", "bot": "@code_center_ai_bot", "desc": {"ru": "Программирование", "en": "Programming"}},
            {"name": "Writing Center", "bot": "@writing_center_ai_bot", "desc": {"ru": "Написание текстов", "en": "Writing"}},
        ]
    },
    "spiritual": {
        "emoji": "✨",
        "name": {"ru": "Духовное", "en": "Spiritual", "ka": "სულიერი"},
        "agents": [
            {"name": "Soul Center", "bot": "@soul_center_ai_bot", "desc": {"ru": "Астрология + Human Design + нумерология", "en": "Astrology + Human Design + numerology"}},
            {"name": "Tarot Center", "bot": "@Tarot_Center_ai_bot", "desc": {"ru": "Таро расклады", "en": "Tarot readings"}},
            {"name": "Meditation", "bot": "@meditation_center_ai_bot", "desc": {"ru": "Медитации и осознанность", "en": "Meditation & mindfulness"}},
            {"name": "Dreams Center", "bot": "@dreams_center_ai_bot", "desc": {"ru": "Толкование снов", "en": "Dream interpretation"}},
            {"name": "Runes Center", "bot": "@runes_center_ai_bot", "desc": {"ru": "Руны", "en": "Runes"}},
        ]
    },
    "lifestyle": {
        "emoji": "🎨",
        "name": {"ru": "Лайфстайл", "en": "Lifestyle", "ka": "ცხოვრების წესი"},
        "agents": [
            {"name": "Cook Center", "bot": "@cook_center_ai_bot", "desc": {"ru": "Рецепты и кулинария", "en": "Recipes & cooking"}},
            {"name": "Travel Center", "bot": "@travel_center_ai_bot", "desc": {"ru": "Путешествия", "en": "Travel planning"}},
            {"name": "Style Center", "bot": "@style_center_ai_bot", "desc": {"ru": "Мода и стиль", "en": "Fashion & style"}},
            {"name": "Movie Center", "bot": "@movie_center_ai_bot", "desc": {"ru": "Фильмы и сериалы", "en": "Movies & TV shows"}},
            {"name": "Music Center", "bot": "@music_center_ai_bot", "desc": {"ru": "Музыка", "en": "Music"}},
            {"name": "Pet Center", "bot": "@pet_center_ai_bot", "desc": {"ru": "Уход за питомцами", "en": "Pet care"}},
        ]
    },
    "personal": {
        "emoji": "💪",
        "name": {"ru": "Саморазвитие", "en": "Self-growth", "ka": "თვითგანვითარება"},
        "agents": [
            {"name": "Motivation Center", "bot": "@motivation_center_ai_bot", "desc": {"ru": "Мотивация и цели", "en": "Motivation & goals"}},
            {"name": "Career Center", "bot": "@career_center_ai_bot", "desc": {"ru": "Карьера и резюме", "en": "Career & resume"}},
            {"name": "Relationship", "bot": "@relationship_center_ai_bot", "desc": {"ru": "Отношения и любовь", "en": "Relationships & love"}},
            {"name": "Self Care", "bot": "@self_care_center_ai_bot", "desc": {"ru": "Забота о себе", "en": "Self care"}},
            {"name": "Stress Center", "bot": "@stress_center_ai_bot", "desc": {"ru": "Управление стрессом", "en": "Stress management"}},
        ]
    }
}

# === User language detection ===
def get_lang(user: types.User) -> str:
    code = (user.language_code or "en").lower()
    if code.startswith("ru"):
        return "ru"
    elif code.startswith("ka"):
        return "ka"
    return "en"

def t(texts: dict, lang: str) -> str:
    return texts.get(lang, texts.get("en", texts.get("ru", "")))

# === Messages ===
WELCOME = {
    "ru": (
        "👋 <b>Добро пожаловать в AI Centers!</b>\n\n"
        "У нас два направления:\n\n"
        "🤖 <b>Готовые AI-агенты</b> — 60+ специалистов\n"
        "Психолог, юрист, финансист, астролог, фитнес-тренер и другие. "
        "Выбери нужного и начни общаться прямо сейчас.\n\n"
        "✨ <b>Живой AI-помощник</b> — создай своего!\n"
        "Опиши какой помощник тебе нужен — и он появится за 5 секунд. "
        "Для бизнеса, учёбы, творчества — любая задача.\n\n"
        "Что выберете? 👇"
    ),
    "en": (
        "👋 <b>Welcome to AI Centers!</b>\n\n"
        "We offer two directions:\n\n"
        "🤖 <b>Ready-made AI Agents</b> — 60+ specialists\n"
        "Psychologist, lawyer, finance, astrology, fitness and more. "
        "Pick one and start chatting now.\n\n"
        "✨ <b>Live AI Assistant</b> — create your own!\n"
        "Describe what assistant you need — it appears in 5 seconds. "
        "For business, study, creativity — any task.\n\n"
        "What will you choose? 👇"
    ),
    "ka": (
        "👋 <b>კეთილი იყოს თქვენი მობრძანება AI Centers-ში!</b>\n\n"
        "🤖 <b>მზა AI-აგენტები</b> — 60+ სპეციალისტი\n"
        "✨ <b>ცოცხალი AI-ასისტენტი</b> — შექმენი შენი!\n\n"
        "რას აირჩევთ? 👇"
    )
}

# === Keyboards ===
def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    # Two main sections
    create_text = {"ru": "✨ Создать живого AI-помощника", "en": "✨ Create live AI assistant", "ka": "✨ შექმენი ცოცხალი AI-ასისტენტი"}
    catalog_text = {"ru": "🤖 Каталог AI-агентов (60+)", "en": "🤖 AI Agents catalog (60+)", "ka": "🤖 AI-აგენტების კატალოგი (60+)"}
    custom_order_text = {"ru": "🛠 AI-помощник для бизнеса", "en": "🛠 AI assistant for business", "ka": "🛠 AI-ასისტენტი ბიზნესისთვის"}
    course_text = {"ru": "🎓 AI Курс", "en": "🎓 AI Course", "ka": "🎓 AI კურსი"}
    site_text = {"ru": "🌐 Сайт", "en": "🌐 Website", "ka": "🌐 საიტი"}
    
    buttons = [
        [InlineKeyboardButton(text=t(create_text, lang), callback_data="try_custom")],
        [InlineKeyboardButton(text=t(catalog_text, lang), callback_data="show_catalog")],
        [InlineKeyboardButton(text=t(custom_order_text, lang), callback_data="custom_bot")],
        [
            InlineKeyboardButton(text=t(course_text, lang), url="https://t.me/ai_course_center_bot"),
            InlineKeyboardButton(text=t(site_text, lang), url="https://aicenters.co")
        ],
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def category_kb(cat_id: str, lang: str) -> InlineKeyboardMarkup:
    cat = CATEGORIES[cat_id]
    buttons = []
    for agent in cat["agents"]:
        desc = t(agent["desc"], lang)
        buttons.append([InlineKeyboardButton(text=f"🤖 {agent['name']}", url=f"https://t.me/{agent['bot'].lstrip('@')}")])
    
    back_text = {"ru": "⬅️ Назад", "en": "⬅️ Back", "ka": "⬅️ უკან"}
    buttons.append([InlineKeyboardButton(text=t(back_text, lang), callback_data="back_main")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def all_agents_kb(lang: str) -> InlineKeyboardMarkup:
    """Compact list of top agents"""
    top_agents = [
        ("🧠", "Psychology", "@Psychology_Center_ai_bot"),
        ("✨", "Soul Center", "@soul_center_ai_bot"),
        ("💰", "Finance", "@finance_center_ai_bot"),
        ("⚖️", "Legal", "@legal_center_ai_bot"),
        ("🏋️", "Fitness", "@fitness_center_ai_bot"),
        ("🎓", "AI Course", "@ai_course_center_bot"),
        ("🍳", "Cook", "@cook_center_ai_bot"),
        ("✈️", "Travel", "@travel_center_ai_bot"),
        ("🔮", "Tarot", "@Tarot_Center_ai_bot"),
        ("💪", "Motivation", "@motivation_center_ai_bot"),
    ]
    buttons = []
    for emoji, name, bot_user in top_agents:
        buttons.append([InlineKeyboardButton(text=f"{emoji} {name}", url=f"https://t.me/{bot_user.lstrip('@')}")])
    
    back_text = {"ru": "⬅️ Назад", "en": "⬅️ Back", "ka": "⬅️ უკან"}
    more_text = {"ru": "🌐 Все на сайте", "en": "🌐 All on website", "ka": "🌐 ყველა საიტზე"}
    buttons.append([
        InlineKeyboardButton(text=t(back_text, lang), callback_data="back_main"),
        InlineKeyboardButton(text=t(more_text, lang), url="https://aicenters.co")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


# === Smart recommendation based on text ===
KEYWORDS = {
    "psychology": ["психолог", "тревог", "депресс", "стресс", "отношени", "одиноч", "панич", "самооценк", "therapy", "anxiety", "depression", "mental"],
    "fitness": ["фитнес", "тренировк", "спорт", "похуде", "мышц", "зал", "workout", "gym", "exercise", "weight"],
    "finance": ["финанс", "деньг", "инвестиц", "бюджет", "бизнес", "money", "invest", "budget", "finance"],
    "legal": ["юрист", "закон", "суд", "право", "договор", "lawyer", "legal", "law", "court"],
    "soul": ["астролог", "гороскоп", "human design", "нумеролог", "натальн", "astrology", "horoscope", "numerology"],
    "tarot": ["таро", "расклад", "гадан", "карт", "tarot", "cards", "divination"],
    "cook": ["рецепт", "готов", "еда", "кулинар", "блюд", "recipe", "cook", "food"],
    "travel": ["путешеств", "поездк", "отдых", "тур", "travel", "trip", "vacation"],
    "education": ["учи", "курс", "образован", "learn", "course", "study", "education"],
    "english": ["английск", "english", "англ", "language"],
    "career": ["карьер", "работ", "резюме", "career", "job", "resume"],
    "motivation": ["мотивац", "цел", "motivation", "goal", "продуктивн"],
    "metabolic": ["метаболи", "здоров", "питан", "диет", "metabol", "health", "nutrition", "diet"],
    "code": ["програм", "код", "python", "coding", "developer", "programming"],
    "relationship": ["любов", "парт", "свидан", "love", "dating", "relationship"],
    "startup": ["стартап", "запуск", "startup", "launch", "бизнес-план"],
    "sleep": ["сон", "бессонниц", "sleep", "insomnia"],
    "meditation": ["медитац", "осознанн", "meditation", "mindful"],
    "stress": ["стресс", "выгоран", "burnout", "stress"],
}

KEYWORD_TO_AGENT = {
    "psychology": ("Psychology Center", "@Psychology_Center_ai_bot"),
    "fitness": ("Fitness Center", "@fitness_center_ai_bot"),
    "finance": ("Finance Center", "@finance_center_ai_bot"),
    "legal": ("Legal Center", "@legal_center_ai_bot"),
    "soul": ("Soul Center", "@soul_center_ai_bot"),
    "tarot": ("Tarot Center", "@Tarot_Center_ai_bot"),
    "cook": ("Cook Center", "@cook_center_ai_bot"),
    "travel": ("Travel Center", "@travel_center_ai_bot"),
    "education": ("Education Center", "@education_center_ai_bot"),
    "english": ("English Center", "@english_center_ai_bot"),
    "career": ("Career Center", "@career_center_ai_bot"),
    "motivation": ("Motivation Center", "@motivation_center_ai_bot"),
    "metabolic": ("Metabolic Center", "@metabolic_center_ai_bot"),
    "code": ("Code Center", "@code_center_ai_bot"),
    "relationship": ("Relationship Center", "@relationship_center_ai_bot"),
    "startup": ("Startup Center", "@startup_center_ai_bot"),
    "sleep": ("Sleep Center", "@sleep_center_ai_bot"),
    "meditation": ("Meditation Center", "@meditation_center_ai_bot"),
    "stress": ("Stress Center", "@stress_center_ai_bot"),
}

def find_agent(text: str) -> tuple:
    """Find best matching agent based on user text"""
    text_lower = text.lower()
    scores = {}
    for agent_key, keywords in KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            scores[agent_key] = score
    
    if scores:
        best = max(scores, key=scores.get)
        return KEYWORD_TO_AGENT.get(best)
    return None


# === Handlers ===

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    lang = get_lang(message.from_user)
    welcome = t(WELCOME, lang)
    await message.answer(welcome, reply_markup=main_menu_kb(lang))
    logger.info(f"New user: {message.from_user.id} ({message.from_user.full_name}), lang={lang}")


@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    lang = get_lang(message.from_user)
    help_text = {
        "ru": "Напишите мне что вам нужно, и я подберу подходящего AI-агента!\n\nИли выберите категорию:",
        "en": "Tell me what you need and I'll find the right AI agent!\n\nOr choose a category:",
        "ka": "მომწერეთ რა გჭირდებათ და მე შესაფერის AI-ასისტენტს შევარჩევ!\n\nან აირჩიეთ კატეგორია:"
    }
    await message.answer(t(help_text, lang), reply_markup=main_menu_kb(lang))


@dp.message(Command("agents"))
async def cmd_agents(message: types.Message):
    lang = get_lang(message.from_user)
    await message.answer("🤖 <b>Топ AI-агенты:</b>", reply_markup=all_agents_kb(lang))


@dp.callback_query(F.data.startswith("cat:"))
async def on_category(callback: CallbackQuery):
    cat_id = callback.data.split(":")[1]
    lang = get_lang(callback.from_user)
    
    cat = CATEGORIES.get(cat_id)
    if not cat:
        await callback.answer("Category not found")
        return
    
    name = t(cat["name"], lang)
    header = {
        "ru": f"{cat['emoji']} <b>{name}</b>\n\nВыберите AI-агента:",
        "en": f"{cat['emoji']} <b>{name}</b>\n\nChoose an AI agent:",
        "ka": f"{cat['emoji']} <b>{name}</b>\n\nაირჩიეთ AI-აგენტი:"
    }
    
    # Build description
    text = t(header, lang) + "\n"
    for agent in cat["agents"]:
        desc = t(agent["desc"], lang)
        text += f"\n🤖 <b>{agent['name']}</b> — {desc}"
    
    await callback.message.edit_text(text, reply_markup=category_kb(cat_id, lang))
    await callback.answer()


@dp.callback_query(F.data == "back_main")
async def on_back(callback: CallbackQuery):
    lang = get_lang(callback.from_user)
    # Clear custom session if exists
    if callback.from_user.id in custom_sessions:
        del custom_sessions[callback.from_user.id]
    welcome = t(WELCOME, lang)
    await callback.message.edit_text(welcome, reply_markup=main_menu_kb(lang))
    await callback.answer()


ADMIN_ID = 5309206282  # Тимур
GEMINI_KEY = os.getenv("GEMINI_KEY", "AIzaSyDRJLp8JGpKid1pTJBRVgeumPdObveAXwY")
FREE_LIMIT = 20  # бесплатных сообщений

# === Custom AI assistant sessions ===
# user_id -> {"persona": str, "history": [], "count": int, "name": str}
custom_sessions = {}


def gemini_chat(persona: str, history: list, user_msg: str) -> str:
    """Call Gemini API with persona and chat history"""
    messages = [{"role": "user", "parts": [{"text": f"System instruction: {persona}\n\nВажно: отвечай в роли этого AI-помощника. Не выходи из роли. Используй HTML теги (<b>, <i>) для форматирования. Будь полезным и дружелюбным."}]}]
    messages.append({"role": "model", "parts": [{"text": "Понял, я буду отвечать строго в роли описанного AI-помощника."}]})
    
    for msg in history[-10:]:  # last 10 messages for context
        messages.append({"role": "user", "parts": [{"text": msg["user"]}]})
        messages.append({"role": "model", "parts": [{"text": msg["bot"]}]})
    
    messages.append({"role": "user", "parts": [{"text": user_msg}]})
    
    data = json.dumps({
        "contents": messages,
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.8}
    }).encode()
    
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "Извините, произошла ошибка. Попробуйте ещё раз."

CUSTOM_BOT_TEXT = {
    "ru": (
        "🛠 <b>Создание AI-помощника под ключ</b>\n\n"
        "Мы создадим персонального AI-помощника для вашего бизнеса:\n\n"
        "✅ Telegram / WhatsApp / Instagram бот\n"
        "✅ Обученный на ваших данных\n"
        "✅ Отвечает клиентам 24/7\n"
        "✅ Мультиязычный (до 7 языков)\n"
        "✅ Интеграция с CRM\n\n"
        "💰 <b>Стоимость:</b>\n"
        "• Базовый AI-помощник — $499\n"
        "• Продвинутый AI-помощник (CRM, аналитика) — $999\n"
        "• Подписка на обслуживание — от $49/мес\n\n"
        "📋 <b>Примеры:</b>\n"
        "• AI-продавец для интернет-магазина\n"
        "• AI-консультант для клиники\n"
        "• AI-ассистент для ресторана\n"
        "• AI-HR для найма сотрудников\n"
        "• AI-поддержка для SaaS\n\n"
        "Хотите обсудить проект? Нажмите кнопку ниже 👇"
    ),
    "en": (
        "🛠 <b>Custom AI Assistant Development</b>\n\n"
        "We'll build a personalized AI assistant for your business:\n\n"
        "✅ Telegram / WhatsApp / Instagram bot\n"
        "✅ Trained on your data\n"
        "✅ Answers clients 24/7\n"
        "✅ Multilingual (up to 7 languages)\n"
        "✅ CRM integration\n\n"
        "💰 <b>Pricing:</b>\n"
        "• Basic AI assistant — $499\n"
        "• Advanced AI assistant (CRM, analytics) — $999\n"
        "• Maintenance subscription — from $49/mo\n\n"
        "📋 <b>Examples:</b>\n"
        "• AI sales agent for e-commerce\n"
        "• AI consultant for clinics\n"
        "• AI assistant for restaurants\n"
        "• AI HR for hiring\n"
        "• AI support for SaaS\n\n"
        "Want to discuss your project? Click below 👇"
    ),
    "ka": (
        "🛠 <b>AI-ასისტენტის შექმნა შეკვეთით</b>\n\n"
        "შევქმნით პერსონალურ AI-ასისტენტს თქვენი ბიზნესისთვის:\n\n"
        "✅ Telegram / WhatsApp / Instagram ბოტი\n"
        "✅ თქვენს მონაცემებზე გაწვრთნილი\n"
        "✅ კლიენტებს პასუხობს 24/7\n"
        "✅ მრავალენოვანი (7 ენამდე)\n\n"
        "💰 ფასი: $499-დან\n\n"
        "გსურთ პროექტის განხილვა? დააჭირეთ ქვემოთ 👇"
    )
}

# Track users waiting to submit a request
pending_requests = set()
pending_custom_creation = set()


@dp.callback_query(F.data == "custom_bot")
async def on_custom_bot(callback: CallbackQuery):
    lang = get_lang(callback.from_user)
    
    try_text = {"ru": "🚀 Попробовать бесплатно", "en": "🚀 Try for free", "ka": "🚀 სცადეთ უფასოდ"}
    contact_text = {"ru": "💬 Оставить заявку", "en": "💬 Submit request", "ka": "💬 მოთხოვნის გაგზავნა"}
    back_text = {"ru": "⬅️ Назад", "en": "⬅️ Back", "ka": "⬅️ უკან"}
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(try_text, lang), callback_data="try_custom")],
        [InlineKeyboardButton(text=t(contact_text, lang), callback_data="submit_request")],
        [InlineKeyboardButton(text=t(back_text, lang), callback_data="back_main")]
    ])
    
    await callback.message.edit_text(t(CUSTOM_BOT_TEXT, lang), reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "try_custom")
async def on_try_custom(callback: CallbackQuery):
    lang = get_lang(callback.from_user)
    
    prompt = {
        "ru": (
            "🎨 <b>Создайте своего AI-помощника прямо сейчас!</b>\n\n"
            "Опишите, каким он должен быть:\n\n"
            "💡 <b>Примеры:</b>\n"
            "• <i>AI-консультант для стоматологии, отвечает на вопросы о ценах и записи</i>\n"
            "• <i>AI-помощник для ресторана, знает меню и принимает бронь</i>\n"
            "• <i>AI-тренер по продажам, помогает менеджерам закрывать сделки</i>\n"
            "• <i>AI-учитель английского для детей 7-12 лет</i>\n\n"
            "Напишите описание — и я создам его за секунды! ⚡\n"
            f"У вас будет <b>{FREE_LIMIT} бесплатных сообщений</b> для теста."
        ),
        "en": (
            "🎨 <b>Create your AI assistant right now!</b>\n\n"
            "Describe what it should be:\n\n"
            "💡 <b>Examples:</b>\n"
            "• <i>AI consultant for a dental clinic, answers pricing and booking questions</i>\n"
            "• <i>AI assistant for a restaurant, knows the menu and takes reservations</i>\n"
            "• <i>AI sales coach helping managers close deals</i>\n\n"
            "Write a description — I'll create it in seconds! ⚡\n"
            f"You'll get <b>{FREE_LIMIT} free messages</b> to test."
        ),
        "ka": (
            "🎨 <b>შექმენით თქვენი AI-ასისტენტი ახლავე!</b>\n\n"
            "აღწერეთ როგორი უნდა იყოს და მე შევქმნი წამებში! ⚡\n"
            f"თქვენ მიიღებთ <b>{FREE_LIMIT} უფასო შეტყობინებას</b> ტესტირებისთვის."
        )
    }
    
    pending_custom_creation.add(callback.from_user.id)
    await callback.message.edit_text(t(prompt, lang))
    await callback.answer()


@dp.callback_query(F.data == "submit_request")
async def on_submit_request(callback: CallbackQuery):
    lang = get_lang(callback.from_user)
    
    prompt = {
        "ru": (
            "📝 <b>Расскажите о вашем проекте:</b>\n\n"
            "Напишите в свободной форме:\n"
            "• Какой бизнес?\n"
            "• Что должен делать бот?\n"
            "• Для какой платформы? (Telegram, WhatsApp, Instagram)\n"
            "• Какие языки нужны?\n\n"
            "Просто напишите сообщение — мы свяжемся с вами! ✉️"
        ),
        "en": (
            "📝 <b>Tell us about your project:</b>\n\n"
            "Write in free form:\n"
            "• What business?\n"
            "• What should the bot do?\n"
            "• Which platform? (Telegram, WhatsApp, Instagram)\n"
            "• What languages?\n\n"
            "Just write a message — we'll get back to you! ✉️"
        ),
        "ka": (
            "📝 <b>მოგვიყევით თქვენი პროექტის შესახებ:</b>\n\n"
            "დაწერეთ თავისუფალი ფორმით და ჩვენ დაგიკავშირდებით! ✉️"
        )
    }
    
    pending_requests.add(callback.from_user.id)
    await callback.message.edit_text(t(prompt, lang))
    await callback.answer()


@dp.callback_query(F.data == "pay_subscribe")
async def on_pay_subscribe(callback: CallbackQuery):
    lang = get_lang(callback.from_user)
    text = {
        "ru": (
            "💎 <b>Оформление подписки</b>\n\n"
            "Выберите тариф:\n\n"
            "⭐ <b>Starter — $15/мес</b>\n"
            "1 AI-помощник, безлимит сообщений\n\n"
            "⭐⭐ <b>Pro — $49/мес</b>\n"
            "5 AI-помощников, приоритетная поддержка\n\n"
            "⭐⭐⭐ <b>Business — $149/мес</b>\n"
            "Все помощники + API доступ\n\n"
            "📧 Для оформления свяжитесь с нами или оплатите на сайте:"
        ),
        "en": (
            "💎 <b>Subscribe</b>\n\n"
            "Choose a plan:\n\n"
            "⭐ <b>Starter — $15/mo</b> — 1 AI assistant, unlimited\n"
            "⭐⭐ <b>Pro — $49/mo</b> — 5 AI assistants\n"
            "⭐⭐⭐ <b>Business — $149/mo</b> — All + API\n\n"
            "📧 Contact us or pay on the website:"
        ),
        "ka": (
            "💎 <b>გამოწერა</b>\n\n"
            "⭐ Starter — $15/თვე\n"
            "⭐⭐ Pro — $49/თვე\n"
            "⭐⭐⭐ Business — $149/თვე"
        )
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Оплатить на сайте", url="https://aicenters.co")],
        [InlineKeyboardButton(text="💬 Написать менеджеру", url="https://t.me/timurtokazov")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text(t(text, lang), reply_markup=kb)
    
    # Notify admin
    user = callback.from_user
    try:
        await bot.send_message(ADMIN_ID,
            f"💰 <b>Клиент хочет подписку!</b>\n\n"
            f"👤 {user.full_name}{(' (@' + user.username + ')') if user.username else ''}\n"
            f"🆔 {user.id}")
    except: pass
    await callback.answer()


@dp.callback_query(F.data == "pay_custom")
async def on_pay_custom(callback: CallbackQuery):
    lang = get_lang(callback.from_user)
    
    session = custom_sessions.get(callback.from_user.id, {})
    persona = session.get("persona", "не указано")
    
    text = {
        "ru": (
            f"🛠 <b>Заказ AI-помощника под ключ</b>\n\n"
            f"На основе вашего теста мы создадим полноценного AI-помощника:\n\n"
            f"📝 <b>Ваш запрос:</b> <i>{persona[:200]}</i>\n\n"
            f"<b>Что входит:</b>\n"
            f"✅ Отдельный Telegram бот с вашим именем\n"
            f"✅ Обучение на ваших данных (прайсы, FAQ, каталог)\n"
            f"✅ Мультиязычность (до 7 языков)\n"
            f"✅ Интеграция с CRM/WhatsApp\n"
            f"✅ Аналитика и статистика\n"
            f"✅ 30 дней бесплатной поддержки\n\n"
            f"💰 <b>Стоимость: от $499</b>\n"
            f"⏱ Срок: 3-7 дней\n\n"
            f"Напишите менеджеру для обсуждения деталей:"
        ),
        "en": (
            f"🛠 <b>Custom AI Assistant Order</b>\n\n"
            f"Based on your test, we'll build a full AI assistant:\n\n"
            f"📝 <b>Your request:</b> <i>{persona[:200]}</i>\n\n"
            f"💰 <b>Price: from $499</b>\n"
            f"⏱ Delivery: 3-7 days\n\n"
            f"Contact our manager to discuss details:"
        ),
        "ka": (
            f"🛠 <b>AI-ასისტენტის შეკვეთა</b>\n\n"
            f"💰 ფასი: $499-დან\n"
            f"⏱ ვადა: 3-7 დღე"
        )
    }
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Написать менеджеру", url="https://t.me/timurtokazov")],
        [InlineKeyboardButton(text="🌐 Сайт AI Centers", url="https://aicenters.co")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_main")]
    ])
    await callback.message.edit_text(t(text, lang), reply_markup=kb)
    
    # Notify admin
    user = callback.from_user
    try:
        await bot.send_message(ADMIN_ID,
            f"🔥🔥 <b>Клиент хочет AI-помощника под ключ!</b>\n\n"
            f"👤 {user.full_name}{(' (@' + user.username + ')') if user.username else ''}\n"
            f"🆔 {user.id}\n"
            f"📝 Запрос: {persona[:300]}")
    except: pass
    await callback.answer()


@dp.callback_query(F.data == "show_catalog")
async def on_show_catalog(callback: CallbackQuery):
    lang = get_lang(callback.from_user)
    
    text = {
        "ru": "🤖 <b>Каталог готовых AI-агентов</b>\n\nВыберите категорию:",
        "en": "🤖 <b>AI Agents Catalog</b>\n\nChoose a category:",
        "ka": "🤖 <b>AI-აგენტების კატალოგი</b>\n\nაირჩიეთ კატეგორია:"
    }
    
    buttons = []
    for cat_id, cat in CATEGORIES.items():
        name = t(cat["name"], lang)
        buttons.append([InlineKeyboardButton(text=f"{cat['emoji']} {name}", callback_data=f"cat:{cat_id}")])
    
    all_text = {"ru": "🔍 Топ-10 агентов", "en": "🔍 Top 10 agents", "ka": "🔍 ტოპ-10 აგენტი"}
    back_text = {"ru": "⬅️ Назад", "en": "⬅️ Back", "ka": "⬅️ უკან"}
    buttons.append([InlineKeyboardButton(text=t(all_text, lang), callback_data="all_agents")])
    buttons.append([InlineKeyboardButton(text=t(back_text, lang), callback_data="back_main")])
    
    await callback.message.edit_text(t(text, lang), reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@dp.callback_query(F.data == "all_agents")
async def on_all_agents(callback: CallbackQuery):
    lang = get_lang(callback.from_user)
    text = {
        "ru": "🔍 <b>Топ-10 популярных AI-агентов:</b>",
        "en": "🔍 <b>Top 10 popular AI agents:</b>",
        "ka": "🔍 <b>ტოპ-10 პოპულარული AI-აგენტი:</b>"
    }
    await callback.message.edit_text(t(text, lang), reply_markup=all_agents_kb(lang))
    await callback.answer()


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    """Reset custom assistant session"""
    uid = message.from_user.id
    if uid in custom_sessions:
        del custom_sessions[uid]
    lang = get_lang(message.from_user)
    reset_text = {"ru": "🔄 Сессия сброшена. Нажмите /start для начала.", "en": "🔄 Session reset. Press /start to begin.", "ka": "🔄 სესია გადატვირთულია. დააჭირეთ /start."}
    await message.answer(t(reset_text, lang))


@dp.message(F.text)
async def on_text(message: types.Message):
    """Smart agent recommendation, custom creation, or chat with custom assistant"""
    lang = get_lang(message.from_user)
    uid = message.from_user.id
    
    # === Creating a new custom assistant ===
    if uid in pending_custom_creation:
        pending_custom_creation.discard(uid)
        
        persona_desc = message.text
        custom_sessions[uid] = {
            "persona": persona_desc,
            "history": [],
            "count": 0,
            "name": "Ваш AI-помощник"
        }
        
        # Generate first greeting from the custom assistant
        greeting_prompt = f"Ты — AI-помощник. Вот твоя роль: {persona_desc}\n\nПоприветствуй пользователя коротко и предложи помощь. 2-3 предложения максимум."
        greeting = gemini_chat(persona_desc, [], "Привет!")
        custom_sessions[uid]["history"].append({"user": "Привет!", "bot": greeting})
        custom_sessions[uid]["count"] = 1
        
        created = {
            "ru": f"✅ <b>AI-помощник создан!</b>\n\n📝 Роль: <i>{persona_desc[:200]}</i>\n\n{'—' * 20}\n\n{greeting}\n\n{'—' * 20}\n<i>💬 Осталось {FREE_LIMIT - 1} бесплатных сообщений</i>",
            "en": f"✅ <b>AI assistant created!</b>\n\n📝 Role: <i>{persona_desc[:200]}</i>\n\n{'—' * 20}\n\n{greeting}\n\n{'—' * 20}\n<i>💬 {FREE_LIMIT - 1} free messages remaining</i>",
            "ka": f"✅ <b>AI-ასისტენტი შექმნილია!</b>\n\n📝 როლი: <i>{persona_desc[:200]}</i>\n\n{'—' * 20}\n\n{greeting}\n\n{'—' * 20}\n<i>💬 დარჩა {FREE_LIMIT - 1} უფასო შეტყობინება</i>"
        }
        
        reset_text = {"ru": "🔄 Сбросить помощника", "en": "🔄 Reset assistant", "ka": "🔄 გადატვირთვა"}
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(reset_text, lang), callback_data="back_main")]
        ])
        
        await message.answer(t(created, lang), reply_markup=kb)
        
        # Notify admin
        user = message.from_user
        try:
            await bot.send_message(ADMIN_ID, 
                f"🆕 <b>Новый AI-помощник создан!</b>\n\n"
                f"👤 {user.full_name}{(' (@' + user.username + ')') if user.username else ''}\n"
                f"🆔 {user.id}\n"
                f"📝 {persona_desc[:300]}")
        except: pass
        
        logger.info(f"Custom assistant created for {uid}: {persona_desc[:100]}")
        return
    
    # === Chatting with existing custom assistant ===
    if uid in custom_sessions:
        session = custom_sessions[uid]
        
        # Check limit — switch to sales mode
        if session["count"] >= FREE_LIMIT and not session.get("sales_mode"):
            session["sales_mode"] = True
            session["sales_history"] = []
            
            limit_text = {
                "ru": (
                    f"😊 <b>Отлично! Вы попробовали {FREE_LIMIT} сообщений.</b>\n\n"
                    f"Вижу, что ваш AI-помощник вам полезен! Я — менеджер AI Centers, "
                    f"помогу вам продолжить использование.\n\n"
                    f"У нас есть два варианта:\n\n"
                    f"💎 <b>Подписка — от $15/мес</b>\n"
                    f"Безлимитное общение с вашим AI-помощником прямо здесь\n\n"
                    f"🛠 <b>Свой отдельный AI-помощник — от $499</b>\n"
                    f"Отдельный бот для вашего бизнеса, с вашим брендом, "
                    f"обученный на ваших данных\n\n"
                    f"Какой вариант вам интереснее? Или задавайте любые вопросы — я отвечу! 😊"
                ),
                "en": (
                    f"😊 <b>Great! You've tried {FREE_LIMIT} messages.</b>\n\n"
                    f"I see your AI assistant is useful! I'm the AI Centers manager, "
                    f"I'll help you continue.\n\n"
                    f"We have two options:\n\n"
                    f"💎 <b>Subscription — from $15/mo</b>\n"
                    f"Unlimited chat with your AI assistant right here\n\n"
                    f"🛠 <b>Your own AI assistant — from $499</b>\n"
                    f"Dedicated bot for your business, branded, trained on your data\n\n"
                    f"Which option interests you? Or ask any questions! 😊"
                ),
                "ka": (
                    f"😊 <b>შესანიშნავი! თქვენ გამოსცადეთ {FREE_LIMIT} შეტყობინება.</b>\n\n"
                    f"💎 <b>გამოწერა — $15/თვე-დან</b>\n"
                    f"🛠 <b>საკუთარი AI-ასისტენტი — $499-დან</b>\n\n"
                    f"რომელი ვარიანტი გაინტერესებთ? 😊"
                )
            }
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 $15/мес — Подписка", callback_data="pay_subscribe")],
                [InlineKeyboardButton(text="🛠 $499 — Свой AI-помощник", callback_data="pay_custom")],
                [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_main")]
            ])
            
            await message.answer(t(limit_text, lang), reply_markup=kb)
            
            # Notify admin about hot lead
            user = message.from_user
            try:
                await bot.send_message(ADMIN_ID,
                    f"🔥 <b>Горячий лид! Исчерпал лимит!</b>\n\n"
                    f"👤 {user.full_name}{(' (@' + user.username + ')') if user.username else ''}\n"
                    f"🆔 {user.id}\n"
                    f"📝 Помощник: {session['persona'][:200]}\n"
                    f"💬 Сообщений: {session['count']}")
            except: pass
            return
        
        # === Sales mode — AI Sales Agent handles conversation ===
        if session.get("sales_mode"):
            sales_persona = (
                "Ты — менеджер по продажам AI Centers. Тёплый, дружелюбный, не навязчивый.\n"
                "Клиент уже попробовал AI-помощника бесплатно и ему понравилось.\n"
                f"Его помощник был: {session['persona'][:200]}\n\n"
                "ТВОЯ ЗАДАЧА:\n"
                "1. Ответить на вопросы клиента\n"
                "2. Мягко вести к оплате\n"
                "3. Подчеркнуть ценность (24/7, без зарплаты, мультиязычный)\n"
                "4. Предложить подходящий тариф\n\n"
                "ТАРИФЫ:\n"
                "• Starter $15/мес — 1 AI-помощник, безлимит сообщений\n"
                "• Pro $49/мес — 5 AI-помощников, приоритет\n"
                "• Business $149/мес — все помощники + API\n"
                "• Свой AI-помощник под ключ — $499-999 (отдельный бот, ваш бренд, обучен на ваших данных)\n\n"
                "ВОЗРАЖЕНИЯ:\n"
                "• 'Дорого' → Сравни с зарплатой сотрудника ($500-2000/мес). AI работает 24/7 за $15.\n"
                "• 'Мне надо подумать' → Конечно! Но бесплатный лимит уже исчерпан. Хотите я подарю ещё 5 сообщений?\n"
                "• 'А качество?' → Вы уже попробовали 20 сообщений и видели результат!\n"
                "• 'Есть ли гарантии?' → 7 дней гарантия возврата.\n\n"
                "Пиши коротко, дружелюбно. Используй HTML теги (<b>, <i>). Не будь роботом."
            )
            
            response = gemini_chat(sales_persona, session.get("sales_history", []), message.text)
            session.setdefault("sales_history", []).append({"user": message.text, "bot": response})
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Оформить подписку", callback_data="pay_subscribe")],
                [InlineKeyboardButton(text="🛠 Заказать своего помощника", callback_data="pay_custom")]
            ])
            
            await message.answer(response, reply_markup=kb)
            
            # Log sales conversation for admin
            logger.info(f"Sales chat {uid}: '{message.text[:50]}' → '{response[:50]}'")
            return
        
        # Chat with custom assistant
        response = gemini_chat(session["persona"], session["history"], message.text)
        session["history"].append({"user": message.text, "bot": response})
        session["count"] += 1
        remaining = FREE_LIMIT - session["count"]
        
        if remaining <= 5 and remaining > 0:
            response += f"\n\n<i>💬 Осталось {remaining} бесплатных сообщений</i>"
        
        await message.answer(response)
        return
    
    # === Check if user is submitting a custom bot request ===
    if uid in pending_requests:
        pending_requests.discard(message.from_user.id)
        
        # Send to admin (Тимур)
        user = message.from_user
        admin_msg = (
            f"🔔 <b>Новая заявка на AI-помощника!</b>\n\n"
            f"👤 {user.full_name}"
            f"{(' (@' + user.username + ')') if user.username else ''}\n"
            f"🆔 {user.id}\n"
            f"🌐 Язык: {user.language_code}\n\n"
            f"📝 <b>Запрос:</b>\n{message.text}"
        )
        try:
            await bot.send_message(ADMIN_ID, admin_msg)
        except Exception as e:
            logger.error(f"Failed to notify admin: {e}")
        
        # Confirm to user
        confirm = {
            "ru": "✅ <b>Заявка принята!</b>\n\nМы свяжемся с вами в ближайшее время. Спасибо! 🙏",
            "en": "✅ <b>Request received!</b>\n\nWe'll get back to you shortly. Thank you! 🙏",
            "ka": "✅ <b>მოთხოვნა მიღებულია!</b>\n\nმალე დაგიკავშირდებით. მადლობა! 🙏"
        }
        back_text = {"ru": "🏠 Главное меню", "en": "🏠 Main menu", "ka": "🏠 მთავარი მენიუ"}
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(back_text, lang), callback_data="back_main")]
        ])
        await message.answer(t(confirm, lang), reply_markup=kb)
        logger.info(f"AI assistant request from {user.id} ({user.full_name}): {message.text[:100]}")
        return
    
    result = find_agent(message.text)
    
    if result:
        name, bot_user = result
        recommend = {
            "ru": (
                f"💡 Я рекомендую <b>{name}</b>!\n\n"
                f"Этот AI-агент специализируется именно на вашем запросе.\n\n"
                f"👉 Нажмите чтобы начать:"
            ),
            "en": (
                f"💡 I recommend <b>{name}</b>!\n\n"
                f"This AI agent specializes exactly in what you need.\n\n"
                f"👉 Click to start:"
            ),
            "ka": (
                f"💡 გირჩევთ <b>{name}</b>-ს!\n\n"
                f"ეს AI-აგენტი სპეციალიზდება თქვენს მოთხოვნაზე.\n\n"
                f"👉 დააჭირეთ დასაწყებად:"
            )
        }
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"🤖 {name}", url=f"https://t.me/{bot_user.lstrip('@')}")],
            [InlineKeyboardButton(
                text={"ru": "🔍 Другие варианты", "en": "🔍 Other options", "ka": "🔍 სხვა ვარიანტები"}.get(lang, "🔍 Other"),
                callback_data="back_main"
            )]
        ])
        
        await message.answer(t(recommend, lang), reply_markup=kb)
    else:
        # No match — show categories
        no_match = {
            "ru": "🤔 Не уверен какой агент подойдёт лучше. Выберите категорию:",
            "en": "🤔 Not sure which agent fits best. Choose a category:",
            "ka": "🤔 არ ვარ დარწმუნებული რომელი აგენტი ჯობია. აირჩიეთ კატეგორია:"
        }
        await message.answer(t(no_match, lang), reply_markup=main_menu_kb(lang))
    
    logger.info(f"Text from {message.from_user.id}: '{message.text[:50]}' → {result[0] if result else 'no match'}")


async def main():
    logger.info("AI Centers Receptionist Bot starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
