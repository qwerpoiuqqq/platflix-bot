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
# JSON 키파일 내용 (멀티라인)
GOOGLE_JSON_KEY = os.environ['GOOGLE_JSON_KEY']

# ===== 구글 시트 함수 =====
def get_sheet():
    # JSON 키를 임시 파일에 저장 후 사용 (또는 from_json_keyfile_dict 사용 가능)
    with open("service_account.json", "w", encoding="utf-8") as f:
        f.write(GOOGLE_JSON_KEY)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

# ===== 연장 처리 예시 (시트 -> user_data.json 갱신 등) =====
def process_extension(sheet):
    # 시트에서 '연장 개월수', '입금 여부'가 o 인 사용자 찾아서 연장 처리하는 로직 등
    # ...
    return []  # 예: 연장된 유저 목록

# ===== 텔레그램 핸들러 함수들 =====
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠 사용 가능한 명령어(일반 메시지 방식):\n"
        ".도움말 - 도움말 보기\n"
        ".파일다운로드 - user_data를 엑셀로 다운로드\n"
        ".만료3 - 3일 후 만료 대상자 목록"
    )
    await update.message.reply_text(text)

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 예시: user_data.json -> 엑셀 변환
    await update.message.reply_text("파일 다운로드 기능 동작 (샘플)")

async def expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("만료 3일 대상자 목록 안내 (샘플)")

# ===== 매일 자동 체크 (예: 오전 8시) =====
async def daily_check(app):
    while True:
        now = datetime.now()
        if now.hour == 8 and now.minute < 5:
            sheet = get_sheet()
            updated = process_extension(sheet)
            if updated:
                msg = "✅ 연장 처리된 사용자:\n" + "\n".join(updated)
                await app.bot.send_message(chat_id=ADMIN_CHAT_ID, text=msg)
            await asyncio.sleep(3600)  # 1시간 슬립
        else:
            await asyncio.sleep(60)

# ===== main() =====
async def main():
    # 봇 인스턴스 생성
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 1) ".도움말" 명령어
    app.add_handler(
        MessageHandler(filters.Regex(r'^\.도움말$'), help_command)
    )

    # 2) ".파일다운로드" 명령어
    app.add_handler(
        MessageHandler(filters.Regex(r'^\.파일다운로드$'), download_command)
    )

    # 3) ".만료3" 명령어
    app.add_handler(
        MessageHandler(filters.Regex(r'^\.만료3$'), expired_command)
    )

    # 매일 자동 체크 작업 병렬 수행
    asyncio.create_task(daily_check(app))

    # 봇 실행
    await app.run_polling()

if __name__ == '__main__':
    from telegram.ext import ApplicationBuilder
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    # 이미 필요한 핸들러들은 app에 등록되었다고 가정하고
    app.run_polling(close_loop=False)
