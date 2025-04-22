import logging
from datetime import datetime, timedelta

from utils.sheet_helper import get_sheet_df, append_row, update_sheet_df
from utils.telegram_helper import send_telegram_message
from utils.email_helper import send_premium_email, send_friend_email, get_due_date_str

def format_phone(num: str) -> str:
    """숫자만 골라 11자리면 xxx-xxxx-xxxx, 10자리면 xx-xxxx-xxxx"""
    digits = "".join(filter(str.isdigit, num))
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
    return num

def is_in_extends(df_ext, email):
    """extends_data에 이미 해당 이메일이 기록되어 있는지 검사"""
    if "이메일" not in df_ext.columns:
        return False
    return not df_ext[df_ext["이메일"] == email].empty

def record_expiring_users():
    """
    1) user_data에서 이미 만료되었거나 만료 3일 전 대상 찾기
    2) 이메일 발송 → extends_data에 기록 (연장 개월수/입금 여부는 빈칸으로 남겨 두고, 나중에 수작업 입력)
    3) 처리된 이름을 모아 한 번에 텔레그램에 발송
    """
    df_main = get_sheet_df("user_data")
    df_ext  = get_sheet_df("extends_data")
    today   = datetime.now().date()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if df_ext.empty:
        send_telegram_message("[record] extends_data 시트가 비어 있습니다. 패스합니다.")
        return

    targets = []
    for i, row in df_main.iterrows():
        exp = datetime.strptime(row["만료일"], "%Y-%m-%d").date()
        if exp <= today or exp == today + timedelta(days=3):
            # '지인 결제 여부'가 "X"인 경우에는 extends_data에 추가하지 않음
            if row["비고"] == "지인" and row["결제 여부"].strip().upper() == "X":
                continue
            if not is_in_extends(df_ext, row["이메일"]):
                targets.append(i)

    if not targets:
        send_telegram_message("[record] 대상 없음")
        return

    sent_names = []
    for idx in targets:
        u          = df_main.loc[idx]
        name       = u["이름"]
        email      = u["이메일"]
        exp_str    = u["만료일"]
        phone      = format_phone(u.get("전화번호", ""))
        remark     = u.get("비고", "")
        group      = u.get("그룹", "")
        group_no   = u.get("그룹 번호", "")
        friend_pay = u.get("지인 결제 여부", "")
        friend_f   = u.get("지인 여부", "")
        due        = get_due_date_str(exp_str)

        # 템플릿 분기: 지인 결제 여부 X 또는 결제하지 않는 경우 'friends_email.html'로 발송
        if friend_pay == "X" or (friend_f.upper() == "O" and friend_pay != "X"):
            ok = send_friend_email(
                to_email=email,
                name=name,
                sign_email=email,
                deposit_account="입금계좌",
                due_date=due
            )
        else:
            ok = send_premium_email(
                to_email=email,
                name=name,
                expire_date=exp_str,
                sign_email=email,
                deposit_account="입금계좌",
                kakao_link="카카오링크",
                due_date=due
            )

        if ok:
            append_row("extends_data", [
                name,        # 이름
                email,       # 이메일
                exp_str,     # 만료일
                phone,       # 전화번호
                remark,      # 비고
                group,       # 그룹
                group_no,    # 그룹 번호
                friend_pay,  # 지인 결제 여부
                friend_f,    # 지인 여부
                "",          # 연장 개월수 (수동 입력)
                "",          # 입금 여부   (수동 입력)
                now_str      # 기록 시간
            ])
            sent_names.append(name)

    # 한 번에 묶어서 알림
    if sent_names:
        msg = "[record] 이메일 발송 대상:\n" + "\n".join(f"- {n}" for n in sent_names)
        send_telegram_message(msg)

def check_payment_and_extend():
    """
    1) extends_data에서 입금 여부(O)면 user_data 만료일 연장
    2) 입금 여부 X, 삭제 기한 도달 시 user_data에서 삭제
    3) 처리된 레코드를 extends_data 및 user_data에서 제거
    """
    df_ext = get_sheet_df("extends_data")
    df_main = get_sheet_df("user_data")
    to_remove = []

    extended = []
    dropped  = []

    if df_ext.empty:
        send_telegram_message("[check] extends_data 시트가 비어 있습니다. 패스합니다.")
        return

    for i, row in df_ext.iterrows():
        name = row["이름"]
        email = row["이메일"]
        old_exp = datetime.strptime(row["만료일"], "%Y-%m-%d").date()
        record_ts = datetime.strptime(row.get("기록 시간", ""), "%Y-%m-%d %H:%M:%S")
        deposit = row.get("입금 여부", "")  # 입금 여부가 'O'이면 연장
        months = row.get("연장 개월수", "")
        now = datetime.now()

        # 삭제 기한 계산 (만료일 기준 또는 기록일 기준)
        if old_exp > record_ts.date():
            delete_deadline = datetime.combine(old_exp, datetime.max.time())  # 만료일 23:59까지
        else:
            delete_deadline = (record_ts + timedelta(days=1)).replace(hour=23, minute=59, second=59)  # 기록일+1일

        if str(deposit).upper() == "O":
            # 입금 O: 연장 처리
            idxs = df_main[df_main["이메일"] == email].index
            if len(idxs) > 0:
                j      = idxs[0]
                prev   = datetime.strptime(df_main.loc[j, "만료일"], "%Y-%m-%d").date()
                ext_m  = 1
                if "3" in str(months):
                    ext_m = 3
                elif "6" in str(months):
                    ext_m = 6
                new_dt = prev + timedelta(days=30 * ext_m)
                df_main.loc[j, "만료일"] = new_dt.strftime("%Y-%m-%d")
                extended.append(f"{name} ({ext_m}개월)")
            to_remove.append(i)

        # 미입금 & 삭제 기한 도달 시 삭제
        elif now >= delete_deadline:
            idxs = df_main[df_main["이메일"] == email].index
            if len(idxs) > 0:
                df_main.drop(idxs, inplace=True)
                dropped.append(name)
            to_remove.append(i)

    # 처리된 레코드 삭제 및 시트 갱신
    if to_remove:
        df_ext.drop(to_remove, inplace=True)
        update_sheet_df("extends_data", df_ext)
        update_sheet_df("user_data", df_main)

    # 텔레그램 알림
    if extended:
        msg = "[extend] 연장 처리 완료:\n" + "\n".join(f"- {e}" for e in extended)
        send_telegram_message(msg)
    if dropped:
        msg = "[drop] 탈락 사용자 삭제:\n" + "\n".join(f"- {n}" for n in dropped)
        send_telegram_message(msg)
    if not extended and not dropped:
        send_telegram_message("[check] 연장/삭제 대상 없음")

def handle_phone_list_for_sms():
    """
    문자 발송용: extends_data의 이름·전화번호를 묶어서 두 번에 나눠 전송
    """
    df_ext = get_sheet_df("extends_data")
    if df_ext.empty or "전화번호" not in df_ext.columns:
        send_telegram_message("[sms] 대상 없음")
        return

    names  = df_ext["이름"].dropna().astype(str).tolist()
    phones = [
        format_phone(p)
        for p in df_ext["전화번호"].dropna().astype(str).tolist()
        if p.strip()
    ]

    if not names:
        send_telegram_message("[sms] 대상 없음")
        return

    name_msg  = "[만료자 안내]\n" + "\n".join(f"- {n}" for n in names)
    phone_msg = "[번호목록]\n" + ", ".join(phones)

    send_telegram_message(name_msg)
    send_telegram_message(phone_msg)