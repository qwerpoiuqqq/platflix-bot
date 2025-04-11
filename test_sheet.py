# test_sheet.py
import logging
logging.basicConfig(level=logging.INFO)

from utils.sheet_helper import get_sheet_df

if __name__ == "__main__":
    logging.info("[TEST] user_data 시트에서 데이터 읽기 시작")
    df = get_sheet_df("user_data")
    logging.info(f"[TEST] user_data → 행 개수: {len(df)}")
    print(df.head(10).to_string())
