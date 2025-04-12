import os
from utils.email_helper import send_premium_email, send_friend_email
from datetime import datetime, timedelta

def get_due_date_str():
    d = datetime.now() + timedelta(days=1)
    return f"{d.month}월 {d.day}일 (23시 59분까지)"

user_info = {
    "이름": "테스트유저",
    "이메일": "받을이메일@gmail.com",
    "가입이메일": "google_account@gmail.com",
    "만료일": "2025-04-11",
    "입금계좌": "000-1234-5678",
    "카카오채널링크": "https://pf.kakao.com/_XXXXXX"
}

# 일반 사용자 메일 테스트
send_premium_email(
    to_email=user_info["이메일"],
    name=user_info["이름"],
    expire_date=user_info["만료일"],
    sign_email=user_info["가입이메일"],
    deposit_account=user_info["입금계좌"],
    kakao_link=user_info["카카오채널링크"],
    due_date=get_due_date_str()
)

# 또는 지인용 메일 테스트 (주석 해제 시 사용)
# send_friend_email(
#     to_email=user_info["이메일"],
#     name=user_info["이름"],
#     sign_email=user_info["가입이메일"],
#     deposit_account=user_info["입금계좌"],
#     due_date=get_due_date_str()
# )
