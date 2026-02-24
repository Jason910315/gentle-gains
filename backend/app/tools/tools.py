from typing import Dict, List, Any, Optional, Literal
from agents import function_tool
from app.data.repositories import WorkOutRepository, FoodRepository
from app.data.schema import WorkoutLogRequest
from pydantic import Field
import traceback

workout_repo = WorkOutRepository()
food_repo = FoodRepository()

# --- Define Tools ---
@function_tool
def log_workout(exercise_name: str, body_part: Literal["胸部","背部","腿部","肩膀","手臂","核心"], weight: float, sets: int, reps: int) -> str:
    """
    當使用者提到他們完成某項訓練動作，或提及記錄訓練動作，呼叫此工具將數據寫入資料庫。
    參數:
        exercise_name: 訓練動作名稱。請「絕對保留」使用者原本輸入的原始語言與字詞，絕對不要自行翻譯成英文。
        body_part: 訓練部位，請根據使用者的描述（如：胸肌、練胸、推胸），自動歸類並映射到最符合的部位選項。
    """
    try:
        print(f"⚙️ [Tool 執行] log_workout: {body_part} - {exercise_name} {weight}kg")

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

@function_tool
def get_recent_workouts(days: int, 
                        body_part: Optional[Literal["胸部", "背部", "腿部", "肩膀", "手臂", "核心"]] = None,  # Optional 可選填，若不是六種之一，可以是 None
                        exercise_name: Optional[str] = None) -> str:
    """
    查詢使用者過往的健身記錄，可以根據天數、部位、或特定動作進行精細查詢。
    參數：
        days: 查詢的天數 (預設為 7 天，若使用者問「最近」，代入 7，若問「這個月」，帶入 30)。
        body_part: (選填) 限定查詢的訓練部位，若未指定，則忽略 (Null)。
        exercise_name: (選填) 限定查詢的特定訓練動作，請保留使用者輸入的中文動作名稱
    """
    print(f"⚙️ [Tool 執行] get_recent_workouts: 查詢最近 {days} 天，部位={body_part}，動作={exercise_name}")

# 將所有 tools 打包成一個 list，給 AI 讀取
AGENT_TOOLS = [log_workout]
        
        