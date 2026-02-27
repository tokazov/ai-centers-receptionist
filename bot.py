#!/usr/bin/env python3
"""
AI Centers Receptionist Bot — Бот-воронка
Встречает пользователя → определяет потребность → направляет к нужному AI-агенту
@ai_centers_bot
"""

import os
import json
import logging
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
        "Я — AI-рецепционист. Помогу найти идеального AI-агента для вас.\n\n"
        "У нас <b>60+ специализированных AI-агентов</b>:\n"
        "🏥 Здоровье и психология\n"
        "💼 Бизнес и финансы\n"
        "📚 Образование\n"
        "✨ Астрология и духовное\n"
        "🎨 Лайфстайл\n"
        "💪 Саморазвитие\n\n"
        "Выберите категорию или просто <b>напишите, что вам нужно</b> — я подберу подходящего агента! 🤖"
    ),
    "en": (
        "👋 <b>Welcome to AI Centers!</b>\n\n"
        "I'm your AI receptionist. I'll help you find the perfect AI agent.\n\n"
        "We have <b>60+ specialized AI agents</b>:\n"
        "🏥 Health & Psychology\n"
        "💼 Business & Finance\n"
        "📚 Education\n"
        "✨ Astrology & Spiritual\n"
        "🎨 Lifestyle\n"
        "💪 Self-growth\n\n"
        "Choose a category or just <b>tell me what you need</b> — I'll find the right agent! 🤖"
    ),
    "ka": (
        "👋 <b>კეთილი იყოს თქვენი მობრძანება AI Centers-ში!</b>\n\n"
        "მე ვარ AI-რეცეფციონისტი. დაგეხმარებით იდეალური AI-აგენტის პოვნაში.\n\n"
        "ჩვენ გვაქვს <b>60+ სპეციალიზებული AI-აგენტი</b>.\n\n"
        "აირჩიეთ კატეგორია ან უბრალოდ <b>მომწერეთ რა გჭირდებათ</b>! 🤖"
    )
}

# === Keyboards ===
def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    buttons = []
    for cat_id, cat in CATEGORIES.items():
        name = t(cat["name"], lang)
        buttons.append([InlineKeyboardButton(text=f"{cat['emoji']} {name}", callback_data=f"cat:{cat_id}")])
    
    # Add special buttons
    custom_text = {"ru": "🛠 Создать своего AI-агента", "en": "🛠 Build your own AI agent", "ka": "🛠 შექმენი შენი AI-აგენტი"}
    all_text = {"ru": "🔍 Все агенты", "en": "🔍 All agents", "ka": "🔍 ყველა აგენტი"}
    site_text = {"ru": "🌐 Сайт", "en": "🌐 Website", "ka": "🌐 საიტი"}
    course_text = {"ru": "🎓 AI Курс", "en": "🎓 AI Course", "ka": "🎓 AI კურსი"}
    
    buttons.append([InlineKeyboardButton(text=t(custom_text, lang), callback_data="custom_bot")])
    buttons.append([
        InlineKeyboardButton(text=t(all_text, lang), callback_data="all_agents"),
        InlineKeyboardButton(text=t(course_text, lang), url="https://t.me/ai_course_center_bot")
    ])
    buttons.append([
        InlineKeyboardButton(text=t(site_text, lang), url="https://aicenters.co")
    ])
    
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
        "ka": "მომწერეთ რა გჭირდებათ და მე შესაფერის AI-აგენტს შევარჩევ!\n\nან აირჩიეთ კატეგორია:"
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
    welcome = t(WELCOME, lang)
    await callback.message.edit_text(welcome, reply_markup=main_menu_kb(lang))
    await callback.answer()


ADMIN_ID = 5309206282  # Тимур

CUSTOM_BOT_TEXT = {
    "ru": (
        "🛠 <b>Создание AI-агента под ключ</b>\n\n"
        "Мы создадим персонального AI-агента для вашего бизнеса:\n\n"
        "✅ Telegram / WhatsApp / Instagram бот\n"
        "✅ Обученный на ваших данных\n"
        "✅ Отвечает клиентам 24/7\n"
        "✅ Мультиязычный (до 7 языков)\n"
        "✅ Интеграция с CRM\n\n"
        "💰 <b>Стоимость:</b>\n"
        "• Базовый бот — $499\n"
        "• Продвинутый (с CRM, аналитикой) — $999\n"
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
        "🛠 <b>Custom AI Agent Development</b>\n\n"
        "We'll build a personalized AI agent for your business:\n\n"
        "✅ Telegram / WhatsApp / Instagram bot\n"
        "✅ Trained on your data\n"
        "✅ Answers clients 24/7\n"
        "✅ Multilingual (up to 7 languages)\n"
        "✅ CRM integration\n\n"
        "💰 <b>Pricing:</b>\n"
        "• Basic bot — $499\n"
        "• Advanced (CRM, analytics) — $999\n"
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
        "🛠 <b>AI-აგენტის შექმნა შეკვეთით</b>\n\n"
        "შევქმნით პერსონალურ AI-აგენტს თქვენი ბიზნესისთვის:\n\n"
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


@dp.callback_query(F.data == "custom_bot")
async def on_custom_bot(callback: CallbackQuery):
    lang = get_lang(callback.from_user)
    
    contact_text = {"ru": "💬 Оставить заявку", "en": "💬 Submit request", "ka": "💬 მოთხოვნის გაგზავნა"}
    examples_text = {"ru": "📱 Примеры наших ботов", "en": "📱 See our bots", "ka": "📱 ჩვენი ბოტები"}
    back_text = {"ru": "⬅️ Назад", "en": "⬅️ Back", "ka": "⬅️ უკან"}
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(contact_text, lang), callback_data="submit_request")],
        [InlineKeyboardButton(text=t(examples_text, lang), callback_data="back_main")],
        [InlineKeyboardButton(text=t(back_text, lang), callback_data="back_main")]
    ])
    
    await callback.message.edit_text(t(CUSTOM_BOT_TEXT, lang), reply_markup=kb)
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


@dp.message(F.text)
async def on_text(message: types.Message):
    """Smart agent recommendation or custom bot request"""
    lang = get_lang(message.from_user)
    
    # Check if user is submitting a custom bot request
    if message.from_user.id in pending_requests:
        pending_requests.discard(message.from_user.id)
        
        # Send to admin (Тимур)
        user = message.from_user
        admin_msg = (
            f"🔔 <b>Новая заявка на создание бота!</b>\n\n"
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
        logger.info(f"Custom bot request from {user.id} ({user.full_name}): {message.text[:100]}")
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
