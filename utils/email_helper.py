import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_ADDRESS = os.environ.get("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")

def load_template(template_path: str) -> str:
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logging.error(f"[load_template] 템플릿 로드 실패: {e}")
        return ""

def send_premium_email(to_email, name, expire_date, sign_email, deposit_account, kakao_link, due_date):
    html_body = load_template("templates/premium_email.html")
    if not html_body:
        return False

    html_body = html_body.replace("{{이름}}", name)
    html_body = html_body.replace("{{만료일}}", expire_date)
    html_body = html_body.replace("{{가입이메일}}", sign_email)
    html_body = html_body.replace("{{입금계좌}}", deposit_account)
    html_body = html_body.replace("{{카카오채널링크}}", kakao_link)
    html_body = html_body.replace("{{납부기한}}", due_date)

    subject = f"[플랫플릭스] 구독 만료 안내 - {name}님"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", _charset="utf-8"))

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
    html_body = load_template("templates/friends_email.html")
    if not html_body:
        return False

    html_body = html_body.replace("{{이름}}", name)
    html_body = html_body.replace("{{가입이메일}}", sign_email)
    html_body = html_body.replace("{{입금계좌}}", deposit_account)
    html_body = html_body.replace("{{납부기한}}", due_date)

    subject = f"[플랫플릭스] {name}님, 이번 달 요금 안내드립니다 😊"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html", _charset="utf-8"))

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
