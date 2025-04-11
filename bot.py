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

# 환경변수 불러오기
TELEGRAM_TOKEN = os.environ['TELEGRAM_TOKEN']
ADMIN_CHAT_ID = os.environ['ADMIN_CHAT_ID']
SPREADSHEET_ID = os.environ['SPREADSHEET_ID']
GOOGLE_JSON_KEY = os.environ['GOOGLE_JSON_KEY']

# 시트에서 사용자 불러오기
def load_users():
    logging.info("🧾 [load_users] 시트에서 사용자 데이터 로딩 중...")
    df = get_sheet_df("user_data")
    logging.info(f"✅ [load_users] 총 {len(df)}명 로드됨.")
    return df.to_dict(orient="records")

# 사용자 정보를 보기 좋게 포맷
def format_user_entry(user):
    name = user.get("이름", "이름없음")
    email = user.get("이메일", "이메일없음")
    group = user.get("그룹", "")
    group_num = user.get("그룹 번호", "")
    admin = group.split('@')[0] if "@" in group else group
    return f"👤 {name}\n📧 {email}\n👑 {admin}('{group_num}')"

# .도움말 명령어 처리
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("[명령어] .도움말 실행됨")
    await update.message.reply_text(
        "🛠 사용 가능한 명령어:\n"
        ".도움말 - 도움말 보기\n"
        ".만료 N - 오늘 기준 N일 후/전 만료자 확인 (예: .만료 3)\n"
        ".오늘만료 - 오늘 만료되는 사용자\n"
        ".무료 사용자 - 무료 사용자 목록"
    )

# .만료 N 명령어 처리
async def expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("[명령어] .만료 N 실행됨")
    try:
        n = int(context.matches[0].group(1))
    except:
        await update.message.reply_text("❌ 형식 오류: 예) .만료 3 또는 .만료 -2")
        return

    today = datetime.now().date()
    users = load_users()
    groups = {}

    for user in users:
        try:
            exp_date = datetime.strptime(user.get("만료일", ""), "%Y-%m-%d").date()
            logging.info(f"🔍 {user.get('이름')} 만료일: {exp_date}")
        except Exception as e:
            logging.warning(f"⚠️ {user.get('이름')} 만료일 파싱 실패: {e}")
            continue

        if n > 0 and today < exp_date <= today + timedelta(days=n):
            key = f"❗만료 {exp_date - today} 후 ({exp_date})"
        elif n < 0 and today + timedelta(days=n) <= exp_date < today:
            key = f"❗만료 {today - exp_date} 전 ({exp_date})"
        elif n == 0 and exp_date == today:
            key = f"❗만료 오늘 ({today})"
        else:
            continue

        groups.setdefault(key, []).append(format_user_entry(user))

    if groups:
        msg = ""
        for k in sorted(groups.keys()):
            msg += f"{k}\n\n" + "\n\n".join(groups[k]) + "\n\n"
        await update.message.reply_text(msg.strip())
    else:
        await update.message.reply_text("📭 해당 조건의 만료 대상자가 없습니다.")

# .오늘만료 명령어 처리
async def today_expired_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("[명령어] .오늘만료 실행됨")
    today = datetime.now().date()
    users = load_users()
    entries = []

    for user in users:
        try:
            exp_date = datetime.strptime(user.get("만료일", ""), "%Y-%m-%d").date()
            if exp_date == today:
                entries.append(format_user_entry(user))
        except Exception as e:
            logging.warning(f"⚠️ {user.get('이름')} 날짜 파싱 실패: {e}")
            continue

    if entries:
        msg = f"❗오늘 만료 ({today})\n\n" + "\n\n".join(entries)
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("📭 오늘 만료되는 사용자가 없습니다.")

# .무료 사용자 명령어 처리
async def free_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("[명령어] .무료 사용자 실행됨")
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
        await update.message.reply_text("📭 무료 사용자가 없습니다.")

# 메인 실행 함수
async def main():
    logging.info("🚀 봇 시작 준비 중...")
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    # 명령어 핸들러 등록
    app.add_handler(MessageHandler(filters.Regex(r'^\.도움말$'), help_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.오늘만료$'), today_expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.만료\s*(-?\d+)$'), expired_command))
    app.add_handler(MessageHandler(filters.Regex(r'^\.무료\s*사용자$'), free_users_command))

    logging.info("✅ 핸들러 등록 완료")
    await app.run_polling()
    logging.info("📡 폴링 시작됨")

# 여기서 시트 연동 테스트도 함께 진행
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()

    try:
        # 시트 연동 테스트용
        logging.info("🧪 [테스트] 구글 시트 연동 테스트 시작")
        df = get_sheet_df("user_data")
        logging.info(f"🧪 [테스트] 시트에서 {len(df)}명 로딩 성공")
        logging.info(f"\n{df.head(5).to_string()}")

    except Exception as e:
        logging.error(f"❌ [테스트] 시트 연동 실패: {e}")

    asyncio.run(main())
