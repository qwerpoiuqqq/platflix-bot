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
# GOOGLE_JSON_KEY: Render 환경변수에 설정한 서비스 계정 JSON 키 내용 (멀티라인 문자열)
GOOGLE_JSON_KEY = os.environ['GOOGLE_JSON_KEY']

# ===== 구글 시트 연결 함수 =====
def get_sheet():
    # JSON 키를 임시 파일에 저장
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
    # 실제 연장 처리 로직을 구현할 예정입니다.
    # 예: 시트의 각 행을 순회하여 '연장 개월수'와 '입금 여부' 조건에 맞으면
    #    만료일을 업데이트하고 해당 행을 삭제하는 로직
    return updated_users

# ===== 헬퍼 함수 =====
def format_user_entry(user):
    name = user.get("이름", "이름없음")
    email = user.get("이메일", "이메일없음")
    group = user.get("그룹", "")
    admin = group.split('@')[0] if "@" in group else group
    note = user.get("비고", "").strip()
    # 비고 필드가 공란이면 생략
    if note:
        return f"- {name} ({email}) | 그룹 관리자: {admin} | 비고: {note}"
    else:
        return f"- {name} ({email}) | 그룹 관리자: {admin}"

def load_users():
    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            users = json.load(f)
        return users
    except Exception as e:
        return None

# ===== 텔레그램 핸들러 함수들 =====

# 도움말 명령어: .도움말
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🛠 사용 가능한 명령어 (일반 메시지 방식):\n"
        ".도움말 - 도움말 보기\n"
        ".파일다운로드 - user_data를 엑셀로 다운로드\n"
        ".만료 N - 오늘 기준 N일 후(또는 전) 만료 대상자 목록\n"
        "    예: .만료 3  → 내일부터 3일 후까지 만료 대상자\n"
        "         .만료 -2 → 오늘 전 2일 동안 만료된 대상자\n"
        ".오늘만료 - 오늘 만료되는 사용자 목록\n"
        ".무료 사용자 - 무료 사용자 목록 출력"
    )
    await update.message.reply_text(text)

# 파일 다운로드 명령어: .파일다운로드
async def download_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("파일 다운로드 기능 동작 (샘플)")

# 만료 명령어: .만료 N  
async def expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        n_str = context.matches[0].group(1)
        n = int(n_str)
    except Exception as e:
        await update.message.reply_text("명령어 형식이 올바르지 않습니다. 예: .만료 3 또는 .만료 -2")
        return

    today = datetime.now().date()
    groups = {}

    users = load_users()
    if users is None:
        await update.message.reply_text("사용자 데이터를 불러올 수 없습니다.")
        return

    if n > 0:
        # 내일부터 오늘+n일까지 (즉, 1일 후부터 n일 후)
        for user in users:
            if "만료일" in user:
                try:
                    exp_date = datetime.strptime(user["만료일"], "%Y-%m-%d").date()
                except:
                    continue
                if today < exp_date <= today + timedelta(days=n):
                    diff = (exp_date - today).days  # 양의 정수
                    header = f"만료 {diff}일 후 ({exp_date.strftime('%Y-%m-%d')})"
                    groups.setdefault(header, []).append(format_user_entry(user))
    elif n < 0:
        # 오늘+n일부터 어제까지 (즉, n일 전부터 1일 전)
        for user in users:
            if "만료일" in user:
                try:
                    exp_date = datetime.strptime(user["만료일"], "%Y-%m-%d").date()
                except:
                    continue
                if today + timedelta(days=n) <= exp_date < today:
                    diff = (today - exp_date).days  # 양의 정수
                    header = f"만료 {diff}일 전 ({exp_date.strftime('%Y-%m-%d')})"
                    groups.setdefault(header, []).append(format_user_entry(user))
    else:
        # n == 0: 오늘 만료되는 사용자
        for user in users:
            if "만료일" in user:
                try:
                    exp_date = datetime.strptime(user["만료일"], "%Y-%m-%d").date()
                except:
                    continue
                if exp_date == today:
                    header = f"만료 오늘 ({today.strftime('%Y-%m-%d')})"
                    groups.setdefault(header, []).append(format_user_entry(user))

    if groups:
        # 정렬: 만료일 차이를 기준으로 정렬 (숫자 추출)
        def sort_key(header):
            try:
                parts = header.split()
                diff_str = parts[1].replace("일", "")
                return int(diff_str)
            except:
                return 0

        sorted_headers = sorted(groups.keys(), key=sort_key)
        message_parts = []
        for header in sorted_headers:
            message_parts.append(header + ":")
            message_parts.extend(groups[header])
            message_parts.append("")  # 빈 줄 추가
        msg = "\n".join(message_parts)
    else:
        msg = "해당 조건의 만료 대상자가 없습니다."

    await update.message.reply_text(msg)

# 오늘 만료 명령어: .오늘만료
async def today_expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().date()
    header = f"만료 오늘 ({today.strftime('%Y-%m-%d')})"
    entries = []
    
    users = load_users()
    if users is None:
        await update.message.reply_text("사용자 데이터를 불러올 수 없습니다.")
        return
    
    for user in users:
        if "만료일" in user:
            try:
                exp_date = datetime.strptime(user["만료일"], "%Y-%m-%d").date()
            except:
                continue
            if exp_date == today:
                entries.append(format_user_entry(user))
    
    if entries:
        msg = header + ":\n" + "\n".join(entries)
    else:
        msg = "오늘 만료되는 대상자가 없습니다."
    await update.message.reply_text(msg)

# 무료 사용자 명령어: .무료 사용자
async def free_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 조건: "지인 여부"가 'O', "결제 여부"가 'X', "만료일 없음"
    entries = []
    users = load_users()
    if users is None:
        await update.message.reply_text("사용자 데이터를 불러올 수 없습니다.")
        return

    for user in users:
        exp_date = user.get("만료일", "").strip()
        if (user.get("지인 여부", "").strip().upper() == "O" and 
            user.get("결제 여부", "").strip().upper() == "X" and 
            not exp_date):
            entries.append(format_user_entry(user))

    if entries:
        msg = "무료 사용자 목록:\n" + "\n".join(entries)
    else:
        msg = "무료 사용자가 없습니다."
    await update.message.reply_text(msg)

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
                logging.error(f"[DailyCheckError] {e}")
            await asyncio.sleep(3600)
        else:
            await asyncio.sleep(60)

# ===== 메인 함수 =====
async def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 핸들러 등록 (정규식을 이용한 일반 메시지 처리)
    app.add_handler(MessageHandler(filters.Regex(r'^\.도움말$'), help_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.파일다운로드$'), download_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.만료\s*(-?\d+)$'), expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.오늘만료$'), today_expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.무료\s*사용자$'), free_users_command))

    # 백그라운드 자동 체크 작업 시작
    asyncio.create_task(daily_check(app))

    # 봇 실행 (close_loop=False로 이벤트 루프 충돌 방지)
    await app.run_polling(close_loop=False)

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
