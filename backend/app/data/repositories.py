import os
from supabase import create_client, Client
from app.data.schema import FoodAnalysisResult, WorkoutLogRequest
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta

load_dotenv()

# 負責查詢資料庫的一切對話記錄操作
class ChatRepository:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL or Key not found in env")
        self.supabase: Client = create_client(url, key)  # 建立 Supabase 連線

    def get_recent_messages(self, session_id: str, limit: int):
        """
        取得最近的 N 筆對話記錄，並按時間新舊排序 (給 LLM 讀的順序)
        """
        try:
            # 要取出全部的對話
            if(limit == 0):
                # 這裡存的是圖片公開網址，內部 supabase 還要用網址去 bucket 存圖片
                response = self.supabase.table("chat_messages")\
                    .select("role, content, image_url")\
                    .eq("session_id", session_id)\
                    .order("created_at", desc=True)\
                    .execute()
            else:
                # 根據 session_id 查詢最新到最舊的記錄，並只取前 limit 筆
                response = self.supabase.table("chat_messages")\
                    .select("role, content, image_url")\
                    .eq("session_id", session_id)\
                    .order("created_at", desc=True)\
                    .limit(limit)\
                    .execute()

            data = response.data
            # 資料庫回傳: [最新, 第二新, 第三新, ...]
            # 翻轉後: [最舊, 第二舊, 第三舊, ..., 最新]，讓 LLM 可以讀到順序的意義
            return data[::-1]

        except Exception as e:
            print(f"Error fetching chat history: {e}")
            return []

    def create_message(self, session_id: str, role: str, content: str, image_url: str | None = None):
        """
        將當前的對話訊息寫入資料庫 (圖片不一定要有)
        """
        try:
            # 定義好要寫入的資料
            data = {
                "session_id": session_id,
                "role": role,
                "content": content,
                "image_url": image_url 
            }
            self.supabase.table("chat_messages").insert(data).execute()
            return True
        except Exception as e:
            print(f"Error creating chat message: {e}")
            return False

# 負責存取 workout_logs database
class WorkOutRepository:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL or Key not found in env")
        self.supabase: Client = create_client(url, key)  # 建立 Supabase 連線


    # 接收到前端請求，將健身記錄寫入資料庫
    def save_workout_logs(self, workout_data: WorkoutLogRequest):
        data_to_insert = {
            "exercise_name": workout_data.exercise_name,
            "body_part": workout_data.body_part,
            "weight": workout_data.weight,
            "sets": workout_data.sets,
            "reps": workout_data.reps,
        }
        try:
            response = self.supabase.table("workout_logs").insert(data_to_insert).execute()
            # response.data 是一個 list，裡面包含一筆剛寫入的資料
            if response.data:
                return response.data[0]
            else:
                raise Exception("Failed to save workout log")
        except Exception as e:
            print(f"Supabase Error: {e}")
            print(f"資料寫入失敗，但仍返回 AI 分析結果")
            return None

    # 根據使用者的查詢條件，從資料庫中取出最近的健身記錄
    def get_filtered_workouts(self, days: int, body_part: str | None = None, exercise_name: str | None = None):
        # 取得絕對的現在時間 (UTC)
        now_utc = datetime.now(timezone.utc)
        target_date = now_utc - timedelta(days=days)  # 例如查過去 7 天，日期就是 7 天前那天
        # 資料庫操作只能吃字串，故要轉換為字串格式
        target_date_str = target_date.isoformat()

        try:
            # greater than or equal to
            query = self.supabase.table("workout_logs").select("*").gte("created_at", target_date_str)

            # 根據使用者有給的特定查詢條件，再次過濾結果
            if body_part:
                query = query.eq("body_part", body_part)
            if exercise_name:
                # 使用者在對話輸入的可能不是精準的名稱，要模糊查詢
                query = query.ilike("exercise_name", f"%{exercise_name}%")

            response = query.order("created_at", desc=True).execute()

            return response.data

        except Exception as e:
            print(f"查詢最近 {days} 天的健身記錄失敗: {e}")
            return []

# 負責存取 food_logs database
class FoodRepository:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL or Key not found in env")
        self.supabase: Client = create_client(url, key)  # 建立 Supabase 連線

    def save_food_logs(self, food_data: FoodAnalysisResult, image_url: str, food_name: str, meal_type: str) -> dict:
        """
        將 AI 分析結果寫入 Supabase 的 food_log 資料表中
        Args:
            food_data: AI 分析出來的數據
            image_url: 圖片的 Supabase 公開網址 URL 字串
            food_name: 使用者填寫的食物名稱
            meal_type: 使用者選擇的用餐時段
        """

        # 過濾出要存進資料庫的欄位
        data_to_insert = {
            "food_name": food_name,
            "image_url": image_url, 
            "meal_type": meal_type,  # 上述兩者直接用使用者填寫的資料
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
            print(f"Supabase Error: {e}")
            print(f"資料寫入失敗，但仍返回 AI 分析結果")
            return None
