import os, json, traceback, asyncio
from datetime import datetime
from openai.types.responses import ResponseTextDeltaEvent
from app.data.repositories import ChatRepository
from app.services.context import current_image_ctx
from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from app.tools import tools
from typing import Dict, List, Any
from langsmith.wrappers import wrap_openai
from langsmith.run_trees import RunTree
from langsmith.run_helpers import tracing_context
from app.services.agent_instructions import get_agent_instructions

class AgentService:
    def __init__(self):
        # 用 wrap_openai 包裝 client，讓他攔截所有經過這個 client 的 OpenAI API 呼叫
        self.async_client = wrap_openai(
            AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))  # AsyncOpenAI 是建立非同步版本，比較適合 stream
        )
        self.chat_repo = ChatRepository()  # 查詢歷史對話記錄的工具

    async def chat_stream(self, session_id: str, user_query: str, image_url: str | None = None):
        """
        處理對話的核心流程：存訊息 -> 撈歷史 -> 交給 Runner 處理 -> 存回覆，並可以使用 Local 的工具
        """
        now_str = datetime.now().strftime("%Y-%m-%d (%A)") # 例如：2026-03-08 (Sunday)
        print(f"🕒 系統時間：{now_str}")

        # RunTree 像是追蹤的根節點，可以追蹤整個對話流程 (把這一次完整的聊天流程，視為一條 chain)
        rt = RunTree(
            name="GentleCoach_Chat_Flow",
            run_type="chain",    # 告訴 LangSmith 這是一個「串聯流程」
            inputs={
                "user_query": user_query
            },
            project_name=os.environ.get("LANGSMITH_PROJECT")
        )

        # 這個實例要讓 Agent 使用，否則 Agent 會自己建立一個新的
        agent_model = OpenAIChatCompletionsModel(
            model="gpt-4o",
            openai_client=self.async_client  # 傳入已經 wrap_openai，確保所有 LLM 呼叫都會被蹤到
        )

        # 建立 Agent 實例，並將 tools 掛載上去 (要放在函式內，這樣每次對話都可以抓到最新的 now_str)
        coach_agent = Agent(
            name="GentleCoach",
            instructions=get_agent_instructions(now_str),
            tools=tools.AGENT_TOOLS,
            model=agent_model  # 掛載
        )
        try:
            # 將網址注入到此 COntextVar 變數，只要整個非同步還沒結束，contextvar 就不會消失，工具調用時也還在非同步，所以可以直接抓 
            token = current_image_ctx.set(image_url)

            # 存入「當下」的使用者訊息
            self.chat_repo.create_message(session_id, "user", user_query, image_url)
            # 撈取歷史對話記錄，這裡會由最舊的對話開始往後走 (最多50筆)
            chat_history = self.chat_repo.get_recent_messages(session_id, limit=50)

            # 轉換為多模態格式 (這裡之所以不用加入當下的 query 是因為前面已經將它存到歷史訊息了)
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
            
            # 在這個 with block 裡面發生的所有追蹤，父節點都是 rt
            with tracing_context(parent=rt):
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
                            content = f'[Tool Use] 正在呼叫 {tool_name}，參數: {tool_args}\n\n'

                            full_response_text += content  # 這樣讓工具調用過程也存入資料庫
                            # 通知前端：正在執行工具 (轉成 JSON 方便前端解析，開頭與結尾加上 data: /n/n 是 SSE 的通訊格式)
                            yield f"data: {json.dumps({'type': 'tool_calling', 'content': content}, ensure_ascii=False)}\n\n"
                        elif event.item.type == "tool_call_output_item":
                            tool_output_string = event.item.output   # tool function 回傳的結果
                            print(f"📦 [工具回傳]: {tool_output_string}")
                            if tool_output_string.startswith("[工具調用失敗]"):
                                full_response_text += f"[Tool Use] 工具執行失敗，請稍後在試\n\n"
                                # 通知前端：工具執行失敗，使用 \n\n 確保 Markdown 換行
                                yield f"data: {json.dumps({'type': 'tool_output', 'content': f'[Tool Use] 工具執行失敗，請稍後在試\n\n'}, ensure_ascii=False)}\n\n"
                            else:
                                full_response_text += f"[Tool Use] 工具執行完畢\n\n"
                                # 通知前端：工具執行完畢，使用 \n\n 確保 Markdown 換行
                                yield f"data: {json.dumps({'type': 'tool_output', 'content': f'[Tool Use] 工具執行完畢\n\n'}, ensure_ascii=False)}\n\n"             
                            
                    # 2. 捕捉到 LLM 的「純文字」輸出，讓前端能以「串流」的方式顯示回覆
                    elif event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                        if event.data.delta:
                            full_response_text += event.data.delta  # 一小段回應s組裝
                            # 即時將文字傳送給前端
                            yield f"data: {json.dumps({'type': 'llm_generate', 'content': event.data.delta}, ensure_ascii=False)}\n\n"
                
                # 對話結束
                if full_response_text:
                    self.chat_repo.create_message(session_id, "assistant", full_response_text)

                yield f"data: {json.dumps({'type': 'done'})}\n\n"  # 讓前端知道完成了
            
            rt.end(outputs={"output": full_response_text}, metadata={"session_id": session_id, 'image_url': image_url, 'system_time': now_str})   # 結束整個流程，並存入 outputs
            rt.post()    # 真正結束，上傳到伺服器存檔
        
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"[系統錯誤]: {error_traceback}")
            print(f"Agent Error: {e}")

            rt.end(outputs={"output": f"Error: {error_traceback}"}, metadata={"session_id": session_id, 'image_url': image_url, 'system_time': now_str})
            rt.post()

            # 錯誤訊息也要存到資料庫
            self.chat_repo.create_message(session_id, "assistant", f"抱歉，GentleCoach 大腦暫時短路了，請稍後再試，或聯絡開發者 a0938692163@gmail.com")
            # 避免 API 錯誤導致整個聊天室崩潰，還是要回傳訊息
            yield f"data: {json.dumps({'type': 'error', 'content': f'抱歉，GentleCoach 大腦暫時短路了，請稍後再試，或聯絡開發者 a0938692163@gmail.com'})}\n\n"
        
        finally:
            current_image_ctx.reset(token)
