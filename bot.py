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

# 환경 변수
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
GOOGLE_JSON_KEY = os.environ['GOOGLE_JSON_KEY']

# 시트 연결 함수
def get_sheet():
    with open("service_account.json", "w", encoding="utf-8") as f:
        f.write(GOOGLE_JSON_KEY)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    return client.open_by_key(SPREADSHEET_ID).sheet1

# 연장 처리 함수 (미구현)
def process_extension(sheet):
    return []

# 유저 데이터 로딩
def load_users():
    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return None

# 포맷: 이모지 + 줄바꿈
def format_user_entry(user):
    name = user.get("이름", "이름없음")
    email = user.get("이메일", "이메일없음")
    group = user.get("그룹", "")
    admin = group.split('@')[0] if "@" in group else group
    note = user.get("비고", "").strip()
    
    entry = f"👤 {name}\n📧 {email}\n👑 그룹 관리자: {admin}"
    if note:
        entry += f"\n📝 비고: {note}"
    return entry

# 명령어: .도움말
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🛠 사용 가능한 명령어:\n"
        ".도움말 - 도움말 보기\n"
        ".파일다운로드 - user_data 엑셀 다운로드\n"
        ".만료 N - 오늘 기준 N일 후/전 만료 대상자\n"
        ".오늘만료 - 오늘 만료되는 사용자\n"
        ".무료 사용자 - 무료 사용자 목록"
    )

# 명령어: .파일다운로드
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("파일 다운로드 기능 동작 (샘플)")

# 명령어: .만료 N
async def expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n = int(context.matches[0].group(1))
    except:
        await update.message.reply_text("형식 오류: 예) .만료 3 또는 .만료 -2")
        return

    today = datetime.now().date()
    users = load_users()
    if not users:
        await update.message.reply_text("데이터 로드 실패")
        return

    groups = {}

    for user in users:
        try:
            exp_date = datetime.strptime(user.get("만료일", ""), "%Y-%m-%d").date()
        except:
            continue

        if n > 0 and today < exp_date <= today + timedelta(days=n):
            key = f"📅 만료 { (exp_date - today).days }일 후 ({exp_date})"
        elif n < 0 and today + timedelta(days=n) <= exp_date < today:
            key = f"📅 만료 { (today - exp_date).days }일 전 ({exp_date})"
        elif n == 0 and exp_date == today:
            key = f"📅 만료 오늘 ({today})"
        else:
            continue

        groups.setdefault(key, []).append(format_user_entry(user))

    if groups:
        msg = ""
        for k in sorted(groups.keys()):
            msg += f"{k}:\n" + "\n\n".join(groups[k]) + "\n\n"
        await update.message.reply_text(msg.strip())
    else:
        await update.message.reply_text("해당 조건의 만료 대상자가 없습니다.")

# 명령어: .오늘만료
async def today_expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().date()
    users = load_users()
    if not users:
        await update.message.reply_text("데이터 로드 실패")
        return

    entries = []
    for user in users:
        try:
            if datetime.strptime(user.get("만료일", ""), "%Y-%m-%d").date() == today:
                entries.append(format_user_entry(user))
        except:
            continue

    if entries:
        msg = f"📅 만료 오늘 ({today}):\n" + "\n\n".join(entries)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("오늘 만료되는 사용자가 없습니다.")

# 명령어: .무료 사용자
async def free_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    if not users:
        await update.message.reply_text("데이터 로드 실패")
        return

    entries = []
    for user in users:
        if (user.get("지인 여부", "").strip().upper() == "O" and
            user.get("결제 여부", "").strip().upper() == "X" and
            not user.get("만료일", "").strip()):
            entries.append(format_user_entry(user))

    if entries:
        msg = "🎁 무료 사용자 목록:\n" + "\n\n".join(entries)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("무료 사용자가 없습니다.")

# 자동 연장 체크 루프
async def daily_check(app):
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute < 5:
            try:
                sheet = get_sheet()
                updated = process_extension(sheet)
                if updated:
                    await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text="✅ 연장 완료:\n" + "\n".join(updated))
            except Exception as e:
                logging.error(f"[DailyCheckError] {e}")
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)

# 메인 함수
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 충돌 방지용 Webhook 삭제
    await app.bot.delete_webhook(drop_pending_updates=True)

    # 핸들러 등록
    app.add_handler(MessageHandler(filters.Regex(r'^\.도움말$'), help_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.파일다운로드$'), download_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.만료\s*(-?\d+)$'), expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.오늘만료$'), today_expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.무료\s*사용자$'), free_users_command))

    # 자동 연장 체크
    asyncio.create_task(daily_check(app))

    # 실행
    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
