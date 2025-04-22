import logging
from datetime import datetime, timedelta

from utils.sheet_helper import get_sheet_df, append_row, update_sheet_df
from utils.telegram_helper import send_telegram_message
from utils.email_helper import send_premium_email, send_friend_email, get_due_date_str

def is_in_extends(df_ext, email):
    """
    extends_data에 '이메일' 컬럼이 없거나, 해당 이메일이 없으면 False.
    이미 기록된 이메일이면 True.
    """
    if "이메일" not in df_ext.columns:
        return False
    return not df_ext[df_ext["이메일"] == email].empty

def record_expiring_users():
    """
    user_data에서 이미 만료되었거나 만료 3일 전 사용자만 골라,
    이메일 발송 → extends_data에 기록. 중복 기록 방지.
    """
    df_main = get_sheet_df("user_data")
    df_ext  = get_sheet_df("extends_data")
    today   = datetime.now().date()
    targets = []

    for i, row in df_main.iterrows():
        exp = datetime.strptime(row["만료일"], "%Y-%m-%d").date()
        if exp <= today or exp == today + timedelta(days=3):
            if not is_in_extends(df_ext, row["이메일"]):
                targets.append(i)

    if not targets:
        send_telegram_message("[record] 대상 없음")
        return

    for idx in targets:
        u         = df_main.loc[idx]
        name      = u["이름"]
        email     = u["이메일"]
        exp_str   = u["만료일"]
        phone     = u.get("전화번호", "")
        remark    = u.get("비고", "")
        group     = u.get("그룹", "")
        group_no  = u.get("그룹 번호", "")
        friend_pay= u.get("지인 결제 여부", "")
        friend_f  = u.get("지인 여부", "")
        due       = get_due_date_str(exp_str)

        # 지인 결제 여부 O & 지인 여부 O → 친구용 이메일
        if friend_f.upper() == "O" and friend_pay.upper() == "O":
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
                name, email, exp_str, phone, remark,
                group, group_no, friend_pay, friend_f, "", ""
            ])
            send_telegram_message(f"[record] {name} 이메일 발송 → extends_data 기록")

def check_payment_and_extend():
    """
    extends_data에서 입금 여부(O) 사용자는 user_data 만료일 연장,
    입금 여부 X 사용자는 만료일+3일 경과 시 user_data에서 삭제.
    """
    df_ext  = get_sheet_df("extends_data")
    df_main = get_sheet_df("user_data")
    to_remove = []

    for i, row in df_ext.iterrows():
        name      = row["이름"]
        email     = row["이메일"]
        old_exp   = datetime.strptime(row["만료일"], "%Y-%m-%d").date()
        deposit   = row.get("입금 여부", "")
        months    = row.get("연장 개월수", "")
        days_past = (datetime.now().date() - old_exp).days

        # 연장 개월수 파싱
        ext_months = 1
        if "3" in str(months):
            ext_months = 3
        elif "6" in str(months):
            ext_months = 6

        if str(deposit).upper() == "O":
            # 연장 처리
            idxs = df_main[df_main["이메일"] == email].index
            if not idxs.empty:
                j      = idxs[0]
                prev   = datetime.strptime(df_main.loc[j, "만료일"], "%Y-%m-%d").date()
                new_exp= prev + timedelta(days=30 * ext_months)
                df_main.loc[j, "만료일"] = new_exp.strftime("%Y-%m-%d")
                send_telegram_message(f"[extend] {name}: {prev} → {new_exp} ({ext_months}개월)")
            else:
                send_telegram_message(f"[extend] 실패 — {name}을 user_data에서 찾을 수 없음")
            to_remove.append(i)

        else:
            # 미입금 탈락 (만료일+3일 경과 시 삭제)
            if days_past >= 3:
                idxs = df_main[df_main["이메일"] == email].index
                if not idxs.empty:
                    df_main.drop(idxs, inplace=True)
                    send_telegram_message(f"[drop] 미입금 탈락 — {name} 삭제")
                to_remove.append(i)

    if to_remove:
        df_ext.drop(to_remove, inplace=True)
        update_sheet_df("extends_data", df_ext)
        update_sheet_df("user_data", df_main)
        send_telegram_message(f"[check] {len(to_remove)}명 처리 후 extends_data 및 user_data 갱신")

def handle_phone_list_for_sms():
    """
    문자 발송용: extends_data에 기록된 사용자들의 이름 목록과
    전화번호 목록을 텔레그램으로 두 차례 전송.
    """
    df_ext = get_sheet_df("extends_data")

    # 컬럼 누락 혹은 빈 DataFrame 처리
    if df_ext.empty or "전화번호" not in df_ext.columns:
        send_telegram_message("[sms] 대상 없음")
        return

    names  = df_ext["이름"].dropna().astype(str).tolist()
    phones = df_ext["전화번호"].dropna().astype(str).tolist()

    if not names:
        send_telegram_message("[sms] 대상 없음")
        return

    name_msg  = "[만료자 안내]\n" + "\n".join(f"- {n}" for n in names)
    phone_msg = "[번호목록]\n" + ", ".join(phones)

    send_telegram_message(name_msg)
    send_telegram_message(phone_msg)
