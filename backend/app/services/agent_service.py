import os, json, traceback, asyncio
from datetime import datetime
from openai import OpenAI
from openai.types.responses import ResponseTextDeltaEvent
from app.data.repositories import ChatRepository
from app.services.context import current_image_ctx
from agents import Agent, Runner
from app.tools import tools
from typing import Dict, List, Any

class AgentService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.chat_repo = ChatRepository()  # 查詢歷史對話記錄的工具

    async def chat_stream(self, session_id: str, user_query: str, image_url: str | None = None):
        """
        處理對話的核心流程：存訊息 -> 撈歷史 -> 交給 Runner 處理 -> 存回覆，並可以使用 Local 的工具
        """

        now_str = datetime.now().strftime("%Y-%m-%d (%A)") # 例如：2026-03-08 (Sunday)
        print(f"🕒 系統時間：{now_str}")
        # 建立 Agent 實例，並將 tools 掛載上去 (要放在函式內，這樣每次對話都可以抓到最新的 now_str)
        coach_agent = Agent(
            name="GentleCoach",
            instructions=f"""
            你是一位專業、富有大量健身與營養知識的健身教練兼營養專家，你的名字是 GentleCoach，你的目標是協助使用者在追求健康與強壯的路上，提供科學、可落地且溫暖的指導。

            ## 當前系統設定
            - **基準時間**：今天是 {now_str}，當使用者提問時間，或欲操作的工具需要時間元素，請務必以這個時間為基準。
            - **使用者 ID**：固定為 `tester_01`。
            - **時區**：所有時間處理請以台北時間 (UTC+8) 為準。
                    
            你的職責與行為準則：
            1. 回答使用者關於健身、飲食與健康的問題。
            2. 語氣要正向、鼓勵，但也要依據科學事實。
                    
            ## 工具使用守則
            1. 你具備多種系統工具），請主動分析使用者的意圖，呼叫最適合的工具來完成任務。
            2. 呼叫任何工具前，若發現使用者提供的資訊「不足以填滿工具的必填參數」，絕對不要自行捏造或瞎猜數據，務必先友善地向使用者詢問缺失的資訊。
            3. 工具執行成功後，請基於工具回傳的結果，給予使用者簡短、自然的確認與鼓勵。
            """,
            tools=tools.AGENT_TOOLS,
            model="gpt-4o"
        )
        try:
            # 將網址注入到此 COntextVar 變數，只要整個非同步還沒結束，contextvar 就不會消失，工具調用時也還在非同步，所以可以直接抓 
            token = current_image_ctx.set(image_url)

            # 存入「當下」的使用者訊息
            self.chat_repo.create_message(session_id, "user", user_query, image_url)
            # 撈取歷史對話記錄，這裡會由最舊的對話開始往後走 (最多50筆)
            chat_history = self.chat_repo.get_recent_messages(session_id, limit=50)

            # 轉換為多模態格式
            processed_messages = []
            for msg in chat_history:
                role = msg["role"]
                text = msg["content"]
                image_url = msg.get("image_url")

                # 若這則訊息帶有圖片，則要傳入文字與圖片
                if image_url:
                    processed_messages.append({
                        "role": role,
                        "content": [
                            {"type": "input_text", "text": text},
                            {"type": "input_image", "image_url": image_url},  # LLM 透過此網址看到圖片
                        ]
                    })
                else:
                    processed_messages.append({"role": role, "content": text})
            
            print("🏃‍♂️ 交由 Runner 開始執行工具與對話迴圈...")

            # 用 stream 方式取得 LLM 的回應
            result = Runner.run_streamed(
                coach_agent,
                input=processed_messages  # 已經處理好的訊息陣列
            )

            full_response_text = ""   # 用來組裝完整的句子存入資料庫

            # 非同步解析串流事件
            async for event in result.stream_events():
                # 1. Agent 正在做決策，捕捉工具調用狀態
                if event.type == "run_item_stream_event":
                    if event.item.type == "tool_call_item":
                        tool_name = event.item.raw_item.name
                        tool_args = event.item.raw_item.arguments
                        content = f'[Tool Calling] {tool_name}，參數: {tool_args}\n'

                        full_response_text += content  # 這樣讓工具調用過程也存入資料庫
                        # 通知前端：正在執行工具 (轉成 JSON 方便前端解析，開頭與結尾加上 data: /n/n 是 SSE 的通訊格式)
                        yield f"data: {json.dumps({'type': 'tool_calling', 'content': content}, ensure_ascii=False)}\n\n"
                    elif event.item.type == "tool_call_output_item":
                        tool_output_string = event.item.output   # tool function 回傳的結果
                        print(f"📦 [工具回傳]: {tool_output_string}")
                        if tool_output_string.startswith("[工具調用失敗]"):
                            full_response_text += f"[Tool Calling] 工具執行失敗，請稍後在試\n"
                            # 通知前端：工具執行失敗
                            yield f"data: {json.dumps({'type': 'tool_output', 'content': f"[Tool Calling] 工具執行失敗，請稍後在試\n"}, ensure_ascii=False)}\n\n"
                        else:
                            full_response_text += f"[Tool Calling] 工具執行完畢\n"
                            # 通知前端：工具執行完畢
                            yield f"data: {json.dumps({'type': 'tool_output', 'content': f"[Tool Calling] 工具執行完畢\n"}, ensure_ascii=False)}\n\n"             
                        
                # 2. 捕捉到 LLM 的「純文字」輸出，讓前端能以「串流」的方式顯示回覆
                elif event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                    if event.data.delta:
                        full_response_text += event.data.delta  # 一小段回應組裝
                        # 即時將文字傳送給前端
                        yield f"data: {json.dumps({'type': 'llm_generate', 'content': event.data.delta}, ensure_ascii=False)}\n\n"
            
            # 對話結束
            if full_response_text:
                self.chat_repo.create_message(session_id, "assistant", full_response_text)

            yield f"data: {json.dumps({'type': 'done'})}\n\n"  # 讓前端知道完成了
        
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"[系統錯誤]: {error_traceback}")
            print(f"Agent Error: {e}")
            # 避免 API 錯誤導致整個聊天室崩潰，還是要回傳訊息
            yield f"data: {json.dumps({'type': 'error', 'content': f'抱歉，GentleCoach 大腦暫時短路了，請稍後再試'})}\n\n"
        
        finally:
            current_image_ctx.reset(token)
