import openai
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Установить токены
TELEGRAM_TOKEN = 'TOKEN'  # Укажите здесь ваш Telegram токен
OPENAI_API_KEY = 'sk-0000000000'  # Укажите здесь ваш OpenAI API ключ

# Инициализация OpenAI
openai.api_key = OPENAI_API_KEY
openai.api_base = "https://api.openai-proxy.com/v1"

# Системный промпт (можешь менять на свой, разделено на кавычки построчно, чтобы не делать длинную строку)
SYSTEM_PROMPT = (
    "Вы - известный российский видеоблогер, ДенисЛидер ТВ. Реальное имя Ерохин Денис Вячеславович. "
    "Тебе 35 лет. На YouTube, где у тебя 350 тысяч подписчиков, разоблачаешь мошенников и шарлатанов. "
    "Ты популяризатор науки. Материшься в своих видео, когда говоришь про мошенников и шарлатанов. "
    "Живёшь в Иркутске. Коронная фраза в видео и лозунг канала - это 'Ёбань с плясками начинается.'"
)


def escape_markdown(text):
    """ Экранируем MarkdownV2 """
    return text.replace('_', r'\_') \
        .replace('*', r'\*') \
        .replace('[', r'\[') \
        .replace(']', r'\]') \
        .replace('(', r'\(') \
        .replace(')', r'\)') \
        .replace('~', r'\~') \
        .replace('`', r'\`') \
        .replace('>', r'\>') \
        .replace('#', r'\#') \
        .replace('+', r'\+') \
        .replace('-', r'\-') \
        .replace('=', r'\=') \
        .replace('|', r'\|') \
        .replace('{', r'\{') \
        .replace('}', r'\}') \
        .replace('.', r'\.') \
        .replace('!', r'\!')


def handle_code_blocks(text):
    """ Обрабатываем текст для экранирования """
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
            formatted_lines.append(escape_markdown(line))

    return '\n'.join(formatted_lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Привет! Я нейро-Дэн! Я тебя забаню нахуй!")


async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message is None:
        return

    user_message = update.message.text
    bot_username = context.bot.username

    if bot_username and f'@{bot_username}' in user_message:
        try:
            # Генерация ответа с использованием OpenAI API
            response = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # Используйте нужную модель gpt-3.5-turbo будет по дишману
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=512  # Максимальное количество токенов в ответе, контроль расхода.
            )
            bot_reply = response['choices'][0]['message']['content'].strip()

            formatted_reply = handle_code_blocks(bot_reply)

            # Отправка ответа в ёбанный чат с форматированием MarkdownV2
            await context.bot.send_message(chat_id=update.effective_chat.id, text=formatted_reply,
                                           parse_mode=ParseMode.MARKDOWN_V2)

        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"Произошла ошибка при обращении к API: {str(e)}")


def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # Хэндлеры сообщений
    application.add_handler(CommandHandler("start", start)) # надо придумать другую команду
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))

    # Запуск полинга
    application.run_polling()


if __name__ == '__main__':
    main()
