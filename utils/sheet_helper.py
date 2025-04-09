import gspread
import os
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd

def get_google_client():
    with open("service_account.json", "w", encoding="utf-8") as f:
        f.write(os.environ['GOOGLE_JSON_KEY'])

    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name("service_account.json", scope)
    return gspread.authorize(creds)

def get_sheet_df(sheet_name="user_data"):
    client = get_google_client()
    sheet = client.open_by_key(os.environ['SPREADSHEET_ID']).worksheet(sheet_name)
    data = sheet.get_all_records()
    return pd.DataFrame(data)

def append_row(sheet_name, row_data: list):
    client = get_google_client()
    sheet = client.open_by_key(os.environ['SPREADSHEET_ID']).worksheet(sheet_name)
    sheet.append_row(row_data)

def delete_row(sheet_name, index: int):  # index는 2부터 시작 (헤더 제외)
    client = get_google_client()
    sheet = client.open_by_key(os.environ['SPREADSHEET_ID']).worksheet(sheet_name)
    sheet.delete_rows(index)
