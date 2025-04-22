import os
import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST      = "smtp.gmail.com"
SMTP_PORT      = 587
EMAIL_ADDRESS  = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

def load_template(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"[load_template] 실패: {e}")
        return ""

def get_due_date_str(expire_date: str) -> str:
    """
    만료일(expire_date, 'YYYY-MM-DD')을 받아
    - 만료일이 미래면 오늘+3일
    - 이미 만료면 오늘+1일
    의 'M월 D일 (23시 59분까지)' 문자열을 반환합니다.
    """
    today = datetime.now().date()
    exp   = datetime.strptime(expire_date, "%Y-%m-%d").date()

    if exp > today:
        due = today + timedelta(days=3)
    else:
        due = today + timedelta(days=1)

    return f"{due.month}월 {due.day}일 (23시 59분까지)"

def send_premium_email(to_email, name, expire_date, sign_email, deposit_account, kakao_link, due_date):
    html = load_template("templates/premium_email.html")
    if not html:
        return False

    # 템플릿 변수 치환
    for key, val in {
        "{{이름}}": name,
        "{{만료일}}": expire_date,
        "{{가입이메일}}": sign_email,
        "{{입금계좌}}": deposit_account,
        "{{카카오채널링크}}": kakao_link,
        "{{납부기한}}": due_date
    }.items():
        html = html.replace(key, val)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[플랫플릭스] 구독 만료 안내 - {name}님"
    msg["From"]    = EMAIL_ADDRESS
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html", _charset="utf-8"))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        logging.info(f"[이메일] 전송 성공 → {to_email}")
        return True
    except Exception as e:
        logging.error(f"[이메일] 전송 실패 → {to_email}, 오류: {e}")
        return False

def send_friend_email(to_email, name, sign_email, deposit_account, due_date):
    html = load_template("templates/friends_email.html")
    if not html:
        return False

    for key, val in {
        "{{이름}}": name,
        "{{가입이메일}}": sign_email,
        "{{입금계좌}}": deposit_account,
        "{{납부기한}}": due_date
    }.items():
        html = html.replace(key, val)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[플랫플릭스] {name}님, 요금 안내드립니다 😊"
    msg["From"]    = EMAIL_ADDRESS
    msg["To"]      = to_email
    msg.attach(MIMEText(html, "html", _charset="utf-8"))

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()
        logging.info(f"[이메일] 지인용 전송 성공 → {to_email}")
        return True
    except Exception as e:
        logging.error(f"[이메일] 지인용 전송 실패 → {to_email}, 오류: {e}")
        return False
