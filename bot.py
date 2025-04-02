import logging
import json
import asyncio
from datetime import datetime, timedelta

# telegram 패키지
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)

# gspread, oauth 인증
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os

# ===== 환경 변수 =====
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
GOOGLE_JSON_KEY = os.environ['GOOGLE_JSON_KEY']

# ===== 구글 시트 연결 함수 =====
def get_sheet():
    with open("service_account.json", "w", encoding="utf-8") as f:
        f.write(GOOGLE_JSON_KEY)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

# ===== 연장 처리 함수 (placeholder) =====
def process_extension(sheet):
    updated_users = []
    return updated_users

# ===== 헬퍼 함수 =====
def format_user_entry(user):
    name = user.get("이름", "이름없음")
    email = user.get("이메일", "이메일없음")
    group = user.get("그룹", "")
    admin = group.split('@')[0] if "@" in group else group
    note = user.get("비고", "").strip()
    if note:
        return f"- {name} ({email}) | 그룹 관리자: {admin} | 비고: {note}"
    else:
        return f"- {name} ({email}) | 그룹 관리자: {admin}"

def load_users():
    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        return users
    except:
        return None

# ===== 핸들러 =====
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠 사용 가능한 명목어:\n"
        ".도움말 - 도움말 보기\n"
        ".파일다운로드 - user_data에서 파일 다운로드\n"
        ".만료 N - N일 후/전 만료 대상자 \n"
        ".오늘만료 - 오늘 만료 \n"
        ".무료 사용자 - 무료 대상자 보기"
    )
    await update.message.reply_text(text)

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("파일 다운로드 기능 동작 (사본)")

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
                label = f"만료 { (exp_date - today).days }일 후 ({exp_date})"
            elif n < 0:
                label = f"만료 { (today - exp_date).days }일 전 ({exp_date})"
            else:
                label = f"만료 오늘 ({today})"
            groups.setdefault(label, []).append(format_user_entry(user))

    if not groups:
        await update.message.reply_text("만료 대상자 없음")
        return

    result = []
    for k in sorted(groups.keys()):
        result.append(k + ":")
        result.extend(groups[k])
        result.append("")
    await update.message.reply_text("\n".join(result))

async def today_expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().date()
    users = load_users()
    if users is None:
        await update.message.reply_text("사용자 데이터 없음")
        return

    entries = [format_user_entry(u) for u in users if u.get("\ub9cc\ub8cc\uc77c", "") == today.strftime("%Y-%m-%d")]
    if entries:
        await update.message.reply_text(f"만료 오늘 ({today}):\n" + "\n".join(entries))
    else:
        await update.message.reply_text("오늘 만료 대상자 없음")

async def free_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    if users is None:
        await update.message.reply_text("사용자 데이터 로드 오류")
        return

    entries = [format_user_entry(u) for u in users 
               if u.get("지인 유무", "").upper() == "O" and \
                  u.get("결제 유무", "").upper() == "X" and \
                  not u.get("\ub9cc\ub8cc\uc77c", "").strip()]
    if entries:
        await update.message.reply_text("무료 사용자 목록:\n" + "\n".join(entries))
    else:
        await update.message.reply_text("무료 사용자 없음")

# ===== daily check =====
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

# ===== main =====
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(MessageHandler(filters.Regex(r'^\.\ub3c4\uc6c0\ub9d0$'), help_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.\ud30c\uc77c\ub2e4\uc6b4\ub85c\ub4dc$'), download_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.\ub9cc\ub8cc\s*(-?\d+)$'), expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.\uc624\ub298\ub9cc\ub8cc$'), today_expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.\ubb34\ub8cc\s*\uc0ac\uc6a9\uc790$'), free_users_command))

    await app.bot.delete_webhook(drop_pending_updates=True)
    asyncio.create_task(daily_check(app))
    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
