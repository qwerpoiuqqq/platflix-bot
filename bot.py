import logging
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# 환경변수 (Render에서 설정)
import os
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']

# 구글 인증
def get_sheet():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name('vaulted-journal-455310-n4-b59f57f4ed55.json', scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SPREADSHEET_ID).sheet1
    return sheet

# 사용자 연장 처리
def process_extension(sheet):
    rows = sheet.get_all_records()
    updated_users = []
    for i, row in enumerate(rows, start=2):  # 시트의 실제 행 번호
        if str(row['입금 여부']).lower() == 'o' and row['연장 개월수']:
            months = int(row['연장 개월수'].replace('개월', '').strip())
            try:
                expires = datetime.strptime(row['만료일'], '%Y-%m-%d').date()
            except:
                continue
            new_expiry = expires + timedelta(days=30 * months)
            row['만료일'] = new_expiry.strftime('%Y-%m-%d')
            sheet.update_cell(i, 3, row['만료일'])  # 만료일 업데이트
            sheet.delete_rows(i)  # 연장 처리 후 시트에서 삭제
            updated_users.append(f"{row['이름']} ({row['이메일']}) → +{months}개월")
    return updated_users

# 자동 체크 루프
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

# /도움말 명령어
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛠 사용 가능한 명령어:\n"
        "/도움말 - 이 도움말 보기\n"
        "/파일다운로드 - 전체 사용자 엑셀 파일 받기\n"
        "/만료3 - 3일 후 만료 대상자 보기\n"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=help_text)

# /파일다운로드 명령어
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from utils.json_to_excel import convert_json_to_excel
    path = convert_json_to_excel()
    await context.bot.send_document(chat_id=update.effective_chat.id, document=open(path, 'rb'))

# /만료3 명령어
async def expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().date()
    target = today + timedelta(days=3)
    with open("user_data.json", "r", encoding="utf-8") as f:
        users = json.load(f)
    filtered = [f"- {u['이름']} ({u['이메일']})" for u in users if '만료일' in u and u['만료일'] == target.strftime('%Y-%m-%d')]
    msg = "📆 3일 후 만료 예정:\n" + "\n".join(filtered) if filtered else "🙅‍♀️ 3일 후 만료자는 없습니다."
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

# main 함수
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("도움말", help_command))
    app.add_handler(CommandHandler("파일다운로드", download_command))
    app.add_handler(CommandHandler("만료3", expired_command))
    asyncio.create_task(daily_check(app))
    await app.run_polling()

if __name__ == '__main__':
    asyncio.run(main())
