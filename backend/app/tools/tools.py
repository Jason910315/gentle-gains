from typing import Dict, List, Any
from agents import function_tool
from app.data.repositories import WorkOutRepository, FoodRepository
from app.data.schema import WorkoutLogRequest
import traceback

workout_repo = WorkOutRepository()
food_repo = FoodRepository()

# --- Define Tools ---
@function_tool
def log_workout(exercise_name: str, body_part: str, weight: float, sets: int, reps: int) -> str:
    """
    當使用者提到他們完成某項訓練動作，或提及記錄訓練動作，呼叫此工具將數據寫入資料庫。
    參數:
        exercise_name: 訓練動作名稱。請「絕對保留」使用者原本輸入的原始語言與字詞，絕對不要自行翻譯成英文。
        body_part: 訓練部位。只能從「胸部、背部、腿部、肩膀、手臂、核心」這六個詞彙中挑選一個。
    """
    try:
        print(f"⚙️ [Tool 執行] 寫入健身紀錄: {body_part} - {exercise_name} {weight}kg")

        # 將參數組裝成 WorkoutLogRequest 格式
        workout_data = WorkoutLogRequest(
            exercise_name=exercise_name,
            body_part=body_part,
            weight=weight,
            sets=sets,
            reps=reps,
        )
        
        # 將健身記錄儲存至資料庫 (呼叫 repositories 的方法)
        workout_repo.save_workout_logs(workout_data)
        return f"[Tool Output] 已成功記錄 {body_part} 訓練 - {exercise_name}，{weight}kg，{sets}組，{reps}下。"
    except ValueError as ve:
        # 如果 Pydantic 驗證失敗，會噴出 ValueError
        print(f"[資料驗證錯誤] log_workout: {ve}")
        return "[Tool Output] 系統通知：寫入失敗，請告訴使用者提供的訓練數據格式不合理。"
    except Exception as e:
        print(f"[系統錯誤] log_workout: {e}")
        return "[Tool Output] 系統通知：寫入資料庫失敗，請告知使用者系統發生內部錯誤，稍後再試。"

# 將所有 tools 打包成一個 list，給 AI 讀取
AGENT_TOOLS = [log_workout]
        
        