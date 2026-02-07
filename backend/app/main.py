from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from app.schema import AnalyzeRequest, FoodAnalysisResult
from app.ai_services import OpenAIService
from app.food_repository import FoodRepository
import traceback

app = FastAPI(title="AI Food Coach Backend")

food_repo = FoodRepository()

# 解決前後端網域不同問題
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許前端所有網域發送請求
    allow_credentials=True,  
    allow_methods=["*"],  # 允許所有方法 (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # 允許所有標頭
)

# 進行 AI 分析飲食圖片的 API 端點
@app.post(
    "/api/v1/analyze", 
    response_model=FoodAnalysisResult,
    status_code=status.HTTP_200_OK, 
    summary="AI analyze food image")
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

@app.get("/")
def health_check():
    return{"status": "ok", "message": "backend is running"}
