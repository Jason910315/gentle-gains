import os
from supabase import create_client, Client
from app.data.schema import FoodAnalysisResult
from dotenv import load_dotenv
import traceback

"""
與資料庫進行 CRUD 操作
"""

load_dotenv()

# 負責 Supabase 的 CRUD 操作
class FoodRepository:
    def __init__(self):
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL or Key not found in env")
        self.supabase: Client = create_client(url, key)  # 建立 Supabase 連線

    def save_food_logs(self, food_data: FoodAnalysisResult, image_base64: str, food_name: str, meal_type: str) -> dict:
        """
        將 AI 分析結果寫入 Supabase 的 food_log 資料表中
        Args:
            food_data: AI 分析出來的數據
            food_name: 使用者填寫的食物名稱
            meal_type: 使用者選擇的用餐時段
        """

        # 過濾出要存進資料庫的欄位
        data_to_insert = {
            "food_name": food_name,
            "image_url": image_base64,
            "meal_type": meal_type,  # 上述兩者直接用使用者填寫的數資料
            "calories": food_data.calories,
            "protein": food_data.protein,
            "fat": food_data.fat,
            "carbs": food_data.carbs,
            "score": food_data.score,
            "coach_comment": food_data.coach_comment,
        }

        try:
            response = self.supabase.table("food_logs").insert(data_to_insert).execute()
            # response.data 是一個 list，裡面包含一筆剛寫入的資料
            if response.data:
                return response.data[0]
            else:
                raise Exception("Failed to save food log")
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Supabase Error: {error_traceback}")
            print(f"資料寫入失敗，但仍返回 AI 分析結果")
            return None
