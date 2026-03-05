from typing import Dict, List, Any, Optional, Literal
from agents import function_tool
from app.data.repositories import WorkOutRepository, FoodRepository
from app.data.schema import WorkoutLogRequest
from app.services.ai_service import OpenAIService
from app.services.context import current_image_ctx  # 去共用的 context.py 拿 current_image_ctx
from pydantic import Field
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import json, os, traceback

workout_repo = WorkOutRepository()
food_repo = FoodRepository()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

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

@function_tool
def log_food_record(meal_type: str, food_name: str) -> str:
    """
    當使用者傳送圖片，並「表達」要儲存或記錄這餐飲食時才呼叫，
    如果只傳圖片且未給指令，且圖片為食物、飲食時，要詢問使用者是否要記錄分析此圖片到資料庫。
    Args:
        meal_type: 
            - 飲食時段，根據使用者給予的餐點時段判斷：必須從以下選項選擇其一：'Breakfast', 'Lunch', 'Dinner', 'Snack', 'MidnightSnack'。
            - 強制詢問：若使用者「未說明」是哪一餐，禁止猜測，請先詢問使用者。
        food_name: 食物名稱。若使用者未提供，請根據視覺分析結果自行填入（例如：牛肉麵、雞肉沙拉），但要詢問使用者名稱是否正確。
    """
    try:
        # 從 agent 內定義的 ContextVar 變數中取得圖片網址
        # 網址一定是 bucket 內存的，因為是從前端傳給後端再呼叫 chat api 的
        image_url = current_image_ctx.get()

        if not image_url:
            return "[Tool Output]：未找到圖片網址，請告知試著重新傳送圖片。"

        print(f"⚙️ [Tool 執行] log_food_record: img_url={image_url}")

        path_in_bucket = image_url.split('chat_images/')[1]

        # 從 chat_images 下載檔案內容
        file_content = supabase.storage.from_('chat_images').download(path_in_bucket)

        # 把剛剛下載的檔案 (圖片) 上傳一份到 food_images 的 bucket 上，就跟 food/add 前端操作一樣
        supabase.storage.from_('food_images').upload(
            path=path_in_bucket,
            file=file_content,
        )

        new_food_url = supabase.storage.from_('food_images').get_public_url(path_in_bucket)

        # 呼叫 AI 分析圖片
        ai_result = OpenAIService.analyze_food_image(new_food_url, food_name, meal_type)

        save_record = food_repo.save_food_logs(
            food_data=ai_result,
            image_url=new_food_url,
            food_name=food_name,
            meal_type=meal_type
        )

        ai_result_dict = ai_result.model_dump()  # pyｄantic 物件轉成 dict

        if save_record:
            return f"[Tool Output]: 已成功分析圖片，並寫入資料庫，以下是飲食分析結果:\n食物名稱：{food_name}，熱量：{ai_result_dict['calories']}大卡，蛋白質：{ai_result_dict['protein']}克，脂肪：{ai_result_dict['fat']}克，碳水：{ai_result_dict['carbs']}克，評分：{ai_result_dict['score']}分，建議：{ai_result_dict['coach_comment']}\n"
        
    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"[系統錯誤]: {error_traceback}")
        return "[Tool Output]：分析飲食圖片或寫入資料庫失敗，請告知使用者系統發生內部錯誤，稍後再試。"
        

# 將所有 tools 打包成一個 list，給 AI 讀取
AGENT_TOOLS = [log_workout, get_recent_workouts, log_food_record]
        
        