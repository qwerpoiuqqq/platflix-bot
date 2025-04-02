import logging
import json
import asyncio
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
GOOGLE_JSON_KEY = os.environ['GOOGLE_JSON_KEY']

def get_sheet():
    with open("service_account.json", "w", encoding="utf-8") as f:
        f.write(GOOGLE_JSON_KEY)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

def process_extension(sheet):
    updated_users = []
    return updated_users

def format_user_entry(user):
    name = user.get("이름", "이름없음")
    email = user.get("이메일", "이메일없음")
    group = user.get("그룹", "")
    admin = group.split('@')[0] if "@" in group else group
    note = user.get("비고", "").strip()

    lines = [
        f"👤 {name}",
        f"📧 {email}",
        f"👑 그룹 관리자: {admin}"
    ]
    if note:
        lines.append(f"📝 비고: {note}")
    return "\n".join(lines)

def load_users():
    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        return users
    except:
        return None

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠 사용 가능한 명령어:\n"
        ".도움말 - 도움말 보기\n"
        ".파일다운로드 - user_data에서 파일 다운로드\n"
        ".만료 N - N일 후/전 만료 대상자 \n"
        ".오늘만료 - 오늘 만료 \n"
        ".무료 사용자 - 무료 대상자 보기"
    )
    await update.message.reply_text(text)

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("파일 다운로드 기능 동작 (샘플)")

async def expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(context.matches[0].group(1))
    except:
        await update.message.reply_text(".만료 N 가 유효한 형식이 아닐 경우")
        return

    today = datetime.now().date()
    users = load_users()
    if users is None:
        await update.message.reply_text("사용자 데이터 로드 오류")
        return

    groups = {}
    for user in users:
        try:
            exp_date = datetime.strptime(user.get("만료일", ""), "%Y-%m-%d").date()
        except:
            continue
        if (n > 0 and today < exp_date <= today + timedelta(days=n)) or \
           (n < 0 and today + timedelta(days=n) <= exp_date < today) or \
           (n == 0 and exp_date == today):
            if n > 0:
                label = f"📅 만료 { (exp_date - today).days }일 후 ({exp_date})"
            elif n < 0:
                label = f"📅 만료 { (today - exp_date).days }일 전 ({exp_date})"
            else:
                label = f"📅 만료 오늘 ({today})"
            groups.setdefault(label, []).append(format_user_entry(user))

    if not groups:
        await update.message.reply_text("만료 대상자 없음")
        return

    result = []
    for k in sorted(groups.keys()):
        result.append(k + ":")
        for entry in groups[k]:
            result.append(entry)
            result.append("")
    await update.message.reply_text("\n".join(result))

async def today_expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().date()
    users = load_users()
    if users is None:
        await update.message.reply_text("사용자 데이터 없음")
        return

    entries = [format_user_entry(u) for u in users if u.get("만료일", "") == today.strftime("%Y-%m-%d")]
    if entries:
        msg = f"📅 만료 오늘 ({today}):\n\n" + "\n\n".join(entries)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("오늘 만료 대상자 없음")

async def free_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    if users is None:
        await update.message.reply_text("사용자 데이터 로드 오류")
        return

    entries = [format_user_entry(u) for u in users 
               if u.get("지인 여부", "").upper() == "O" and \
                  u.get("결제 여부", "").upper() == "X" and \
                  not u.get("만료일", "").strip()]
    if entries:
        msg = "무료 사용자 목록:\n\n" + "\n\n".join(entries)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("무료 사용자 없음")

async def daily_check(app):
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute < 5:
            try:
                sheet = get_sheet()
                updated = process_extension(sheet)
                if updated:
                    msg = "✅ 연장 처리 완료:\n" + "\n".join(updated)
                    await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)
            except Exception as e:
                logging.error(f"[DailyCheckError] {e}")
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)

async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.Regex(r'^\.도움말$'), help_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.파일다운로드$'), download_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.만료\s*(-?\d+)$'), expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.오늘만료$'), today_expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.무료\s*사용자$'), free_users_command))

    await app.bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(daily_check(app))
    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
