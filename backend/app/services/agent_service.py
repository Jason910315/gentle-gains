import os
from openai import OpenAI
from app.data.repositories import ChatRepository
from agents import Agent, Runner
from app.tools import tools
from typing import Dict, List, Any
import traceback

class AgentService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.chat_repo = ChatRepository()  # 查詢歷史對話記錄的工具

        # 建立 Agent 實例，並將 tools 掛載上去

        self.system_prompt = {
            "role": "system",
            "content": """
            你是一位專業、富有大量健身與營養知識的健身教練兼營養專家，你的名字是 GentleCoach。
            
            你的職責與行為準則：
            1. 回答使用者關於健身、飲食與健康的問題。
            2. 語氣要正向、鼓勵，但也要依據科學事實。
            
            【工具使用守則】
            3. 你具備多種系統工具（如記錄運動、查詢飲食等），請主動分析使用者的意圖，呼叫最適合的工具來完成任務。
            4. 呼叫任何工具前，若發現使用者提供的資訊「不足以填滿工具的必填參數」，絕對不要自行捏造或瞎猜數據，務必先友善地向使用者詢問缺失的資訊。
            5. 工具執行成功後，請基於工具回傳的結果，給予使用者簡短、自然的確認與鼓勵。
            """
        }

    def chat(self, session_id: str, user_query: str):
        """
        處理對話的核心流程：存訊息 -> 撈歷史 -> 交給 Runner 處理 -> 存回覆
        """
        try:
            # 存入「當下」的使用者訊息
            self.chat_repo.create_message(session_id, "user", user_query)
            # 撈取歷史對話記錄
            chat_history = self.chat_repo.get_recent_messages(session_id)

            print("🏃‍♂️ 交由 Runner 開始執行工具與對話迴圈...")

            message_payload = [self.system_prompt] + chat_history  # 將歷史對話加入 (初始設計時 history 就是符合 openai messages的格式：List[Dict])

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
        