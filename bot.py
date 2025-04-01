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

# ===== 환경 변수 =====
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
GOOGLE_JSON_KEY = os.environ['GOOGLE_JSON_KEY']

# ===== 구글 시트 연결 =====
def get_sheet():
    with open("service_account.json", "w", encoding="utf-8") as f:
        f.write(GOOGLE_JSON_KEY)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

# ===== 연장 처리 (추후 구현) =====
def process_extension(sheet):
    updated_users = []
    # TODO: 시트 순회 → 조건 맞는 사용자 → 만료일 연장 처리
    return updated_users

# ===== .도움말 명령어 =====
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠 사용 가능한 명령어:\n"
        ".도움말 - 도움말 보기\n"
        ".파일다운로드 - user_data 엑셀로 받기\n"
        ".만료 N - N일 후까지 만료 대상자 전체 출력 (예: .만료 3, .만료 -2)"
    )
    await update.message.reply_text(text)

# ===== .파일다운로드 명령어 (샘플) =====
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("파일 다운로드 기능 동작 (샘플)")

# ===== .만료 N 명령어 =====
async def expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n_str = context.matches[0].group(1)
        n = int(n_str)
    except:
        await update.message.reply_text("형식: .만료 3 또는 .만료 -2")
        return

    today = datetime.now().date()
    result_lines = []

    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            users = json.load(f)
    except:
        await update.message.reply_text("⚠️ user_data.json 파일을 불러올 수 없습니다.")
        return

    if n > 0:
        for d in range(1, n + 1):
            date = (today + timedelta(days=d)).strftime('%Y-%m-%d')
            for u in users:
                if u.get("만료일") == date:
                    result_lines.append(f"- {u['이름']} ({u['이메일']}) | 만료일: {date}")
    elif n < 0:
        for d in range(n, 0):
            date = (today + timedelta(days=d)).strftime('%Y-%m-%d')
            for u in users:
                if u.get("만료일") == date:
                    result_lines.append(f"- {u['이름']} ({u['이메일']}) | 만료일: {date}")
    else:
        date = today.strftime('%Y-%m-%d')
        for u in users:
            if u.get("만료일") == date:
                result_lines.append(f"- {u['이름']} ({u['이메일']}) | 만료일: {date}")

    if result_lines:
        await update.message.reply_text("📆 만료 대상자:\n" + "\n".join(result_lines))
    else:
        await update.message.reply_text("📭 해당 조건의 만료 대상자가 없습니다.")

# ===== 매일 자동 실행 체크 =====
async def daily_check(app):
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute < 5:
            try:
                sheet = get_sheet()
                updated = process_extension(sheet)
                if updated:
                    msg = "✅ 연장 처리된 사용자:\n" + "\n".join(updated)
                    await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)
            except Exception as e:
                logging.error(f"[DailyCheckError] {e}")
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)

# ===== main 함수 =====
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.Regex(r'^\.도움말$'), help_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.파일다운로드$'), download_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.만료\s*(-?\d+)$'), expired_command))

    asyncio.create_task(daily_check(app))
    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
