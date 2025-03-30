import json
import pandas as pd

def convert_json_to_excel():
    with open("user_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    path = "user_data_export.xlsx"
    df.to_excel(path, index=False)
    return path
