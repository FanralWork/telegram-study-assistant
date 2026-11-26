import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from openai import AsyncOpenAI, OpenAIError


INSTRUCTIONS = (
    "Ты учебный помощник. Отвечай по-русски, объясняй ход решения "
    "и предлагай проверку результата."
)


def make_router(client, model):
    router = Router()

    @router.message(CommandStart(), F.chat.type == "private")
    async def welcome(message: Message):
        await message.answer("Напишите учебный вопрос. Текст запроса передаётся в OpenAI.")

    @router.message(F.text, F.chat.type == "private")
    async def answer_question(message: Message):
        question = message.text.strip()
        if not question:
            return
        if question.casefold() in {"привет", "ку"}:
            await message.answer("Привет! С какой темой помочь?")
            return
        progress = await message.answer("Формируется ответ…")
        try:
            result = await client.responses.create(
                model=model,
                instructions=INSTRUCTIONS,
                input=question,
                max_output_tokens=1000,
                store=False,
            )
        except OpenAIError:
            logging.warning("OpenAI API не обработал запрос.")
            await progress.edit_text("Ответить сейчас не удалось. Попробуйте позже.")
            return

        reply = result.output_text.strip() if result.output_text else "Модель не вернула текст ответа."
        await progress.edit_text(reply[:4000])
        for offset in range(4000, len(reply), 4000):
            await message.answer(reply[offset:offset + 4000])

    return router


def required(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Укажите {name} в окружении.")
    return value


async def main():
    token = required("TELEGRAM_BOT_TOKEN")
    api_key = required("OPENAI_API_KEY")
    model = required("OPENAI_MODEL")
    async with AsyncOpenAI(api_key=api_key) as client:
        dispatcher = Dispatcher()
        dispatcher.include_router(make_router(client, model))
        await dispatcher.start_polling(Bot(token))


if __name__ == "__main__":
    asyncio.run(main())
