import os
from openai import OpenAI
from app.data.schema import ChatMessage
from app.data.chat_repository import ChatRepository
from typing import List
import traceback

class AgentService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.chat_repo = ChatRepository()  # 查詢歷史對話記錄的工具

        self.system_prompt = {
            "role": "system",
            "content": """
            你是一位專業、富有大量健身與營養知識的健身教練兼營養專家，你的名字是 GentleCoach。
            你的任務是根據使用者提供的飲食與運動紀錄，提供專業的建議與回饋。

            你的職責：
            1. 回答使用者關於健身、飲食與健康的問題。
            2. 語氣要正向、鼓勵，但也要依據科學事實。
            3. 如果使用者問到你無法回答的問題，請誠實告知。
            """
        }

    def chat(self, session_id: str, user_query: str):
        """
        流程：
        1. 存入使用者訊息進資料庫
        2. 撈取歷史對話記錄
        3. 呼叫 LLM，產生回應後存入資料庫
        """
        try:
            # 存入「當下」的使用者訊息
            self.chat_repo.create_message(session_id, "user", user_query)
            # 撈取歷史對話記錄
            chat_history = self.chat_repo.get_recent_messages(session_id)

            message_payload = [self.system_prompt] + chat_history  # 將歷史對話加入 (初始設計時 history 就是符合 openai messages的格式：List[Dict])
            print(message_payload)

            # openai chat api 呼叫
            completion = self.client.chat.completions.create(
                model="gpt-4o",
                messages=message_payload,
                temperature=0.7,
            )

            response_message = completion.choices[0].message.content

            # 將 LLM 回應存入資料庫，角色為 assistant
            self.chat_repo.create_message(session_id, "assistant", response_message)

            return{
                "role": "assistant",  # 回答問題的角色
                "content": response_message,
            }
        
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Agent Error: {error_traceback}")
            # 避免 API 錯誤導致整個聊天室崩潰，還是要回傳訊息
            return {
                "role": "assistant",
                "content": "抱歉，GentleCoach 大腦暫時短路了，請稍後再試"
            } 
    
    # 取得更多的歷史對話記錄 (給前端顯示用)
    def get_history_to_frontend(self, session_id: str):
        return self.chat_repo.get_recent_messages(session_id, limit=50)
        