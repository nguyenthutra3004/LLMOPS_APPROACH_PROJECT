from datetime import datetime
import pandas as pd
from google.cloud import bigquery
import os
from utils import connect_to_mongo
from pandas.api import types as ptypes
import json
# 1) Cấu hình
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "neusolution.json"
MONGO_DB      = "training_messages"
MONGO_COL     = "news_v2"
BQ_PROJECT    = "neusolution"
BQ_DATASET    = "message"
BQ_TABLE      = "news_v2"

def check_mongo_dtypes(df, num_samples=2):
    print("===> Kiểu dữ liệu hiện tại trong MongoDB:\n")
    for col in df.columns:
        series = df[col].dropna()
        types_found = series.map(lambda x: type(x).__name__).unique()

        print(f"- Cột '{col}':")
        print(f"    Loại dữ liệu tìm thấy: {types_found}")

        # Nếu dữ liệu là list/dict → không dùng unique()
        if any(isinstance(x, (list, dict)) for x in series.head(10)):
            sample_values = series.head(num_samples).tolist()
        else:
            sample_values = series.unique()[:num_samples]

        print(f"    Giá trị mẫu: {sample_values}\n")
def clean_dataframe_for_bigquery(df):
    for col in df.columns:
        # Lấy một giá trị mẫu không null để xác định kiểu
        sample_series = df[col].dropna()
        sample_value = sample_series.iloc[0] if not sample_series.empty else None

        # 1) Kiểm tra kiểu số nguyên
        if ptypes.is_integer_dtype(df[col].dtype):
            # Giữ nguyên int64
            df[col] = df[col].astype('Int64')  # pandas Nullable Integer
            continue

        # 2) Kiểm tra kiểu số thực (float)
        if ptypes.is_float_dtype(df[col].dtype):
            # Giữ nguyên int64
            df[col] = df[col].astype('Int64')  # float64
            continue

        # 3) Kiểm tra kiểu boolean
        if ptypes.is_bool_dtype(df[col].dtype):
            df[col] = df[col].astype('boolean')  # pandas Nullable Boolean
            continue

        # 4) Kiểm tra kiểu datetime
        if ptypes.is_datetime64_any_dtype(df[col].dtype) or isinstance(sample_value, datetime):
            df[col] = pd.to_datetime(df[col], errors='coerce')
            continue

        # 5) Kiểm tra dict / list
        #    Chuyển thành JSON string với dấu nháy kép
        if isinstance(sample_value, (dict, list)):
            df[col] = df[col].apply(
                lambda x: json.dumps(x, ensure_ascii=False) if isinstance(x, (dict, list)) else None
            )
            continue

        # 6) Các trường hợp còn lại (chuỗi, object khác)
        #    Ép thành string bình thường
        df[col] = df[col].astype(str)

    return df

collection = connect_to_mongo(
    db_name=MONGO_DB,
    collection_name=MONGO_COL
)
df = pd.DataFrame(collection.find())  
# (Tuỳ nhu cầu) Loại bỏ _id nếu không cần
if "_id" in df.columns:
    df.drop(columns=["_id"], inplace=True)
# Thêm chỉ số tăng dần 
df.insert(0, "index", range(1, len(df) + 1))
df["index"] = df["index"].astype("Int64")
# 3) Khởi tạo BigQuery client
check_mongo_dtypes(df)
bq = bigquery.Client(project="neusolution")
# 4) Đẩy DataFrame lên BigQuery
table_id = f"{"neusolution"}.{BQ_DATASET}.{BQ_TABLE}"
df = clean_dataframe_for_bigquery(df)
job = bq.load_table_from_dataframe(df, table_id)   # Mặc định append
job.result()  # chờ hoàn thành
print(f"Đã đẩy {len(df)} bản ghi lên {table_id}")
