from typing import Dict, List, Any, Optional, Literal
from agents import function_tool
from app.data.repositories import WorkOutRepository, FoodRepository
from app.data.schema import WorkoutLogRequest
from pydantic import Field
from datetime import datetime, timezone, timedelta
import json

workout_repo = WorkOutRepository()
food_repo = FoodRepository()

# --- 輔助 Tools 的函式 ---

# 幫忙把 DB 的 created_at 欄位字串，轉換成台灣時間字串 (LLM 要看)
def format_utc_to_tw_time(utc_str: str) -> str:
    try:
        # Supabase 預設回傳的格式類似: "2026-02-25T02:47:08.55647+00:00"，是字串
        # 轉成 Python 感知時間物件
        utc_dt = datetime.fromisoformat(utc_str)

        # 轉換為台灣的時區時間
        tw_tz = timezone(timedelta(hours=8))
        tw_datetime = utc_dt.astimezone(tw_tz)

        # 轉成 LLM 容易讀的格式 (乾淨時間字串)
        return tw_datetime.strftime("%Y-%m-%d %H:%M:%S")

    except Exception as e:
        print(f"[時間轉換錯誤] {e}")
        return utc_str  

# --- Define Tools ---
@function_tool
def log_workout(exercise_name: str, body_part: Literal["胸部","背部","腿部","肩膀","手臂","核心"], weight: float, sets: int, reps: int) -> str:
    """
    當使用者提到他們完成某項訓練動作，或提及記錄訓練動作，呼叫此工具將數據寫入資料庫。
    參數:
        exercise_name: 訓練動作名稱。請「絕對保留」使用者原本輸入的原始語言與字詞，絕對不要自行翻譯成英文。
        body_part: 訓練部位，請根據使用者的描述（如：胸肌、練胸、推胸），自動理解語意並映射到最符合的部位選項。
    """
    try:
        print(f"⚙️ [Tool 執行] log_workout: {body_part} - {exercise_name} {weight}kg")

        # 因為 work_repo 內函式吃的是 WorkoutLogRequest 物件，所以要將參數組裝
        workout_data = WorkoutLogRequest(
            exercise_name=exercise_name,
            body_part=body_part,
            weight=weight,
            sets=sets,
            reps=reps,
        )
        
        # 將健身記錄儲存至資料庫 (呼叫 repositories 的方法)
        workout_repo.save_workout_logs(workout_data)
        return f"[Tool Output]: 已成功記錄 {body_part} 訓練 - {exercise_name}，{weight}kg，{sets}組，{reps}下。"
    except ValueError as ve:
        # 如果 Pydantic 驗證失敗，會噴出 ValueError
        print(f"[資料驗證錯誤]: {ve}")
        return "[Tool Output]：寫入失敗，請告訴使用者提供的訓練數據格式不合理。"
    except Exception as e:
        print(f"[系統錯誤]: {e}")
        return "[Tool Output]：寫入資料庫失敗，請告知使用者系統發生內部錯誤，稍後再試。"

@function_tool
def get_recent_workouts(days: int, 
                        body_part: Optional[Literal["胸部", "背部", "腿部", "肩膀", "手臂", "核心"]] = None,  # Optional 可選填，若不是六種之一，可以是 None
                        exercise_name: Optional[str] = None) -> str:
    """
    查詢使用者過往的健身記錄，可以根據天數、部位、或特定動作進行精細查詢。
    參數：
        days: 查詢的天數，若使用者並未給予天數參數，則預設為 7 天，若使用者問「最近」，代入 7，若問「這個月」，帶入 30。
        body_part: (選填) 限定查詢的訓練部位，若未指定，則忽略 (Null)，必須自動將使用者口語化的部位（如：練胸、胸肌）歸類到選項中。
        exercise_name: (選填) 限定查詢的特定訓練動作，請保留使用者輸入的中文動作名稱。
    """
    print(f"⚙️ [Tool 執行] get_recent_workouts: 查詢最近 {days} 天，部位={body_part}，動作={exercise_name}")
    try:
        # 查詢特定條件的健身記錄，目前還是 UTC
        db_records = workout_repo.get_filtered_workouts(
            days=days,
            body_part=body_part,
            exercise_name=exercise_name
        )
        if not db_records:
            return "[Tool Output]: 資料庫回傳空陣列，請告訴使用者過去 {days} 天內沒有符合條件的健身記錄。"

        # 資料清洗
        cleaned_records = []
        # db_records 是一個 list of dict
        for row in db_records:
            cleaned_row = {
                "時間": format_utc_to_tw_time(row.get("created_at")),
                "動作": row.get("exercise_name"),
                "部位": row.get("body_part"),
                "重量": f"{row.get('weight')} kg",
                "組數": row.get("sets"),
                "次數": row.get("reps")
            }
            cleaned_records.append(cleaned_row)
        
        return f"[Tool Output]: 查詢成功，以下是真實訓練資料 (以轉換為台灣時間): \n{json.dumps(cleaned_records, ensure_ascii=False)}"
    
    except Exception as e:
        print(f"[系統錯誤]: {e}")
        return "[Tool Output]：查詢健身記錄失敗，請告知使用者系統發生內部錯誤，稍後再試。"

# 將所有 tools 打包成一個 list，給 AI 讀取
AGENT_TOOLS = [log_workout, get_recent_workouts]
        
        