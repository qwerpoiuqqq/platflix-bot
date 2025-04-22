import logging
import os
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

def get_google_client():
    """구글 시트 클라이언트를 생성하는 함수"""
    try:
        logging.info("[get_google_client] Creating service_account.json from environment variable.")
        with open("service_account.json", "w", encoding="utf-8") as f:
            f.write(os.environ['GOOGLE_JSON_KEY'])

        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
        client = gspread.authorize(creds)

        logging.info("[get_google_client] Google Sheets client created successfully.")
        return client

    except Exception as e:
        logging.error(f"[get_google_client] Failed to create Google client: {e}")
        raise e

def get_sheet_df(sheet_name="user_data"):
    """구글 시트에서 데이터를 가져와서 pandas DataFrame으로 반환"""
    try:
        logging.info(f"[get_sheet_df] Fetching data from sheet: {sheet_name}")
        client = get_google_client()

        spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")

        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        data = sheet.get_all_records()
        logging.info(f"[get_sheet_df] Retrieved {len(data)} rows from '{sheet_name}'.")

        df = pd.DataFrame(data)
        logging.info(f"[get_sheet_df] DataFrame shape: {df.shape}")
        return df

    except Exception as e:
        logging.error(f"[get_sheet_df] Error fetching data from sheet '{sheet_name}': {e}")
        return pd.DataFrame()

def append_row(sheet_name, row_data: list):
    """지정된 시트에 한 줄 데이터를 추가"""
    try:
        logging.info(f"[append_row] Appending row to sheet: {sheet_name}")
        client = get_google_client()

        spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")

        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        sheet.append_row(row_data, value_input_option="USER_ENTERED")
        logging.info(f"[append_row] Row appended: {row_data}")

    except Exception as e:
        logging.error(f"[append_row] Error appending row to sheet '{sheet_name}': {e}")

def update_sheet_df(sheet_name, df):
    """
    DataFrame 전체를 해당 시트에 덮어쓰기 합니다.
    — 기존 데이터를 지우고, 새 DataFrame의 헤더+값을 업데이트
    """
    try:
        logging.info(f"[update_sheet_df] Updating entire sheet: {sheet_name}")
        client = get_google_client()

        spreadsheet_id = os.environ.get('SPREADSHEET_ID')
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")

        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        sheet.clear()
        sheet.update([df.columns.tolist()] + df.values.tolist())
        logging.info(f"[update_sheet_df] Sheet '{sheet_name}' updated successfully.")

    except Exception as e:
        logging.error(f"[update_sheet_df] Error updating sheet '{sheet_name}': {e}")
