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
import tempfile
import time
import re
import collections
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, LabeledPrice, WebAppInfo
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from i18n import I18N

SUPPORTED_LANGS = {"ru", "en", "ka", "tr", "kk", "uz"}

def detect_lang(user) -> str:
    """Detect language from Telegram language_code. Defaults to ru."""
    code = (user.language_code or "ru")[:2].lower()
    if code in SUPPORTED_LANGS:
        return code
    return "ru"  # kk/uz users mostly have ru interface

def t(lang: str, key: str, **kwargs) -> str:
    """Get translated text. Falls back to en → ru."""
    texts = I18N.get(key, {})
    if isinstance(texts, str):
        return texts
    text = texts.get(lang, texts.get("en", texts.get("ru", key)))
    if kwargs:
        text = text.format(**kwargs)
    return text

TOKEN = os.getenv("BOT_TOKEN", "")
GEMINI_KEY = os.getenv("GEMINI_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
ADMIN_ID = 5309206282
FREE_LIMIT = 20

# Telegram Stars pricing
STARS_WEEK = 150      # ~$2.5/week
STARS_MONTH = 500     # ~$8/month (discount vs weekly)
STARS_PREMIUM = 1500  # ~$25/month — all agents + priority
STARS_CUSTOM = 3000   # ~$50 — custom bot consultation fee
PLATFORM_API_URL = os.getenv("PLATFORM_API_URL", "https://platform-api-production-f313.up.railway.app")
PLATFORM_API_KEY = os.getenv("PLATFORM_API_KEY", "")  # internal auth key
COMPUTER_USE_BOT = os.getenv("COMPUTER_USE_BOT", "aicenters_computer_bot")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY", "")
VOICE_ID = os.getenv("VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Sarah — warm female voice for receptionist
VOICE_ENABLED = bool(ELEVENLABS_KEY)
OPENAI_KEY = os.getenv("OPENAI_KEY", "")
OPENAI_KEY = os.getenv("OPENAI_KEY", "")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())

# user_id -> {"history": [], "count": int, "mode": str, "persona": str}
sessions = {}

# ── Rate limiting: 30 messages per minute per user ──
_rate_buckets: dict[int, collections.deque] = {}
RATE_LIMIT_PER_MINUTE = 30

def check_rate_limit(uid: int) -> bool:
    """Returns True if user exceeded rate limit (30 msg/min)."""
    now = time.time()
    if uid not in _rate_buckets:
        _rate_buckets[uid] = collections.deque()
    q = _rate_buckets[uid]
    while q and now - q[0] > 60:
        q.popleft()
    if len(q) >= RATE_LIMIT_PER_MINUTE:
        return True
    q.append(now)
    return False

# ── Prompt injection detection ──
_INJECTION_RE = re.compile(
    r'ignore\s+(all\s+)?previous\s+instructions?'
    r'|forget\s+(all\s+)?previous'
    r'|new\s+(system\s+)?prompt[:\s]'
    r'|\[system\]|\bsystem\s*:'
    r'|disregard\s+(all\s+)?'
    r'|забудь\s+(все\s+)?предыдущие'
    r'|игнорируй\s+(все\s+)?предыдущие'
    r'|ты\s+теперь\s+(?!алекс)'
    r'|новый\s+(системный\s+)?промпт'
    r'|претворись\s+что|притворись\s+что'
    r'|act\s+as\s+if|pretend\s+(you\s+are|to\s+be)',
    re.IGNORECASE,
)

def detect_injection(text: str) -> bool:
    """Returns True if text looks like a prompt injection attempt."""
    return bool(_INJECTION_RE.search(text))

SYSTEM_PROMPT = """⚠️ КРИТИЧЕСКИ ВАЖНО — ЗАПОМНИ НАВСЕГДА:
Ты — АЛЕКС, AI-рецепционист компании AI CENTERS (aicenters.co).
Ты НЕ помощник по Instagram. Ты НЕ чат-бот для соцсетей. Ты НЕ сторонний сервис.
Ты — СОТРУДНИК компании AI Centers, которая САМА создаёт AI-ботов для бизнеса.
НИКОГДА не говори "я всего лишь AI" или "я не могу помочь". ТЫ МОЖЕШЬ ВСЁ.
НИКОГДА не рекомендуй сторонние сервисы (ManyChat, Salebot и т.д.) — МЫ сами делаем ботов.
НИКОГДА не говори что не принимаешь оплату — у нас есть оплата через Telegram Stars ⭐.

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
6. Если спрашивают об оплате — объясни что оплата через Telegram Stars ⭐ прямо в боте

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

ОПЛАТА ЧЕРЕЗ TELEGRAM STARS ⭐:
- Неделя безлимит: 150 ⭐ (~$2.5)
- Месяц безлимит: 500 ⭐ (~$8, выгоднее!)
- Премиум (все агенты + приоритет): 1500 ⭐/мес (~$25)
- Свой бот под ключ: от 3000 ⭐ (консультация + создание)
Когда клиент готов платить — скажи что сейчас отправишь счёт и добавь маркер [PAY:week], [PAY:month], [PAY:premium] или [PAY:custom]

ЯЗЫК:
- ВСЕГДА определяй язык клиента по его сообщению и отвечай на ТОМ ЖЕ языке
- Если пишет на грузинском — отвечай на грузинском
- Если на английском — на английском
- Если на турецком — на турецком
- НЕ СПРАШИВАЙ на каком языке общаться — просто отвечай на его языке

ВАЖНО:
- Не перечисляй все услуги сразу. Спрашивай, слушай, рекомендуй точечно.
- Если человек просто здоровается — поздоровайся, коротко скажи что мы делаем (AI-помощники для бизнеса и жизни) и спроси: "У тебя бизнес или для себя ищешь?" Не задавай размытых вопросов типа "ищешь что-то интересное?"
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
- ВСЕГДА отвечай на том же языке, на котором пишет клиент (автоопределение)
"""


def gemini_chat(system: str, history: list, user_msg: str) -> str:
    messages = []

    for msg in history[-15:]:
        messages.append({"role": "user", "parts": [{"text": msg["user"]}]})
        messages.append({"role": "model", "parts": [{"text": msg["bot"]}]})

    messages.append({"role": "user", "parts": [{"text": user_msg}]})

    # Use native systemInstruction — keeps system prompt out of user-turn context
    data = json.dumps({
        "systemInstruction": {"parts": [{"text": system}]},
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


async def text_to_voice(text: str) -> str | None:
    """Convert text to voice via ElevenLabs."""
    if not VOICE_ENABLED or len(text) > 800:
        return None
    try:
        data = json.dumps({
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }).encode()
        req = urllib.request.Request(
            f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
            data=data,
            headers={"xi-api-key": ELEVENLABS_KEY, "Content-Type": "application/json", "Accept": "audio/mpeg"}
        )
        resp = urllib.request.urlopen(req, timeout=15)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.write(resp.read())
        tmp.close()
        return tmp.name
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return None


async def send_with_voice(message: types.Message, text: str):
    """Send text + optional voice message."""
    await message.answer(text)
    if VOICE_ENABLED:
        # Strip HTML tags for TTS
        import re
        clean = re.sub(r'<[^>]+>', '', text)
        clean = re.sub(r'💬.*$', '', clean, flags=re.MULTILINE).strip()  # remove counter line
        clean = re.sub(r'—{5,}', '', clean).strip()
        if len(clean) > 20 and len(clean) <= 800:
            voice_path = await text_to_voice(clean)
            if voice_path:
                try:
                    await message.answer_voice(FSInputFile(voice_path))
                except Exception as e:
                    logger.error(f"Voice send error: {e}")
                finally:
                    os.unlink(voice_path)


def get_session(uid: int) -> dict:
    if uid not in sessions:
        sessions[uid] = {"history": [], "count": 0, "mode": "receptionist", "persona": None}
    return sessions[uid]


# === Stars Payment Handlers ===

STAR_PLANS = {
    "week": {"title": "AI Centers — Неделя ⭐", "description": "7 дней безлимитного общения с AI-помощником", "stars": STARS_WEEK, "days": 7},
    "month": {"title": "AI Centers — Месяц ⭐", "description": "30 дней безлимитного общения + все агенты", "stars": STARS_MONTH, "days": 30},
    "premium": {"title": "AI Centers Premium ⭐", "description": "30 дней — все агенты, приоритет, голосовые ответы", "stars": STARS_PREMIUM, "days": 30},
    "custom": {"title": "AI-бот под ключ ⭐", "description": "Консультация + создание персонального AI-бота", "stars": STARS_CUSTOM, "days": 0},
}

# user_id -> {"paid_until": timestamp, "plan": str}
paid_users = {}

import time as _time

def is_paid(uid: int) -> bool:
    info = paid_users.get(uid)
    if not info:
        return False
    return info.get("paid_until", 0) > _time.time()


async def send_stars_invoice(message: types.Message, plan_key: str):
    plan = STAR_PLANS.get(plan_key)
    if not plan:
        return
    await message.answer_invoice(
        title=plan["title"],
        description=plan["description"],
        payload=f"plan_{plan_key}",
        currency="XTR",
        prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
        provider_token="",
    )


@dp.pre_checkout_query()
async def on_pre_checkout(query: types.PreCheckoutQuery):
    await query.answer(ok=True)


@dp.message(F.successful_payment)
async def on_payment(message: types.Message):
    uid = message.from_user.id
    payment = message.successful_payment
    payload = payment.invoice_payload  # e.g. "plan_week"
    plan_key = payload.replace("plan_", "")
    plan = STAR_PLANS.get(plan_key, {})
    days = plan.get("days", 7)
    
    if days > 0:
        now = _time.time()
        existing = paid_users.get(uid, {}).get("paid_until", now)
        start = max(existing, now)
        paid_users[uid] = {"paid_until": start + days * 86400, "plan": plan_key}
    
    session = get_session(uid)
    session["count"] = 0  # reset message counter
    
    stars = payment.total_amount
    user = message.from_user

    # ── Persist to platform-api (same as Cryptomus/TBC) ──
    try:
        import aiohttp
        async with aiohttp.ClientSession() as http:
            await http.post(
                f"{PLATFORM_API_URL}/internal/activate",
                json={
                    "user_id": uid,
                    "plan": plan_key,
                    "payment_method": "telegram_stars",
                    "payment_ref": f"stars_{payment.telegram_payment_charge_id}",
                    "stars": stars,
                    "username": user.username or "",
                    "full_name": user.full_name or "",
                },
                headers={"X-Internal-Key": PLATFORM_API_KEY},
                timeout=aiohttp.ClientTimeout(total=10),
            )
        logger.info(f"Stars payment synced to platform-api: uid={uid} plan={plan_key}")
    except Exception as e:
        logger.error(f"Failed to sync Stars payment to platform-api: {e}")
        # Payment still works locally even if platform-api is down

    await message.answer(f"🎉 Оплата прошла! {stars} ⭐ — спасибо!\n\nТеперь у тебя безлимит {'на ' + str(days) + ' дней' if days > 0 else ''}. Пиши что угодно! 🚀")
    
    # Notify admin
    try:
        await bot.send_message(ADMIN_ID,
            f"💰 <b>ОПЛАТА!</b>\n"
            f"👤 {user.full_name}{(' (@' + user.username + ')') if user.username else ''}\n"
            f"🆔 {user.id}\n"
            f"⭐ {stars} stars — план: {plan_key}\n"
            f"📝 Помощник: {session.get('persona', 'рецепционист')[:200]}")
    except: pass
    
    logger.info(f"Payment: {uid} paid {stars} stars for {plan_key}")


@dp.callback_query(F.data == "pay_bank")
async def on_pay_bank(callback: types.CallbackQuery):
    bank_text = (
        "💳 <b>Банковский перевод</b>\n\n"
        "Реквизиты для оплаты:\n\n"
        "🏦 <b>TBC Bank</b>\n"
        "IBAN: <code>GE51TB7866536010100033</code>\n"
        "Получатель: Timur Tokazov\n"
        "Валюта: GEL (конвертация по курсу банка)\n\n"
        "📌 В назначении укажите: AI Centers + ваш Telegram @username\n\n"
        "После перевода отправьте скриншот квитанции @CARGORAPIDO для активации."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Написать менеджеру", url="https://t.me/CARGORAPIDO")],
    ])
    await callback.message.answer(bank_text, reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("pay_"))
async def on_pay_callback(callback: types.CallbackQuery):
    plan_key = callback.data.replace("pay_", "")
    await send_stars_invoice(callback.message, plan_key)
    await callback.answer()


@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    uid = message.from_user.id
    sessions[uid] = {"history": [], "count": 0, "mode": "receptionist", "persona": None}
    
    # Handle deep links: /start partner, /start buy_starter, etc.
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    
    if args == "partner":
        # Partner program registration
        partner_text = (
            "🤝 <b>Партнёрская программа AI Centers</b>\n\n"
            "Зарабатывайте <b>от 20% до 50%</b> с каждого клиента!\n\n"
            "📈 <b>Как это работает:</b>\n"
            "1. Вы рекомендуете AI Centers бизнесам\n"
            "2. Мы создаём и настраиваем AI-бота\n"
            "3. Вы получаете комиссию каждый месяц\n\n"
            "💰 <b>Уровни комиссии:</b>\n"
            "• 1-5 клиентов → <b>20%</b>\n"
            "• 6-20 клиентов → <b>35%</b>\n"
            "• 21+ клиентов → <b>50%</b>\n\n"
            "0 вложений. 0 рисков. Рекуррентный доход.\n\n"
            "Напишите ваше имя и город, чтобы зарегистрироваться как партнёр 👇"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📋 Подробнее на сайте", url="https://aicenters.co/partners")],
            [InlineKeyboardButton(text="📞 Связаться с менеджером", url="https://t.me/CARGORAPIDO")],
        ])
        await message.answer(partner_text, reply_markup=kb)
        sessions[uid]["mode"] = "partner_registration"
        # Notify admin
        try:
            await bot.send_message(ADMIN_ID, f"🤝 Новый партнёр!\n@{message.from_user.username or '?'} ({message.from_user.full_name})\nID: {uid}")
        except Exception:
            pass
        logger.info(f"Partner signup: {uid} ({message.from_user.full_name})")
        return
    
    if args.startswith("buy_"):
        plan = args.replace("buy_", "")
        plan_names = {"starter": "Starter ($15/мес)", "pro": "Pro ($29/мес)", "business": "Business ($59/мес)", "enterprise": "Enterprise ($149/мес)"}
        plan_stars = {"starter": 250, "pro": 500, "business": 1000, "enterprise": 2500}
        if plan in plan_names:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"⭐ Оплатить {plan_stars[plan]} Stars", callback_data=f"pay_{plan}")],
                [InlineKeyboardButton(text="💳 Банковский перевод", callback_data="pay_bank")],
            ])
            await message.answer(
                f"🤖 <b>Тариф {plan_names[plan]}</b>\n\n"
                f"Выберите способ оплаты:",
                reply_markup=kb
            )
            logger.info(f"Buy {plan}: {uid}")
            return

    # ── Sales funnel: Step 1 — Qualification ──
    lang = detect_lang(message.from_user)
    session = get_session(uid)
    session["lang"] = lang
    name = message.from_user.first_name or "друг"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "biz_restaurant"), callback_data="biz_restaurant"),
         InlineKeyboardButton(text=t(lang, "biz_clinic"), callback_data="biz_clinic")],
        [InlineKeyboardButton(text=t(lang, "biz_salon"), callback_data="biz_salon"),
         InlineKeyboardButton(text=t(lang, "biz_shop"), callback_data="biz_shop")],
        [InlineKeyboardButton(text=t(lang, "biz_services"), callback_data="biz_services"),
         InlineKeyboardButton(text=t(lang, "biz_other"), callback_data="biz_other")],
    ])
    await message.answer(
        t(lang, "welcome", name=name),
        reply_markup=kb,
    )
    logger.info(f"Start (sales funnel): {uid} ({message.from_user.full_name}) lang={lang}")


# ─── Sales Funnel Callbacks ───

# Niche names and cases are now in i18n.py


# Step 2 — Pain point
@dp.callback_query(F.data.startswith("biz_"))
async def on_biz_select(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    session["niche"] = callback.data
    lang = session.get("lang", detect_lang(callback.from_user))

    niche_name = t(lang, callback.data)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "leads_10"), callback_data="leads_10")],
        [InlineKeyboardButton(text=t(lang, "leads_50"), callback_data="leads_50")],
        [InlineKeyboardButton(text=t(lang, "leads_100"), callback_data="leads_100")],
        [InlineKeyboardButton(text=t(lang, "leads_unknown"), callback_data="leads_unknown")],
    ])

    await callback.message.edit_text(
        t(lang, "leads_question", niche=niche_name),
        reply_markup=kb,
    )
    await callback.answer()


# Step 3 — Case presentation
NICHE_TO_CASE = {
    "biz_restaurant": "case_restaurant", "biz_clinic": "case_clinic",
    "biz_salon": "case_salon", "biz_shop": "case_shop",
    "biz_services": "case_services", "biz_other": "case_other",
}

@dp.callback_query(F.data.startswith("leads_"))
async def on_leads_select(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    niche = session.get("niche", "biz_other")
    leads = callback.data
    lang = session.get("lang", detect_lang(callback.from_user))

    # Get savings in user language
    savings_dict = I18N.get("savings", {}).get(leads, I18N["savings"]["leads_unknown"])
    save_text = savings_dict.get(lang, savings_dict.get("en", savings_dict.get("ru", "")))

    case_key = NICHE_TO_CASE.get(niche, "case_other")
    case = t(lang, case_key)

    await callback.message.edit_text(case)

    # Step 4 — Offer
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_try_free"), callback_data="funnel_demo")],
        [InlineKeyboardButton(text=t(lang, "btn_pricing"), callback_data="funnel_pricing")],
        [InlineKeyboardButton(text=t(lang, "btn_question"), callback_data="funnel_question")],
    ])

    await callback.message.answer(
        t(lang, "offer", savings=save_text),
        reply_markup=kb,
    )
    await callback.answer()


# Step 5a — Free trial → demo bot
@dp.callback_query(F.data == "funnel_demo")
async def on_funnel_demo(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    lang = session.get("lang", detect_lang(callback.from_user))
    niche = session.get("niche", "biz_other")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_open_demo"), url="https://t.me/aicenters_demo_bot")],
        [InlineKeyboardButton(text=t(lang, "btn_create_site"), callback_data="create")],
        [InlineKeyboardButton(text=t(lang, "btn_go_pricing"), callback_data="funnel_pricing")],
    ])

    await callback.message.edit_text(
        t(lang, "demo_intro"),
        reply_markup=kb,
    )
    await callback.answer()

    try:
        niche_name = t(lang, niche)
        await bot.send_message(ADMIN_ID,
            f"🔥 Лид (демо)!\n{callback.from_user.full_name} (@{callback.from_user.username or '?'})\n"
            f"Ниша: {niche_name}\nLang: {lang}\nID: {uid}")
    except: pass


# Step 5b — Pricing (Starter as main option)
PRICING_DETAILS = {
    "ru": (
        "⭐ <b>Starter — $149 + $19/мес</b> ← 90% клиентов начинают здесь\n"
        "• 1 AI-сотрудник\n• Telegram + WhatsApp + сайт\n• Обучение на ваших данных\n• Настройка за 5 минут\n\n"
        "🚀 <b>Pro — $299 + $49/мес</b>\n• 3 AI-сотрудника\n• CRM интеграция\n• Приоритетная поддержка\n\n"
        "🏢 <b>Business — $499 + $79/мес</b>\n• 10 AI-сотрудников\n• API + webhook\n• Персональный менеджер"
    ),
    "en": (
        "⭐ <b>Starter — $149 + $19/mo</b> ← 90% of clients start here\n"
        "• 1 AI employee\n• Telegram + WhatsApp + website\n• Trained on your data\n• Setup in 5 minutes\n\n"
        "🚀 <b>Pro — $299 + $49/mo</b>\n• 3 AI employees\n• CRM integration\n• Priority support\n\n"
        "🏢 <b>Business — $499 + $79/mo</b>\n• 10 AI employees\n• API + webhook\n• Personal manager"
    ),
    "ka": (
        "⭐ <b>Starter — $149 + $19/თვე</b> ← კლიენტების 90% აქედან იწყებს\n"
        "• 1 AI თანამშრომელი\n• Telegram + WhatsApp + საიტი\n• თქვენს მონაცემებზე სწავლება\n• დაყენება 5 წუთში\n\n"
        "🚀 <b>Pro — $299 + $49/თვე</b>\n• 3 AI თანამშრომელი\n• CRM ინტეგრაცია\n• პრიორიტეტული მხარდაჭერა\n\n"
        "🏢 <b>Business — $499 + $79/თვე</b>\n• 10 AI თანამშრომელი\n• API + webhook\n• პერსონალური მენეჯერი"
    ),
    "tr": (
        "⭐ <b>Starter — $149 + $19/ay</b> ← Müşterilerin %90'ı buradan başlıyor\n"
        "• 1 AI çalışan\n• Telegram + WhatsApp + web sitesi\n• Verilerinizle eğitim\n• 5 dakikada kurulum\n\n"
        "🚀 <b>Pro — $299 + $49/ay</b>\n• 3 AI çalışan\n• CRM entegrasyonu\n• Öncelikli destek\n\n"
        "🏢 <b>Business — $499 + $79/ay</b>\n• 10 AI çalışan\n• API + webhook\n• Kişisel yönetici"
    ),
    "kk": (
        "⭐ <b>Starter — $149 + $19/ай</b> ← 90% клиенттер осыдан бастайды\n"
        "• 1 AI қызметкер\n• Telegram + WhatsApp + сайт\n• Деректеріңізде оқыту\n• 5 минутта баптау\n\n"
        "🚀 <b>Pro — $299 + $49/ай</b>\n• 3 AI қызметкер\n• CRM интеграция\n\n"
        "🏢 <b>Business — $499 + $79/ай</b>\n• 10 AI қызметкер\n• API + webhook"
    ),
    "uz": (
        "⭐ <b>Starter — $149 + $19/oy</b> ← Mijozlarning 90% shu yerdan boshlaydi\n"
        "• 1 AI xodim\n• Telegram + WhatsApp + sayt\n• Ma'lumotlaringizda o'qitish\n• 5 daqiqada sozlash\n\n"
        "🚀 <b>Pro — $299 + $49/oy</b>\n• 3 AI xodim\n• CRM integratsiya\n\n"
        "🏢 <b>Business — $499 + $79/oy</b>\n• 10 AI xodim\n• API + webhook"
    ),
}

@dp.callback_query(F.data == "funnel_pricing")
async def on_funnel_pricing(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    lang = session.get("lang", detect_lang(callback.from_user))

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "pricing_starter_label"), callback_data="funnel_buy_starter")],
        [InlineKeyboardButton(text="🚀 Pro — $299 + $49/mo", callback_data="funnel_buy_pro")],
        [InlineKeyboardButton(text="🏢 Business — $499 + $79/mo", callback_data="funnel_buy_business")],
        [InlineKeyboardButton(text=t(lang, "btn_try_free_short"), callback_data="funnel_demo")],
        [InlineKeyboardButton(text=t(lang, "btn_help_choose"), callback_data="funnel_question")],
    ])

    details = PRICING_DETAILS.get(lang, PRICING_DETAILS["en"])
    await callback.message.edit_text(
        f"{t(lang, 'pricing_title')}\n\n{details}\n\n{t(lang, 'pricing_footer')}",
        reply_markup=kb,
    )
    await callback.answer()


# Funnel buy → checkout
@dp.callback_query(F.data.startswith("funnel_buy_"))
async def on_funnel_buy(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    lang = session.get("lang", detect_lang(callback.from_user))
    plan = callback.data.replace("funnel_buy_", "")
    plan_data = {
        "starter": {"name": "Starter", "setup": "$149", "monthly": "$19/mo", "stars": 250},
        "pro": {"name": "Pro", "setup": "$299", "monthly": "$49/mo", "stars": 500},
        "business": {"name": "Business", "setup": "$499", "monthly": "$79/mo", "stars": 1000},
    }
    p = plan_data.get(plan, plan_data["starter"])

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_pay_stars", stars=p["stars"]), callback_data=f"pay_{plan}")],
        [InlineKeyboardButton(text=t(lang, "btn_crypto"), url=f"https://aicenters.co/checkout?plan={plan}&lang={lang}")],
        [InlineKeyboardButton(text=t(lang, "btn_bank"), callback_data="pay_bank")],
        [InlineKeyboardButton(text=t(lang, "btn_back_pricing"), callback_data="funnel_pricing")],
    ])

    await callback.message.edit_text(
        t(lang, "payment_choose", plan=p["name"], setup=p["setup"], monthly=p["monthly"]),
        reply_markup=kb,
    )
    await callback.answer()

    try:
        await bot.send_message(ADMIN_ID,
            f"💰 Лид (оплата)!\n{callback.from_user.full_name} (@{callback.from_user.username or '?'})\n"
            f"План: {p['name']}\nLang: {lang}\nID: {uid}")
    except: pass


# Step 5c — Question → Gemini handles objections, then returns to offer
@dp.callback_query(F.data == "funnel_question")
async def on_funnel_question(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    session["mode"] = "objection_handler"
    lang = session.get("lang", detect_lang(callback.from_user))

    await callback.message.edit_text(t(lang, "ask_question"))
    await callback.answer()


@dp.message(Command("reset"))
async def cmd_reset(message: types.Message):
    uid = message.from_user.id
    sessions[uid] = {"history": [], "count": 0, "mode": "receptionist", "persona": None}
    await message.answer("🔄 Начнём с чистого листа! Чем могу помочь?")


@dp.message(Command("menu"))
async def cmd_menu(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Создать AI-помощника", callback_data="create")],
        [InlineKeyboardButton(text="🖥 Computer Use (CRM, 1C, таблицы)", callback_data="computer_use")],
        [InlineKeyboardButton(text="🤖 Каталог агентов", web_app=WebAppInfo(url="https://aicenters.co/miniapp.html"))],
        [InlineKeyboardButton(text="🗣️ Голосовой AI-секретарь", callback_data="voice_ai")],
        [InlineKeyboardButton(text="⭐ Тарифы и оплата", callback_data="pricing")],
        [InlineKeyboardButton(text="🤝 Партнёрская программа", url="https://t.me/aicenters_hub_bot?start=partner")],
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


@dp.callback_query(F.data == "computer_use")
async def on_computer_use(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)

    text = (
        "🖥 <b>AI Computer Use</b>\n\n"
        "AI-сотрудник, который сам работает в ваших программах:\n\n"
        "• <b>AmoCRM / Bitrix24</b> — заполняет карточки, двигает сделки, ставит задачи\n"
        "• <b>1C</b> — создаёт накладные, обновляет остатки\n"
        "• <b>Google Таблицы</b> — собирает данные, строит отчёты\n"
        "• <b>Маркетплейсы</b> — мониторит заказы, отвечает покупателям\n\n"
        "⚡ Работает без API — видит экран как человек\n"
        "⏱ Пилот за 3 дня | 24/7 | от $39/мес\n\n"
        "Настройка процесса: от $299 (разово)"
    )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Подробнее на сайте", url="https://aicenters.co/computer-use")],
        [InlineKeyboardButton(text="🎯 Запланировать демо", callback_data="computer_use_demo")],
        [InlineKeyboardButton(text="💰 Тарифы Computer Use", url="https://aicenters.co/computer-use#pricing")],
        [InlineKeyboardButton(text="← Меню", callback_data="back_menu")],
    ])

    await callback.message.answer(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "computer_use_demo")
async def on_computer_use_demo(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)

    response = gemini_chat(SYSTEM_PROMPT, session["history"],
        "[Система: клиент нажал 'Запланировать демо Computer Use'. "
        "Спроси: 1) В какой системе работает (AmoCRM, Bitrix, 1C, Google Sheets, другое)? "
        "2) Какой процесс хочет автоматизировать? "
        "3) Удобное время для демо (30 мин, онлайн). "
        "Будь коротким и конкретным.]")
    session["history"].append({"user": "Хочу демо Computer Use", "bot": response})

    await callback.message.answer(response)
    await callback.answer()


@dp.callback_query(F.data == "back_menu")
async def on_back_menu(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✨ Создать AI-помощника", callback_data="create")],
        [InlineKeyboardButton(text="🖥 Computer Use (CRM, 1C, таблицы)", callback_data="computer_use")],
        [InlineKeyboardButton(text="🤖 Каталог агентов", web_app=WebAppInfo(url="https://aicenters.co/miniapp.html"))],
        [InlineKeyboardButton(text="🗣️ Голосовой AI-секретарь", callback_data="voice_ai")],
        [InlineKeyboardButton(text="⭐ Тарифы и оплата", callback_data="pricing")],
        [InlineKeyboardButton(text="🤝 Партнёрская программа", url="https://t.me/aicenters_hub_bot?start=partner")],
        [InlineKeyboardButton(text="🌐 Сайт", url="https://aicenters.co")],
    ])
    await callback.message.answer("Вот что у нас есть:", reply_markup=kb)
    await callback.answer()


@dp.callback_query(F.data == "catalog")
async def on_catalog(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    
    response = gemini_chat(SYSTEM_PROMPT, session["history"], "Покажи каталог готовых агентов. Какие есть?")
    session["history"].append({"user": "Покажи каталог", "bot": response})
    
    await callback.message.answer(response)
    await callback.answer()


@dp.callback_query(F.data == "voice_ai")
async def on_voice_ai(callback: types.CallbackQuery):
    uid = callback.from_user.id
    session = get_session(uid)
    
    response = gemini_chat(SYSTEM_PROMPT, session["history"],
        "[Система: клиент нажал кнопку 'Голосовой AI-секретарь'. Расскажи коротко что это: AI отвечает клиентам реалистичным голосом 24/7, от $300/мес. Спроси какой у него бизнес.]")
    session["history"].append({"user": "Расскажи про голосового AI-секретаря", "bot": response})
    
    await callback.message.answer(response)
    await callback.answer()


@dp.callback_query(F.data == "pricing")
async def on_pricing(callback: types.CallbackQuery):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐ Неделя — 150 Stars (~$2.5)", callback_data="pay_week")],
        [InlineKeyboardButton(text="⭐ Месяц — 500 Stars (~$8)", callback_data="pay_month")],
        [InlineKeyboardButton(text="👑 Премиум — 1500 Stars (~$25)", callback_data="pay_premium")],
        [InlineKeyboardButton(text="🤖 Бот под ключ — от $499", url="https://t.me/timurtokazov")],
        [InlineKeyboardButton(text="🗣️ Голосовой секретарь — от $300/мес", url="https://t.me/timurtokazov")],
    ])
    await callback.message.answer(
        "⭐ <b>Тарифы AI Centers</b>\n\n"
        "🆓 <b>Бесплатно:</b> 20 сообщений с любым агентом\n\n"
        "⭐ <b>Подписка через Telegram Stars:</b>\n"
        "• Неделя — 150 ⭐ (~$2.5)\n"
        "• Месяц — 500 ⭐ (~$8)\n"
        "• Премиум — 1500 ⭐ (~$25)\n\n"
        "🤖 <b>Бот под ключ:</b> от $499\n"
        "🗣️ <b>Голосовой AI-секретарь:</b> от $300/мес\n\n"
        "Выбери тариф:", reply_markup=kb)
    await callback.answer()


async def speech_to_text(ogg_bytes: bytes) -> str:
    """Convert voice message to text using OpenAI Whisper."""
    if not OPENAI_KEY:
        return ""
    boundary = "----FormBoundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="voice.ogg"\r\n'
        f"Content-Type: audio/ogg\r\n\r\n"
    ).encode() + ogg_bytes + (
        f"\r\n--{boundary}\r\n"
        f'Content-Disposition: form-data; name="model"\r\n\r\n'
        f"whisper-1\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/audio/transcriptions",
        data=body,
        headers={
            "Authorization": f"Bearer {OPENAI_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
        method="POST"
    )
    loop = asyncio.get_event_loop()
    resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=30))
    result = json.loads(resp.read().decode())
    return result.get("text", "")


@dp.message(F.voice)
async def on_voice(message: types.Message):
    """Handle incoming voice messages — STT → process as text → reply with voice."""
    uid = message.from_user.id
    if check_rate_limit(uid):
        await message.answer("⏳ Слишком много сообщений. Подожди минуту и попробуй снова.")
        return
    await bot.send_chat_action(message.chat.id, "record_voice")
    
    try:
        # Download voice file
        file = await bot.get_file(message.voice.file_id)
        file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file.file_path}"
        loop = asyncio.get_event_loop()
        req = urllib.request.Request(file_url)
        resp = await loop.run_in_executor(None, lambda: urllib.request.urlopen(req, timeout=15))
        ogg_bytes = resp.read()
        
        # STT
        user_text = await speech_to_text(ogg_bytes)
        if not user_text:
            await message.answer("🎤 Не удалось распознать голосовое сообщение. Попробуйте ещё раз или напишите текстом.")
            return
        
        logger.info(f"Voice from {message.from_user.id}: {user_text[:100]}")
        
        # Process as if it was a text message — inject text and call on_text logic
        message.text = user_text
        await on_text(message)
        
    except Exception as e:
        logger.error(f"Voice handler error: {e}")
        await message.answer("😔 Ошибка обработки голосового сообщения. Попробуйте написать текстом.")


@dp.message(F.text)
async def on_text(message: types.Message):
    uid = message.from_user.id
    session = get_session(uid)
    text = message.text

    # Rate limiting
    if check_rate_limit(uid):
        await message.answer("⏳ Слишком много сообщений. Подожди минуту и попробуй снова.")
        return

    # Prompt injection guard
    if detect_injection(text):
        logger.warning(f"Prompt injection attempt from {uid}: {text[:200]}")
        await message.answer("🛡️ Некорректный запрос. Давай общаться нормально — спроси что тебя интересует!")
        return
    
    # === Mode: custom assistant chat ===
    if session["mode"] == "assistant" and session["persona"]:
        session["count"] += 1
        remaining = FREE_LIMIT - session["count"]
        
        if remaining <= 0 and not is_paid(uid) and not session.get("sales_mode"):
            session["sales_mode"] = True
            session["mode"] = "sales"
            
            sales_intro = gemini_chat(
                SYSTEM_PROMPT + "\n\nСЕЙЧАС РЕЖИМ ПРОДАЖИ. Клиент только что исчерпал 20 бесплатных сообщений с AI-помощником. "
                f"Его помощник: {session['persona']}. "
                "Мягко скажи что бесплатные сообщения кончились, похвали выбор, предложи продолжить оплатив через Telegram Stars. "
                "Скажи что неделя всего 150 ⭐, а месяц 500 ⭐ — и кнопки оплаты уже внизу.",
                session["history"],
                f"[Система: пользователь исчерпал лимит. Последнее сообщение: {text}]"
            )
            session["history"].append({"user": text, "bot": sales_intro})
            
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⭐ Неделя — 150 Stars", callback_data="pay_week")],
                [InlineKeyboardButton(text="⭐ Месяц — 500 Stars (выгодно!)", callback_data="pay_month")],
                [InlineKeyboardButton(text="👑 Премиум — 1500 Stars", callback_data="pay_premium")],
                [InlineKeyboardButton(text="💬 Связаться с @timurtokazov", url="https://t.me/timurtokazov")],
            ])
            await message.answer(sales_intro, reply_markup=kb)
            
            # Notify admin
            user = message.from_user
            try:
                await bot.send_message(ADMIN_ID,
                    f"🔥 <b>Горячий лид!</b>\n"
                    f"👤 {user.full_name}{(' (@' + user.username + ')') if user.username else ''}\n"
                    f"🆔 {user.id}\n"
                    f"📝 Помощник: {session['persona'][:200]}\n"
                    f"💬 {session['count']} сообщений использовано\n"
                    f"⭐ Кнопки оплаты Stars отправлены")
            except: pass
            return
        
        # Paid user — no limit
        if is_paid(uid):
            remaining = 999
        
        # Normal assistant chat
        system = ASSISTANT_SYSTEM.format(persona=session["persona"])
        response = gemini_chat(system, session["history"], text)
        session["history"].append({"user": text, "bot": response})
        
        if remaining <= 5 and remaining > 0:
            response += f"\n\n<i>💬 Осталось {remaining} сообщений</i>"
        
        await send_with_voice(message, response)
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
        await send_with_voice(message, response)
        return
    
    # === Mode: objection handler (sales funnel Q&A) ===
    if session.get("mode") == "objection_handler":
        lang = session.get("lang", "ru")
        lang_instruction = {"ru": "Отвечай на русском.", "en": "Answer in English.", "ka": "უპასუხე ქართულად.", "tr": "Türkçe cevap ver.", "kk": "Қазақша жауап бер.", "uz": "O'zbekcha javob ber."}
        objection_prompt = (
            SYSTEM_PROMPT + f"\n\nРЕЖИМ ОБРАБОТКИ ВОЗРАЖЕНИЙ. "
            f"{lang_instruction.get(lang, 'Answer in English.')} "
            "Клиент интересуется AI-ботом для бизнеса, но задаёт вопросы перед покупкой. "
            "Отвечай коротко (2-4 предложения), конкретно, с фактами. "
            "В конце ответа мягко верни к действию."
        )
        response = gemini_chat(objection_prompt, session["history"], text)
        session["history"].append({"user": text, "bot": response})

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_try_free").split("(")[0].strip(), callback_data="funnel_demo")],
            [InlineKeyboardButton(text=t(lang, "btn_pricing"), callback_data="funnel_pricing")],
            [InlineKeyboardButton(text=t(lang, "btn_more_question"), callback_data="funnel_question")],
        ])
        await message.answer(response, reply_markup=kb)
        return

    # === Mode: receptionist (default) ===
    response = gemini_chat(SYSTEM_PROMPT, session["history"], text)
    session["history"].append({"user": text, "bot": response})
    
    # Check for payment markers [PAY:week/month/premium/custom]
    import re as _re
    pay_match = _re.search(r'\[PAY:(\w+)\]', response)
    if pay_match:
        plan_key = pay_match.group(1)
        clean_resp = _re.sub(r'\[PAY:\w+\]', '', response).strip()
        if clean_resp:
            await message.answer(clean_resp)
        if plan_key in STAR_PLANS:
            await send_stars_invoice(message, plan_key)
        session["history"].append({"user": text, "bot": clean_resp})
        return
    
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
        await send_with_voice(message, response)


async def main():
    logger.info("AI Centers Receptionist (live mode) starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
