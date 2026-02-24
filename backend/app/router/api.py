from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List
from app.data.schema import AnalyzeRequest, FoodAnalysisResult, ChatRequest, ChatResponse, MessageSchema, WorkoutLogRequest
from app.services.ai_service import OpenAIService    # 負責 AI 圖片分析
from app.services.agent_service import AgentService  # 負責 Agent 的服務 (對話、調用工具)
from app.data.repositories import ChatRepository, WorkOutRepository, FoodRepository
import traceback

"""
這裡建立 API 的路由，並呼叫 services 的方法
"""

router = APIRouter(
    prefix="/api/v1",
    tags=["AI GentleGains API"]
)

food_repo = FoodRepository()  # 負責資料庫操作
workout_repo = WorkOutRepository()  # 負責資料庫操作
chat_repo = ChatRepository()  # 負責資料庫操作
agent_service = AgentService()  # 負責 AI 助手的實例

# --- 以下開始路由每個 API ---

@router.post("/workout", status_code=status.HTTP_200_OK, summary="Add workout log")
async def add_workout(workout_data: WorkoutLogRequest):
    try:
        response = workout_repo.save_workout_logs(workout_data)
        return response
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(error_traceback)
        raise HTTPException(status_code=500, detail=f"{error_traceback}")

# 進行 AI 分析飲食圖片的 API 端點
@router.post("/analyze", response_model=FoodAnalysisResult, status_code=status.HTTP_200_OK, summary="AI analyze food image")
async def analyze_food(request: AnalyzeRequest):   
    """
    API 主流程: 前端傳資料進來後會先驗證是否符合 AnalyzeRequest 的結構，若符合則會自動轉成 AnalyzeRequest 物件
    1. 接收前端圖片
    2. 呼叫 OpenAI 分析 (ai_service)
    3. 將分析結果寫入資料庫 (food_repository)
    4. 回傳分析結果給前端
    """
    try:
        # result 是一個 FoodAnalysisResult 物件
        ai_result = OpenAIService.analyze_food_image(request.image_base64, request.food_name, request.meal_type)

        save_record = food_repo.save_food_logs(
            food_data=ai_result,
            image_base64=request.image_base64,
            food_name=request.food_name,
            meal_type=request.meal_type
        )
        
        # 若寫入成功，save_record 會有值
        if save_record:
            ai_result.is_saved = True  # 讓前端知道資料有存進去
        else:
            ai_result.is_saved = False

        return ai_result
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(error_traceback)
        raise HTTPException(status_code=500, detail=str(error_traceback))

@router.post("/chat", status_code=status.HTTP_200_OK, summary="Chat with AI Coach (Streaming)")
async def chat_with_coach(request: ChatRequest):
    """
    AI 教練對話接口，ChatRequest 的格式是 {"session_id": "xxx", "content": "xxx"}
    """
    try:
        # 告訴瀏覽器這是 SSE 格式 (text/event-stream)，是串流傳資料進來
        return StreamingResponse(
            agent_service.chat_stream(request.session_id, request.content),
            media_type="text/event-stream"
        )
        
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail=f"{e}")


# 根據 session_id 取出歷史對話，一個 session_id 代表一個唯一的對話
@router.get("/chat/history/{session_id}", response_model=List[MessageSchema], summary="Get chat history by session_id")
async def get_chat_history(session_id: str, limit: int):
    history = chat_repo.get_recent_messages(session_id, limit=limit)
    return history

@router.get("/")
def health_check():
    return{"status": "ok", "message": "backend is running"}