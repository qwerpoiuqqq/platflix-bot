import logging
from datetime import datetime, timedelta

from utils.sheet_helper import get_sheet_df, append_row, update_sheet_df
from utils.telegram_helper import send_telegram_message
from utils.email_helper import send_premium_email, send_friend_email, get_due_date_str

def is_in_extends(df_ext, email):
    if "이메일" not in df_ext.columns:
        return False
    return not df_ext[df_ext["이메일"] == email].empty

def format_phone(num: str) -> str:
    """숫자만 골라 11자리면 xxx-xxxx-xxxx, 10자리면 xx-xxxx-xxxx"""
    digits = "".join(filter(str.isdigit, num))
    if len(digits) == 11:
        return f"{digits[:3]}-{digits[3:7]}-{digits[7:]}"
    if len(digits) == 10:
        return f"{digits[:2]}-{digits[2:6]}-{digits[6:]}"
    return num  # 포맷 불가 시 원본 반환

def record_expiring_users():
    df_main = get_sheet_df("user_data")
    df_ext  = get_sheet_df("extends_data")
    today   = datetime.now().date()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    targets = []

    for i, row in df_main.iterrows():
        exp = datetime.strptime(row["만료일"], "%Y-%m-%d").date()
        # 이미 만료된 경우 or 만료 3일 전
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
        phone     = format_phone(u.get("전화번호", ""))
        remark    = u.get("비고", "")
        group     = u.get("그룹", "")
        group_no  = u.get("그룹 번호", "")
        friend_pay= u.get("지인 결제 여부", "")
        friend_f  = u.get("지인 여부", "")
        due       = get_due_date_str(exp_str)

        # 메일 발송
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
            # 새로 추가된 '기록 시간' 컬럼(L)에 now_str 기록
            append_row("extends_data", [
                name, email, exp_str, phone, remark,
                group, group_no, friend_pay, friend_f, "", "", now_str
            ])
            send_telegram_message(f"[record] {name} 이메일→extends_data 기록")

def check_payment_and_extend():
    df_ext  = get_sheet_df("extends_data")
    df_main = get_sheet_df("user_data")
    to_remove = []

    for i, row in df_ext.iterrows():
        # 레코드된 정보
        name       = row["이름"]
        email      = row["이메일"]
        old_exp    = datetime.strptime(row["만료일"], "%Y-%m-%d").date()
        record_ts  = datetime.strptime(row.get("기록 시간", ""), "%Y-%m-%d %H:%M:%S")
        deposit    = row.get("입금 여부", "")
        months     = row.get("연장 개월수", "")
        
        # 삭제 기준 계산
        if old_exp > record_ts.date():
            # 만료 3일 전 대상: 만료일까지 기다림
            delete_deadline = datetime.combine(old_exp, datetime.max.time())
        else:
            # 이미 만료된 대상: 기록 시간 + 1일, 23:59:59
            delete_deadline = (record_ts + timedelta(days=1)).replace(
                hour=23, minute=59, second=59
            )

        now = datetime.now()
        # 연장 개월수 파싱
        ext_m = 1
        if "3" in str(months):
            ext_m = 3
        elif "6" in str(months):
            ext_m = 6

        if str(deposit).upper() == "O":
            # 입금 완료 → 만료일 연장
            idxs = df_main[df_main["이메일"] == email].index
            if len(idxs) > 0:
                j      = idxs[0]
                prev   = datetime.strptime(df_main.loc[j, "만료일"], "%Y-%m-%d").date()
                new_dt = prev + timedelta(days=30 * ext_m)
                df_main.loc[j, "만료일"] = new_dt.strftime("%Y-%m-%d")
                send_telegram_message(f"[extend] {name}: {prev}→{new_dt} ({ext_m}개월)")
            else:
                send_telegram_message(f"[extend] 실패 — {name} not found")
            to_remove.append(i)

        else:
            # 미입금, 삭제 시점 도달 시 user_data 삭제
            if now >= delete_deadline:
                idxs = df_main[df_main["이메일"] == email].index
                if len(idxs) > 0:
                    df_main.drop(idxs, inplace=True)
                    send_telegram_message(f"[drop] {name} 탈락→삭제 (기한 만료)")
                to_remove.append(i)

    if to_remove:
        df_ext.drop(to_remove, inplace=True)
        update_sheet_df("extends_data", df_ext)
        update_sheet_df("user_data", df_main)
        send_telegram_message(f"[check] {len(to_remove)}명 처리 후 extends_data/user_data 갱신")

def handle_phone_list_for_sms():
    df_ext = get_sheet_df("extends_data")
    # 대상이 없거나 컬럼 누락 시 종료
    if df_ext.empty or "전화번호" not in df_ext.columns:
        send_telegram_message("[sms] 대상 없음")
        return

    names  = df_ext["이름"].dropna().astype(str).tolist()
    phones = [format_phone(p) for p in df_ext["전화번호"].dropna().astype(str).tolist()]

    if not names:
        send_telegram_message("[sms] 대상 없음")
        return

    name_msg  = "[만료자 안내]\n" + "\n".join(f"- {n}" for n in names)
    phone_msg = "[번호목록]\n" + ", ".join(phones)

    send_telegram_message(name_msg)
    send_telegram_message(phone_msg)
