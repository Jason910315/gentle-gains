import os
from supabase import create_client, Client
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

if __name__ == "__main__":
    repo = ChatRepository()

    TEST_SESSION_ID = "afc433a0-3898-4f1c-8423-934e553c716f"

    print("開始存入資料")
    repo.create_message(TEST_SESSION_ID, "user", "你好")
    repo.create_message(TEST_SESSION_ID, "assistant", "你好，我是你的健身教練！")
    repo.create_message(TEST_SESSION_ID, "user", "我今天吃了什麼")
    repo.create_message(TEST_SESSION_ID, "assistant", "我喝了豆漿")

    print("\n開始讀取資料")
    recent_messages = repo.get_recent_messages(TEST_SESSION_ID)
    print(recent_messages)




       