import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    ContextTypes,
    filters
)
import os
from utils.sheet_helper import get_sheet_df, append_row

# 디버그 로그 설정
logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
GOOGLE_JSON_KEY = os.environ['GOOGLE_JSON_KEY']

# 유저 데이터 로딩 함수
def load_users():
    logging.info("Loading users data from Google Sheets...")
    df = get_sheet_df("user_data")
    return df.to_dict(orient="records")

# 사용자 정보를 형식에 맞게 포맷팅하는 함수
def format_user_entry(user):
    name = user.get("이름", "이름없음")
    email = user.get("이메일", "이메일없음")
    group = user.get("그룹", "")
    group_num = user.get("그룹 번호", "")
    admin = group.split('@')[0] if "@" in group else group
    return f"👤 {name}\n📧 {email}\n👑 {admin}('{group_num}')"

# 도움말 명령어 처리
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Help command triggered")
    await update.message.reply_text(
        "🛠 사용 가능한 명령어:\n"
        ".도움말 - 도움말 보기\n"
        ".파일다운로드 - user_data 엑셀 다운로드\n"
        ".만료 N - 오늘 기준 N일 후/전 만료 대상자\n"
        ".오늘만료 - 오늘 만료되는 사용자\n"
        ".무료 사용자 - 무료 사용자 목록"
    )

# 만료 명령어 처리
async def expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Expired command triggered")
    try:
        n = int(context.matches[0].group(1))
    except:
        await update.message.reply_text("형식 오류: 예) .만료 3 또는 .만료 -2")
        return

    today = datetime.now().date()
    users = load_users()
    groups = {}

    for user in users:
        try:
            exp_date = datetime.strptime(user.get("만료일", ""), "%Y-%m-%d").date()
        except:
            continue

        if n > 0 and today < exp_date <= today + timedelta(days=n):
            key = f"❗만료 {(exp_date - today).days}일 후 ({exp_date})❗"
        elif n < 0 and today + timedelta(days=n) <= exp_date < today:
            key = f"❗만료 {(today - exp_date).days}일 전 ({exp_date})❗"
        elif n == 0 and exp_date == today:
            key = f"❗만료 오늘 ({today})❗"
        else:
            continue

        groups.setdefault(key, []).append(format_user_entry(user))

    if groups:
        msg = ""
        for k in sorted(groups.keys()):
            msg += f"{k}\n\n" + "\n\n".join(groups[k]) + "\n\n"
        await update.message.reply_text(msg.strip())
    else:
        await update.message.reply_text("해당 조건의 만료 대상자가 없습니다.")

# 오늘 만료 명령어 처리
async def today_expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Today expired command triggered")
    today = datetime.now().date()
    users = load_users()
    entries = []

    for user in users:
        try:
            if datetime.strptime(user.get("만료일", ""), "%Y-%m-%d").date() == today:
                entries.append(format_user_entry(user))
        except:
            continue

    if entries:
        msg = f"❗만료 오늘 ({today})❗\n\n" + "\n\n".join(entries)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("오늘 만료되는 사용자가 없습니다.")

# 무료 사용자 명령어 처리
async def free_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Free users command triggered")
    users = load_users()
    entries = []

    for user in users:
        if (user.get("지인 여부", "").strip().upper() == "O" and
            user.get("결제 여부", "").strip().upper() == "X" and
            not user.get("만료일", "").strip()):
            entries.append(format_user_entry(user))

    if entries:
        msg = "🎁 무료 사용자 목록:\n\n" + "\n\n".join(entries)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("무료 사용자가 없습니다.")

# 파일 다운로드 명령어 처리
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Download command triggered")
    await update.message.reply_text("파일 다운로드 기능 동작 (샘플)")

# 연장자 시트에 기록
def add_extension_to_sheet(user):
    logging.info(f"Adding extension for user: {user.get('이름')}")
    row_data = [
        user.get("이름"),
        user.get("이메일"),
        user.get("만료일"),
        user.get("전화번호"),
        user.get("비고"),
        user.get("그룹"),
        user.get("그룹 번호"),
        "입금 여부",  # 입금 여부 필드, 실제 확인 후 입력
        "연장 개월수",  # 연장 개월수 (예: 1개월, 3개월)
    ]
    append_row("extends_data", row_data)

# 연장된 사용자 처리
def process_extension():
    logging.info("Processing extensions...")
    users = get_sheet_df("user_data")
    for user in users:
        exp_date = datetime.strptime(user.get("만료일", ""), "%Y-%m-%d").date()
        if exp_date == datetime.now().date() + timedelta(days=3):  # 3일 전 사용자
            add_extension_to_sheet(user)

# 입금 여부 확인 후 연장/삭제
def check_payment_and_extend():
    logging.info("Checking payments and processing extensions...")
    extends_data = get_sheet_df("extends_data")
    for user in extends_data:
        if user.get("입금 여부") == "o":
            # 연장 처리 (30일 + 연장 개월수 적용)
            pass
        else:
            # 입금 미확인 시 삭제 또는 최종 안내
            pass

# 매일 체크
async def daily_check(app):
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute < 5:
            try:
                process_extension()  # 연장 처리
                check_payment_and_extend()  # 입금 확인 후 연장
            except Exception as e:
                logging.error(f"[DailyCheckError] {e}")
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)

# 메인 실행 함수
async def main():
    logging.info("Starting bot...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    logging.info("App built successfully")

    # 명령어를 텍스트로만 비교 (정규식 변경)
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\.(도움말|파일다운로드|만료|오늘만료|무료 사용자)$'), help_command))
    app.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'^\.(만료|오늘만료|무료 사용자)$'), expired_command))

    logging.info("Handlers added successfully")

    try:
        logging.info("Starting polling...")
        await app.run_polling(close_loop=False)
        logging.info("Bot is running...")
    except Exception as e:
        logging.error(f"Error during polling: {e}")

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
