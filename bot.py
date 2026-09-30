import asyncio
import json
import os
import re
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

def must(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("这里换成"):
        raise SystemExit(f"请先在 .env 里填写 {name}")
    return value

BOT_TOKEN = must("BOT_TOKEN")
OWNER_ID = int(must("OWNER_ID"))
MODEL = os.getenv("MODEL", "deepseek-chat").strip() or "deepseek-chat"
ALLOW_FILE = Path(__file__).with_name("allowed.json")

llm = OpenAI(
    api_key=must("OPENAI_API_KEY"),
    base_url=os.getenv("OPENAI_BASE_URL") or None,
)

SYSTEM = """你在Telegram群里当助手。
根据这个人刚发的话，判断该不该回。
不确定、灌水、纯表情、一句就能看懂的闲聊 → ignore。
该回时：短、像群聊、针对这句话，不要自称AI。
只输出JSON：
{"action":"ignore"}
或
{"action":"reply","text":"..."}
"""


def load_allowed() -> set[int]:
    if not ALLOW_FILE.exists():
        return set()
    try:
        return {int(x) for x in json.loads(ALLOW_FILE.read_text(encoding="utf-8"))}
    except Exception:
        return set()


def save_allowed(ids: set[int]) -> None:
    ALLOW_FILE.write_text(json.dumps(sorted(ids)), encoding="utf-8")


allowed = load_allowed()


def is_allowed(uid: int) -> bool:
    return uid == OWNER_ID or uid in allowed


def owner_only(message: Message) -> bool:
    return message.from_user is not None and message.from_user.id == OWNER_ID


def target_user(message: Message):
    parts = (message.text or "").split()
    if message.reply_to_message and message.reply_to_message.from_user:
        u = message.reply_to_message.from_user
        return u.id, u.full_name
    if len(parts) >= 2 and parts[1].lstrip("-").isdigit():
        return int(parts[1]), parts[1]
    return None


def judge(text: str, is_owner: bool) -> dict:
    who = "这是群主自己说的话，优先认真理解意图。" if is_owner else "这是被群主授权的人说的话。"
    resp = llm.chat.completions.create(
        model=MODEL,
        temperature=0.4,
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"{who}\n消息：{text}"},
        ],
    )
    raw = resp.choices[0].message.content or ""
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        return {"action": "ignore"}
    try:
        data = json.loads(m.group())
    except json.JSONDecodeError:
        return {"action": "ignore"}
    if data.get("action") != "reply":
        return {"action": "ignore"}
    out = (data.get("text") or "").strip()
    return {"action": "reply", "text": out} if out else {"action": "ignore"}


bot = Bot(BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def cmd_start(message: Message):
    if owner_only(message):
        await message.reply(
            "机器人已上线。\n"
            "群里：只处理你和已授权的人。\n"
            "授权别人：回复他的消息发送 /allow\n"
            "取消：回复他发送 /deny\n"
            "名单：/who"
        )
    else:
        await message.reply("这个机器人需要群主授权后才能在群里用。")


@dp.message(Command("allow"))
async def cmd_allow(message: Message):
    if not owner_only(message):
        return
    t = target_user(message)
    if not t:
        await message.reply("请先回复对方的一条消息，再发送 /allow")
        return
    uid, name = t
    if uid == OWNER_ID:
        await message.reply("你自己默认有权限。")
        return
    allowed.add(uid)
    save_allowed(allowed)
    await message.reply(f"已授权：{name}（{uid}）")


@dp.message(Command("deny"))
async def cmd_deny(message: Message):
    if not owner_only(message):
        return
    t = target_user(message)
    if not t:
        await message.reply("请先回复对方的一条消息，再发送 /deny")
        return
    uid, name = t
    allowed.discard(uid)
    save_allowed(allowed)
    await message.reply(f"已取消：{name}（{uid}）")


@dp.message(Command("who"))
async def cmd_who(message: Message):
    if not owner_only(message):
        return
    if not allowed:
        await message.reply("除你以外，还没有授权任何人。")
        return
    await message.reply("已授权ID：\n" + "\n".join(str(i) for i in sorted(allowed)))


@dp.message(F.chat.type.in_({"group", "supergroup"}), F.text)
async def on_group(message: Message):
    if message.from_user is None:
        return
    uid = message.from_user.id
    if not is_allowed(uid):
        return
    text = message.text or ""
    if text.startswith("/"):
        return
    result = judge(text, is_owner=(uid == OWNER_ID))
    if result["action"] == "reply":
        await message.reply(result["text"][:4000])


async def main():
    print("机器人启动中… 先私聊机器人发 /start 测试")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
