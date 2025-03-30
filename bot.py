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
# JSON 키파일 내용 (멀티라인 문자열)
GOOGLE_JSON_KEY = os.environ['GOOGLE_JSON_KEY']

# ===== 구글 시트 함수 =====
def get_sheet():
    # JSON 키를 임시 파일로 저장
    with open("service_account.json", "w", encoding="utf-8") as f:
        f.write(GOOGLE_JSON_KEY)
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

# ===== 연장 처리 예시 (시트 -> user_data.json 갱신 등) =====
def process_extension(sheet):
    # 여기서 시트 데이터를 순회하며 연장 조건에 맞는 사용자 처리 로직 구현
    updated_users = []
    # 현재는 테스트용으로 빈 리스트 반환 (추후 실제 로직 추가)
    return updated_users

# ===== 텔레그램 핸들러 함수들 =====
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠 사용 가능한 명령어 (일반 메시지 방식):\n"
        ".도움말 - 도움말 보기\n"
        ".파일다운로드 - user_data를 엑셀로 다운로드\n"
        ".만료3 - 3일 후 만료 대상자 목록"
    )
    await update.message.reply_text(text)

async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 예시: user_data.json -> 엑셀 변환 (실제 기능은 utils/json_to_excel.py로 구현 예정)
    await update.message.reply_text("파일 다운로드 기능 동작 (샘플)")

async def expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("만료 3일 대상자 목록 안내 (샘플)")

# ===== 매일 자동 체크 (예: 오전 8시) =====
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
                logging.error(f"Daily check error: {e}")
            await asyncio.sleep(3600)  # 1시간 슬립
        else:
            await asyncio.sleep(60)

# ===== 메인 함수 =====
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 핸들러 등록 (정규식을 이용한 일반 메시지 처리)
    app.add_handler(MessageHandler(filters.Regex(r'^\.도움말$'), help_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.파일다운로드$'), download_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.만료3$'), expired_command))

    # 백그라운드 자동 체크 작업 시작
    asyncio.create_task(daily_check(app))

    # 봇 실행 (이벤트 루프 문제 해결을 위해 close_loop=False 사용)
    await app.run_polling(close_loop=False)

if __name__ == '__main__':
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
