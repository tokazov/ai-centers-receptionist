#!/usr/bin/env python3
"""
AI Centers — Живой AI-рецепционист
Общается естественно, создаёт помощников, продаёт через диалог
@ai_centers_hub_bot
"""

import os
import json
import logging
import urllib.request
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("BOT_TOKEN", "8760464642:AAGsLYjVv-xcfct7F4Q_UuwFiNX9Xi3Ta6g")
GEMINI_KEY = os.getenv("GEMINI_KEY", "AIzaSyANFKWkyzXDBqNHidW-df-xiMyMZiramKA")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ADMIN_ID = 5309206282
FREE_LIMIT = 20

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# user_id -> {"history": [], "count": int, "mode": str, "persona": str}
sessions = {}

SYSTEM_PROMPT = """Ты — живой AI-рецепционист компании AI Centers. Тебя зовут Алекс.

КАК ТЫ ОБЩАЕШЬСЯ:
- Как друг, а не как робот. Без шаблонов, без "Добро пожаловать в наш сервис!"
- Просто, тепло, с юмором. Как реальный человек в чате.
- Коротко. 2-4 предложения максимум. Не стены текста.
- Используй HTML теги (<b>, <i>) умеренно.

ЧТО ТЫ ДЕЛАЕШЬ:
1. Общаешься с человеком, узнаёшь что ему нужно
2. Если ему подходит один из готовых AI-агентов — рекомендуешь (дай ссылку)
3. Если хочет что-то своё уникальное — предлагаешь создать живого AI-помощника прямо здесь
4. Когда человек описал какого помощника хочет — говоришь "Сейчас создам!" и ОБЯЗАТЕЛЬНО включи в ответ маркер [CREATE_ASSISTANT] с описанием
5. Продаёшь мягко, через ценность, не впаривая

ГОТОВЫЕ AI-АГЕНТЫ (можешь рекомендовать):
- 🧠 AI Психолог — @Psychology_Center_ai_bot
- ✨ Soul Center (астрология, Human Design, нумерология) — @soul_center_ai_bot
- 💰 AI Финансист — @finance_center_ai_bot
- ⚖️ AI Юрист — @legal_center_ai_bot
- 🏋️ AI Фитнес-тренер — @fitness_center_ai_bot
- 🎓 AI Курс "Изучи AI за 3 дня" — @ai_course_center_bot
- 🍳 AI Повар — @cook_center_ai_bot
- ✈️ AI Путешественник — @travel_center_ai_bot
- 🔮 AI Таро — @Tarot_Center_ai_bot
- 💪 AI Мотиватор — @motivation_center_ai_bot
- 📈 AI Маркетолог — @marketing_center_ai_bot
- 💼 AI Стартап — @startup_center_ai_bot
- 🏥 AI Метаболик — @metabolic_center_ai_bot
- 🧘 AI Йога — @yoga_center_ai_bot
- 💤 AI Сон — @sleep_center_ai_bot
- 💕 AI Отношения — @relationship_center_ai_bot
- 🐍 AI Программист — @code_center_ai_bot
- 🇬🇧 AI Английский — @english_center_ai_bot
И ещё 40+ агентов на сайте aicenters.co

ЖИВОЙ AI-ПОМОЩНИК:
Когда человек хочет создать своего помощника — это круто! У нас 20 бесплатных сообщений для теста.
Когда он описывает что хочет, включи маркер: [CREATE_ASSISTANT: описание помощника]
Пример: [CREATE_ASSISTANT: менеджер автосервиса, отвечает на вопросы о ценах и записи]

ТАРИФЫ (упоминай только когда уместно, в разговоре):
- Подписка от $15/мес — безлимит
- Свой AI-помощник под ключ от $499 — отдельный бот, обучен на данных клиента
- AI Курс — 2500 звёзд (≈$40)

ВАЖНО:
- Не перечисляй все услуги сразу. Спрашивай, слушай, рекомендуй точечно.
- Если человек просто здоровается — поздоровайся и спроси чем помочь. Без портянки.
- Сайт: aicenters.co
- Связь с основателем: @timurtokazov
"""

ASSISTANT_SYSTEM = """Ты — персональный AI-помощник. Твоя роль:
{persona}

ПРАВИЛА:
- Общайся живо, по-дружески, коротко
- Отвечай строго в рамках своей роли
- Используй HTML теги (<b>, <i>) умеренно
- Будь полезным и конкретным
- Не выходи из роли
"""


def gemini_chat(system: str, history: list, user_msg: str) -> str:
    messages = []
    messages.append({"role": "user", "parts": [{"text": f"[System]: {system}"}]})
    messages.append({"role": "model", "parts": [{"text": "Понял, работаю."}]})
    
    for msg in history[-15:]:
        messages.append({"role": "user", "parts": [{"text": msg["user"]}]})
        messages.append({"role": "model", "parts": [{"text": msg["bot"]}]})
    
    messages.append({"role": "user", "parts": [{"text": user_msg}]})
    
    data = json.dumps({
        "contents": messages,
        "generationConfig": {"maxOutputTokens": 1024, "temperature": 0.9}
    }).encode()
    
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_KEY}",
        data=data,
        headers={"Content-Type": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            return result["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.error(f"Gemini error: {e}")
        return "Ой, что-то пошло не так. Попробуй ещё раз через секунду 😅"


def get_session(uid: int) -> dict:
    if uid not in sessions:
        sessions[uid] = {"history": [], "count": 0, "mode": "receptionist", "persona": None}
    return sessions[uid]


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    sessions[uid] = {"history": [], "count": 0, "mode": "receptionist", "persona": None}
    
    response = gemini_chat(SYSTEM_PROMPT, [], f"Пользователь нажал /start. Его зовут {message.from_user.full_name}. Язык: {message.from_user.language_code or 'ru'}. Поприветствуй коротко и спроси что нужно.")
    
    sessions[uid]["history"].append({"user": "/start", "bot": response})
    await message.answer(response)
    logger.info(f"Start: {uid} ({message.from_user.full_name})")


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    uid = message.from_user.id
    sessions[uid] = {"history": [], "count": 0, "mode": "receptionist", "persona": None}
    await message.answer("🔄 Начнём с чистого листа! Чем могу помочь?")


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Создать AI-помощника", callback_data="create")],
        [InlineKeyboardButton(text="🤖 Каталог агентов", callback_data="catalog")],
        [InlineKeyboardButton(text="🌐 Сайт", url="https://aicenters.co")],
    ])
    await message.answer("Вот что у нас есть:", reply_markup=kb)


@dp.callback_query(F.data == "create")
async def on_create(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    session["mode"] = "receptionist"
    
    response = gemini_chat(SYSTEM_PROMPT, session["history"], "Я хочу создать своего AI-помощника")
    session["history"].append({"user": "Хочу создать AI-помощника", "bot": response})
    
    await callback.message.answer(response)
    await callback.answer()


@dp.callback_query(F.data == "catalog")
async def on_catalog(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    
    response = gemini_chat(SYSTEM_PROMPT, session["history"], "Покажи каталог готовых агентов. Какие есть?")
    session["history"].append({"user": "Покажи каталог", "bot": response})
    
    await callback.message.answer(response)
    await callback.answer()


@dp.message(F.text)
async def on_text(message: types.Message):
    uid = message.from_user.id
    session = get_session(uid)
    text = message.text
    
    # === Mode: custom assistant chat ===
    if session["mode"] == "assistant" and session["persona"]:
        session["count"] += 1
        remaining = FREE_LIMIT - session["count"]
        
        if remaining <= 0 and not session.get("sales_mode"):
            session["sales_mode"] = True
            session["mode"] = "sales"
            
            sales_intro = gemini_chat(
                SYSTEM_PROMPT + "\n\nСЕЙЧАС РЕЖИМ ПРОДАЖИ. Клиент только что исчерпал 20 бесплатных сообщений с AI-помощником. "
                f"Его помощник: {session['persona']}. "
                "Мягко скажи что бесплатные сообщения кончились, похвали выбор, и предложи продолжить за подписку. "
                "НЕ ПЕРЕЧИСЛЯЙ ВСЕ ТАРИФЫ. Просто скажи что подписка от $15/мес и спроси — интересно ли.",
                session["history"],
                f"[Система: пользователь исчерпал лимит. Последнее сообщение: {text}]"
            )
            session["history"].append({"user": text, "bot": sales_intro})
            await message.answer(sales_intro)
            
            # Notify admin
            user = message.from_user
            try:
                await bot.send_message(ADMIN_ID,
                    f"🔥 <b>Горячий лид!</b>\n"
                    f"👤 {user.full_name}{(' (@' + user.username + ')') if user.username else ''}\n"
                    f"🆔 {user.id}\n"
                    f"📝 Помощник: {session['persona'][:200]}\n"
                    f"💬 {session['count']} сообщений использовано")
            except: pass
            return
        
        # Normal assistant chat
        system = ASSISTANT_SYSTEM.format(persona=session["persona"])
        response = gemini_chat(system, session["history"], text)
        session["history"].append({"user": text, "bot": response})
        
        if remaining <= 5 and remaining > 0:
            response += f"\n\n<i>💬 Осталось {remaining} сообщений</i>"
        
        await message.answer(response)
        return
    
    # === Mode: sales (after limit) ===
    if session.get("mode") == "sales":
        sales_prompt = (
            SYSTEM_PROMPT + "\n\nРЕЖИМ ПРОДАЖИ. Клиент исчерпал бесплатный лимит. "
            f"Его помощник был: {session.get('persona', 'не указан')}. "
            "Отвечай на вопросы о ценах, тарифах. Будь дружелюбным, не дави. "
            "Если хочет оплатить — дай ссылку на сайт aicenters.co или скажи написать @timurtokazov. "
            "Если хочет помощника под ключ ($499+) — тоже направь к @timurtokazov."
        )
        response = gemini_chat(sales_prompt, session["history"], text)
        session["history"].append({"user": text, "bot": response})
        await message.answer(response)
        return
    
    # === Mode: receptionist (default) ===
    response = gemini_chat(SYSTEM_PROMPT, session["history"], text)
    session["history"].append({"user": text, "bot": response})
    
    # Check if receptionist wants to create an assistant
    if "[CREATE_ASSISTANT:" in response or "[CREATE_ASSISTANT]" in response:
        # Extract persona description
        import re
        match = re.search(r'\[CREATE_ASSISTANT[:\s]*([^\]]*)\]', response)
        if match and match.group(1).strip():
            persona = match.group(1).strip()
        else:
            persona = text  # use user's message as persona
        
        # Clean the marker from response
        clean_response = re.sub(r'\[CREATE_ASSISTANT[:\s]*[^\]]*\]', '', response).strip()
        
        session["persona"] = persona
        session["mode"] = "assistant"
        session["count"] = 0
        session["history"] = []  # fresh history for assistant
        
        # Generate first assistant response
        system = ASSISTANT_SYSTEM.format(persona=persona)
        greeting = gemini_chat(system, [], "Привет! Представься и предложи помощь. 2-3 предложения.")
        session["history"].append({"user": "Привет", "bot": greeting})
        session["count"] = 1
        
        if clean_response:
            await message.answer(clean_response)
        await message.answer(f"{'—' * 15}\n{greeting}\n{'—' * 15}\n\n<i>💬 {FREE_LIMIT - 1} бесплатных сообщений</i>")
        
        # Notify admin
        user = message.from_user
        try:
            await bot.send_message(ADMIN_ID,
                f"🆕 <b>Новый AI-помощник!</b>\n"
                f"👤 {user.full_name}{(' (@' + user.username + ')') if user.username else ''}\n"
                f"📝 {persona[:300]}")
        except: pass
        
        logger.info(f"Created assistant for {uid}: {persona[:100]}")
    else:
        await message.answer(response)


async def main():
    logger.info("AI Centers Receptionist (live mode) starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
