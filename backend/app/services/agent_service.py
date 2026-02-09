import os
from openai import OpenAI
from app.data.schema import ChatMessage
from typing import List
import traceback

class AgentService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

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

    def chat(self, history: List[ChatMessage]) -> ChatMessage:  # 接收對話陣列
        """
        處理對話請求
        history: 前端傳來的所有對話記錄
        """
        try:
            message_payload = [self.system_prompt] + [msg.model_dump() for msg in history]  # 將 ChatMessage 物件轉成字典

            # openai chat api 呼叫
            completion = self.client.chat.completions.create(
                model="gpt-4o",
                messages=message_payload,
                temperature=0.7,
            )

            response_message = completion.choices[0].message.content

            return ChatMessage(
                role='assistant',  # 回答問題的角色
                content=response_message,
            )
        
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"Agent Error: {error_traceback}")
            # 避免 API 錯誤導致整個聊天室崩潰，還是要回傳訊息
            return ChatMessage(
                role="assistant",
                content="抱歉，GentleCoach 大腦暫時短路了，請稍後再試"
            ) 
        