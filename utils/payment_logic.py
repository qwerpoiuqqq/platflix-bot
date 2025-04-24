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
    2) 이메일 발송 → extends_data에 기록
    3) 텔레그램에 발송 대상 알림
    """
    df_main = get_sheet_df("user_data")
    df_ext  = get_sheet_df("extends_data")
    today   = datetime.now().date()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    targets = []
    for i, row in df_main.iterrows():
        exp = datetime.strptime(row["만료일"], "%Y-%m-%d").date()
        # 만료 3일 전 or 이미 만료된 사용자
        if exp <= today or exp == today + timedelta(days=3):
            # 지인 + 결제 여부 X인 경우 건너뛰기
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

        # 지인+공란 → 친구용 이메일 / 그 외 → 프리미엄 이메일
        if remark == "지인" and friend_pay.strip() == "":
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
                name,
                email,
                exp_str,
                phone,
                remark,
                group,
                group_no,
                friend_pay,
                friend_f,
                "",  # 연장 개월수
                "",  # 입금 여부
                now_str
            ])
            sent_names.append(name)

    send_telegram_message("[record] 이메일 발송 대상:\n" + "\n".join(f"- {n}" for n in sent_names))


def check_payment_and_extend():
    """
    1) extends_data에서 입금 여부(O)면 user_data 만료일 연장
    2) 입금 여부 X, 삭제 기한 도달 시 user_data 삭제
    3) 처리된 레코드 extends_data/user_data에서 제거
    """
    df_ext = get_sheet_df("extends_data")
    if df_ext.empty:
        send_telegram_message("[check] extends_data 시트가 비어 있습니다. 패스합니다.")
        return

    df_main = get_sheet_df("user_data")
    to_remove = []
    extended = []
    dropped  = []

    for i, row in df_ext.iterrows():
        name = row["이름"]
        email = row["이메일"]
        old_exp = datetime.strptime(row["만료일"], "%Y-%m-%d").date()

        # 기록 시간이 빈 문자열이면 지금으로 대체
        rec = row.get("기록 시간", "")
        record_ts = datetime.strptime(rec, "%Y-%m-%d %H:%M:%S") if rec else datetime.now()

        deposit = row.get("입금 여부", "").strip().upper()
        months  = row.get("연장 개월수", "")
        now     = datetime.now()

        # 삭제 기한: 만료일 23:59 혹은 기록일+1일 23:59
        if old_exp > record_ts.date():
            deadline = datetime.combine(old_exp, datetime.max.time())
        else:
            deadline = (record_ts + timedelta(days=1)).replace(hour=23, minute=59, second=59)

        if deposit == "O":
            idxs = df_main[df_main["이메일"] == email].index
            if idxs.any():
                j    = idxs[0]
                prev = datetime.strptime(df_main.loc[j, "만료일"], "%Y-%m-%d").date()
                extm = 1
                if "3" in months: extm = 3
                if "6" in months: extm = 6
                newd = prev + timedelta(days=30 * extm)
                df_main.loc[j, "만료일"] = newd.strftime("%Y-%m-%d")
                extended.append(f"{name} ({extm}개월)")
            to_remove.append(i)

        elif now >= deadline:
            idxs = df_main[df_main["이메일"] == email].index
            if idxs.any():
                df_main.drop(idxs, inplace=True)
                dropped.append(name)
            to_remove.append(i)

    if to_remove:
        df_ext.drop(to_remove, inplace=True)
        update_sheet_df("extends_data", df_ext)
        update_sheet_df("user_data", df_main)

    if extended:
        send_telegram_message("[extend] 연장 완료:\n" + "\n".join(f"- {e}" for e in extended))
    if dropped:
        send_telegram_message("[drop] 삭제 완료:\n" + "\n".join(f"- {n}" for n in dropped))
    if not extended and not dropped:
        send_telegram_message("[check] 연장/삭제 대상 없음")


def handle_phone_list_for_sms():
    """
    문자 발송용: extends_data 이름·전화번호 목록을 두 번에 나눠 전송
    """
    df_ext = get_sheet_df("extends_data")
    if df_ext.empty or "전화번호" not in df_ext.columns:
        send_telegram_message("[sms] 대상 없음")
        return

    names  = df_ext["이름"].dropna().tolist()
    phones = [format_phone(p) for p in df_ext["전화번호"].dropna().tolist() if p.strip()]

    send_telegram_message("[만료자 안내]\n" + "\n".join(f"- {n}" for n in names))
    send_telegram_message("[번호목록]\n" + ", ".join(phones))
