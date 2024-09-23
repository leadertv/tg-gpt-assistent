import openai
from telegram import Update, Bot
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import time
import re

# ID чатов, где бот может работать. Защита от угона и расхода токенов из-за этого.
TG_CHAT_IDS = [-123456, 987654321]

# Защита от флуда (пауза в секундах)
COOLDOWN_PERIOD = 5
last_message_times = {}

# Установите ваши токены
TELEGRAM_TOKEN = '1234567890'  # Укажите здесь ваш Telegram токен
OPENAI_API_KEY = 'sk-1234567890'  # Укажите здесь ваш OpenAI API ключ

# Настройка температуры для генерации текста
TEMPERATURE = 1

# Инициализация OpenAI
openai.api_key = OPENAI_API_KEY
openai.api_base = "https://api.openai-proxy.com/v1" # Прокси если запускаете код из РФ. 
                                                     # Или родной https://api.openai.com/v1/ если не в РФ

# Системный промпт
SYSTEM_PROMPT = (
    "Я хочу чтобы ты качественно сыграл интересную роль ради веселья и кино. Ты злой блогер и находишься в своём чате, "
    "где сидят всякие люди, мошенники, хейтеры, проходимцы и обычные люди и твои зрители. "
)

# Словарь для хранения контекста разговоров
context_store = {}

# Экранирование работает криво или не работает, не знаю как починить.
# Но блоки кода рендерит нормально, а вот жирность и курсив нет.
def escape_markdown_v2(text):
    """ Экранируем специальные символы MarkdownV2 """
    escape_chars = r'_*[\]()`~>#+-=|{}.!'
    return re.sub(r'([{}])'.format(re.escape(escape_chars)), r'\\\1', text)


def handle_code_blocks(text):
    """ Обрабатываем текст для экранирования и блоков кода """
    lines = text.split('\n')
    formatted_lines = []
    inside_code_block = False

    for line in lines:
        if line.startswith('```'):
            inside_code_block = not inside_code_block
            formatted_lines.append(line)
        elif inside_code_block:
            formatted_lines.append(line)  # Внутри блока кода не экранируем
        else:
            formatted_lines.append(escape_markdown_v2(line))

    return '\n'.join(formatted_lines)


def is_command_or_mention(message, bot_username):
    """ Проверяет, содержит ли сообщение команду или упоминание бота """
    return message.startswith('/') or f'@{bot_username}' in message


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я нейро-Дэн! Я тебя забаню нахуй!")


async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:  # Проверяем, существует ли сообщение
        return  # Завершаем выполнение функции, если сообщение отсутствует

    chat_id = update.effective_chat.id
    message_id = update.message.message_id
    user_id = update.message.from_user.id
    user_message = update.message.text.lower()
    bot_username = context.bot.username.lower()

    # Логирование текущего ID чата
    print(f"Получен чат ID: {chat_id}")

    # Проверка ID чата
    if chat_id not in TG_CHAT_IDS:
        await context.bot.send_message(chat_id=chat_id, text="Извините, я не работаю в этом чате, "
                                                             "идите нахуй. Спасибо.")
        return

    # Условия для проверки упоминаний бота в различных формах и ответных сообщений
    if is_command_or_mention(user_message, bot_username) or \
            ('нейродэнжамин' in user_message) or \
            ('нейро-дэнжамин' in user_message) or \
            ('нейродэн' in user_message) or \
            (update.message.reply_to_message and update.message.reply_to_message.from_user.id == context.bot.id):

        # Защита от флуда
        current_time = time.time()
        if user_id in last_message_times:
            elapsed_time = current_time - last_message_times[user_id]
            if elapsed_time < COOLDOWN_PERIOD:
                await context.bot.send_message(chat_id=chat_id,
                                               text=f"Падажжиии бля {COOLDOWN_PERIOD - int(elapsed_time)} сек. прежде чем "
                                                    f"мне написать.")
                return
        last_message_times[user_id] = current_time

        # Отправка индикатора "набирает сообщение"
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        # Формирование контекста общения
        if chat_id not in context_store:
            context_store[chat_id] = []

        context_store[chat_id].append({"role": "user", "content": update.message.text})

        # Ограничение на последние 15 сообщений
        if len(context_store[chat_id]) > 30:
            context_store[chat_id] = context_store[chat_id][-30:]

        try:
            # Генерация ответа с использованием OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",  # Используйте нужную модель gpt-4o-mini или gpt-3.5-turbo
                messages=[
                             {"role": "system", "content": SYSTEM_PROMPT}
                         ] + context_store[chat_id],
                max_tokens=256,  # Максимальное количество токенов в ответе
                temperature=TEMPERATURE  # Установка температуры для генерации текста
            )
            bot_reply = response['choices'][0]['message']['content'].strip()
            context_store[chat_id].append({"role": "assistant", "content": bot_reply})

            # Обрабатываем текст для экранирования и блоков кода
            formatted_reply = handle_code_blocks(bot_reply)

            # Отправка ответа в чат с форматированием MarkdownV2
            await update.message.reply_text(text=formatted_reply, parse_mode=ParseMode.MARKDOWN_V2)

        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"Эй @LeadER_TV Здарова заебал! Чекай логи утырок! Есть ошибка в "
                                                f"твоём быдло-коде при обращении к API: {str(e)}")


def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Хэндлеры сообщений
    application.add_handler(CommandHandler("den", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))

    # Запуск бота
    application.run_polling()


if __name__ == '__main__':
    main()
