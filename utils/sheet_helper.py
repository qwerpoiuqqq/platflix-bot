import logging
import os
import gspread
import pandas as pd
from oauth2client.service_account import ServiceAccountCredentials

def get_google_client():
    """구글 시트 클라이언트를 생성하는 함수"""
    try:
        # 1) 환경 변수에서 JSON 키를 가져와 service_account.json 파일로 생성
        logging.info("[get_google_client] Creating service_account.json from environment variable.")
        with open("service_account.json", "w", encoding="utf-8") as f:
            f.write(os.environ['GOOGLE_JSON_KEY'])

        # 2) 구글 시트 API와 드라이브 API에 접근하기 위한 scope 설정
        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

        # 3) service_account.json을 이용해 자격증명 객체 생성
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

        # SPREADSHEET_ID 환경변수 확인
        spreadsheet_id = os.environ.get('SPREADSHEET_ID', None)
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")

        # 시트 열기
        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)

        # 데이터 읽기
        data = sheet.get_all_records()
        logging.info(f"[get_sheet_df] Retrieved {len(data)} rows from '{sheet_name}'.")

        # pandas DataFrame 변환
        df = pd.DataFrame(data)
        logging.info(f"[get_sheet_df] DataFrame shape: {df.shape}")
        return df

    except Exception as e:
        logging.error(f"[get_sheet_df] Error fetching data from sheet '{sheet_name}': {e}")
        # 오류 시 빈 DataFrame 리턴하거나, 필요하다면 raise
        return pd.DataFrame()

def append_row(sheet_name, row_data: list):
    """지정된 시트에 한 줄 데이터를 추가"""
    try:
        logging.info(f"[append_row] Appending row to sheet: {sheet_name}")
        client = get_google_client()
        spreadsheet_id = os.environ.get('SPREADSHEET_ID', None)
        if not spreadsheet_id:
            raise ValueError("SPREADSHEET_ID 환경변수가 설정되지 않았습니다.")

        sheet = client.open_by_key(spreadsheet_id).worksheet(sheet_name)
        sheet.append_row(row_data)
        logging.info(f"[append_row] Row appended: {row_data}")

    except Exception as e:
        logging.error(f"[append_row] Error appending row to sheet '{sheet_name}': {e}")
        # 필요한 경우 raise e
