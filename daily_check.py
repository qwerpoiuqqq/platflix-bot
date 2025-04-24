import time
import schedule
import logging

from utils.payment_logic import (
    record_expiring_users,
    check_payment_and_extend,
    handle_phone_list_for_sms
)
from utils.telegram_helper import send_telegram_message

logging.basicConfig(level=logging.INFO)

def daily_check():
    """
    1) 만료 대상 기록 + 이메일 발송
    2) 입금 확인 후 연장/삭제
    3) 문자 발송용 이름·전화번호 목록 알림
    """
    try:
        send_telegram_message("🚀 [daily_check] 자동화 시작")
        record_expiring_users()
        check_payment_and_extend()
        handle_phone_list_for_sms()
        send_telegram_message("✅ [daily_check] 전체 프로세스 완료")
    except Exception as e:
        send_telegram_message(f"❗ [daily_check] 오류 발생: {e}")
        logging.error(f"[daily_check] 예외: {e}")

# 매일 아침 08:00에 실행되도록 설정
schedule.every().day.at("05:00").do(daily_check)

if __name__ == "__main__":
    # 스크립트 시작 즉시 한 번 실행
    send_telegram_message("[main] 스케줄러 시작 — 즉시 실행")
    daily_check()  # 즉시 실행

    # 이후 매 분마다 스케줄 점검
    send_telegram_message("[main] 루프 진입, 스케줄 대기 중")
    while True:
        schedule.run_pending()
        time.sleep(60)
