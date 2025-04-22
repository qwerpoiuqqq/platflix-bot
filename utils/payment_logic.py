import logging
from datetime import datetime, timedelta
from utils.sheet_helper import get_sheet_df, append_row, update_sheet_df
from utils.telegram_helper import send_telegram_message
from utils.email_helper import send_premium_email, send_friend_email, get_due_date_str

def is_in_extends(df_ext, email):
    return not df_ext[df_ext["이메일"] == email].empty

def record_expiring_users():
    """
    user_data에서 이미 만료 or 3일 전 사용자만 골라
    이메일 발송 → extends_data 기록
    """
    df_main = get_sheet_df("user_data")
    df_ext  = get_sheet_df("extends_data")
    today   = datetime.now().date()
    targets = []

    for i, r in df_main.iterrows():
        exp = datetime.strptime(r["만료일"], "%Y-%m-%d").date()
        if exp <= today or exp == today + timedelta(days=3):
            if not is_in_extends(df_ext, r["이메일"]):
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

        # 지인 & 결제O → 친구용, 아니면 일반
        if friend_f.upper()=="O" and friend_pay.upper()=="O":
            ok = send_friend_email(
                email, name, email, "입금계좌", due
            )
        else:
            ok = send_premium_email(
                email, name, exp_str, email, "입금계좌", "카카오링크", due
            )

        if ok:
            append_row("extends_data", [
                name, email, exp_str, phone, remark,
                group, group_no, friend_pay, friend_f, "", ""
            ])
            send_telegram_message(f"[record] {name} 이메일→기록")

def check_payment_and_extend():
    """
    extends_data에서 입금 여부(O)면 user_data 연장,
    아니면 (만료일+3일 경과) user_data 삭제
    """
    df_ext  = get_sheet_df("extends_data")
    df_main = get_sheet_df("user_data")
    to_rm   = []

    for i, r in df_ext.iterrows():
        name    = r["이름"]
        email   = r["이메일"]
        old_str = r["만료일"]
        dep     = r["입금 여부"]
        months  = r.get("연장 개월수", "")
        exp     = datetime.strptime(old_str, "%Y-%m-%d").date()
        days_p  = (datetime.now().date() - exp).days

        ext_m = 1
        if "3" in months: ext_m = 3
        elif "6" in months: ext_m = 6

        if str(dep).upper()=="O":
            # 연장 처리
            idxs = df_main[df_main["이메일"]==email].index
            if len(idxs)>0:
                j      = idxs[0]
                old_dt = datetime.strptime(df_main.loc[j,"만료일"],"%Y-%m-%d").date()
                new_dt = old_dt + timedelta(days=30*ext_m)
                df_main.loc[j,"만료일"] = new_dt.strftime("%Y-%m-%d")
                send_telegram_message(f"[extend] {name}: {old_dt}→{new_dt}")
            else:
                send_telegram_message(f"[extend] 실패: {name}")
            to_rm.append(i)
        else:
            # 미입금 탈락 (만료일+3일 경과)
            if days_p >= 3:
                idxs = df_main[df_main["이메일"]==email].index
                if len(idxs)>0:
                    df_main.drop(idxs, inplace=True)
                    send_telegram_message(f"[drop] {name} 탈락→삭제")
                to_rm.append(i)

    if to_rm:
        df_ext.drop(to_rm, inplace=True)
        update_sheet_df("extends_data", df_ext)
        update_sheet_df("user_data", df_main)
        send_telegram_message(f"[check] {len(to_rm)}명 처리 후 삭제")

def handle_phone_list_for_sms():
    """
    문자용: extends_data에 남은 사용자들의
    이름 목록 / 전화번호 목록을 텔레그램으로 2회 전송
    """
    df_ext = get_sheet_df("extends_data")
    if df_ext.empty:
        send_telegram_message("[sms] 대상 없음")
        return

    names  = df_ext["이름"].tolist()
    phones = df_ext["전화번호"].dropna().astype(str).tolist()

    name_msg  = "[만료자 안내]\n" + "\n".join(f"- {n}" for n in names)
    phone_msg = "[번호목록]\n" + ", ".join(phones)

    send_telegram_message(name_msg)
    send_telegram_message(phone_msg)
