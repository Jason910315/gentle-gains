from pydantic import BaseModel, Field
from typing import List, Optional

"""
所有資料都需要經過以下定義驗證
"""

# --- food/add 頁面輸入或取得的資料 ---
# 定義 AI 飲食圖片分析後的輸出結構
class FoodAnalysisResult(BaseModel):
    calories: int = Field(..., description="熱量 (大卡)")
    protein: int = Field(..., description="蛋白質 (克)")
    fat: int = Field(..., description="脂肪 (克)")
    carbs: int = Field(..., description="碳水化合物 (克)")
    score: float = Field(..., description="健康評分 (0~5)")
    coach_comment: str = Field(..., description="簡短的營養評價與建議")
    # 新增推理欄位，增加分析精準度
    reasoning: str = Field(..., description="簡短說明你是如何估算的，例如：'辨識為炸雞腿便當，白飯約200 克，炸雞腿約150 克(含油)...'")
    is_saved: bool = Field(True, description="是否成功寫入資料庫")
    
# 定義前端傳進來的飲食分析請求格式 (前端頁面會輸入表單的資料)
class AnalyzeRequest(BaseModel):
    image_base64: str = Field(..., description="圖片的 Base64 字串 (不包含 data:image/... 前綴)")
    food_name: str = Field(..., description="食物的名稱，例如：牛肉麵")
    meal_type: str = Field(..., description="餐點類型，例如：早餐、午餐等")

# 前端傳來的健身記錄請求格式
class WorkoutLogRequest(BaseModel):
    exercise_name: str = Field(..., description="運動名稱")
    body_part: str = Field(..., description="訓練部位")
    weight: float = Field(..., description="重量")
    sets: int = Field(..., description="組數")
    reps: int = Field(..., description="次數")

# --- AI ChatBot 的資料 ---
class ChatRequest(BaseModel):
    """
    前端傳送一句 query + session_id (為了去資料庫抓歷史對話記錄)
    """
    session_id: str
    content: str

# 單則訊息結構 (回傳歷史記錄用)
class MessageSchema(BaseModel):
    role: str
    content: str
    created_at: Optional[str] = None  # 選填，方便前端顯示時間


# 回傳給前端的 LLM 回答
class ChatResponse(BaseModel):
    role: str
    content: str


# --- Workout Add 頁面的資料 ---

# 結尾 (移除 WorkoutLogRequest)

