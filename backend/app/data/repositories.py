import os
from supabase import create_client, Client
from app.data.schema import FoodAnalysisResult, WorkoutLogRequest
from dotenv import load_dotenv
import traceback

load_dotenv()

# 負責查詢資料庫的一切對話記錄操作
class ChatRepository:
    def __init__(self):
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("Supabase URL or Key not found in env")
        self.supabase: Client = create_client(url, key)  # 建立 Supabase 連線

    def get_recent_messages(self, session_id: str, limit: int = 10):
        """
        取得最近的 N 筆對話記錄，並按時間新舊排序 (給 LLM 讀的順序)
        """
        try:
            # 根據 session_id 查詢最新到最舊的記錄，並只取前 10 筆
            response = self.supabase.table("chat_messages")\
                .select("role, content")\
                .eq("session_id", session_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .execute()

            data = response.data
            # 資料庫回傳: [最新, 第二新, 第三新, ...]
            # 翻轉後: [最舊, 第二舊, 第三舊, ..., 最新]，讓 LLM 可以讀到順序的意義
            return data[::-1]

        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error fetching chat history: {error_traceback}")
            return []

    def create_message(self, session_id: str, role: str, content: str):
        """
        將當前的對話訊息寫入資料庫
        """
        try:
            # 定義好要寫入的資料
            data = {
                "session_id": session_id,
                "role": role,
                "content": content
            }
            self.supabase.table("chat_messages").insert(data).execute()
            return True
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Error creating chat message: {error_traceback}")
            return False

# 負責存取 workout_logs database
class WorkOutRepository:
    def __init__(self):
        url: str = os.getenv("SUPABASE_URL")
        key: str = os.getenv("SUPABASE_KEY")
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
            error_traceback = traceback.format_exc()
            print(f"Supabase Error: {error_traceback}")
            print(f"資料寫入失敗，但仍返回 AI 分析結果")
            return None

# 負責存取 food_logs database
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
