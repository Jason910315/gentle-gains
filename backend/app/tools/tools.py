from typing import Counter, Dict, List, Any, Optional, Literal
from agents import function_tool
from app.data.repositories import WorkOutRepository, FoodRepository
from app.data.schema import WorkoutLogRequest
from app.services.ai_service import OpenAIService
from app.services.context import current_image_ctx  # 去共用的 context.py 拿 current_image_ctx
from app.services.google_manager import GoogleManager
from datetime import datetime, timezone, timedelta
from supabase import create_client, Client
import json, os, traceback
from tavily import TavilyClient

# 可以聯網搜尋的工具
tavily_client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))

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
        return "[工具調用失敗]：寫入失敗，請告訴使用者提供的訓練數據格式不合理。"
    except Exception as e:
        print(f"[系統錯誤]: {e}")
        return "[工具調用失敗]：寫入資料庫失敗，請告知使用者系統發生內部錯誤，稍後再試。"

@function_tool
def get_workout_analytics(days: int, 
                        body_parts: Optional[List[Literal["胸部", "背部", "腿部", "肩膀", "手臂", "核心"]]] = None,  # Optional 可選填，不限定只能一種
                        ) -> str: # 回傳的字串，給 LLM 讀的
    """
    查詢使用者過往的健身記錄，可以根據天數、部位、進行精細查詢，查詢完畢後，會自動分析使用者的訓練狀況，並給出建議。
    參數：
        days: 查詢的天數，若使用者並未給予天數參數，則預設為 7 天，若使用者問「最近」，代入 7，若問「這個月」，帶入 30。
        body_part: (選填) 欲查詢的部位，可多選，若未指定，則代表查詢全部部位，必須自動將使用者口語化的部位（如：練胸、胸肌）歸類到選項中。
    """
    print(f"⚙️ [Tool 執行] get_workout_analytics: 查詢最近 {days} 天，部位={body_parts}")
    try:
        # 查詢特定條件的健身記錄，目前還是 UTC
        db_records = workout_repo.get_filtered_workouts(
            days=days,
            body_parts=body_parts
        )
        if not db_records:
            return "[工具調用失敗]: 資料庫回傳空陣列，請告訴使用者過去 {days} 天內沒有符合條件的健身記錄。"

        unique_days = set()  # 有可能同一天有多筆訓練紀錄，我們會想知道範圍內哪幾天有訓練的
        part_counter = Counter()  # 計算各部位的訓練次數

        exercise_data = {}  # ex: {"深蹲": {"weights": [60, 62], "reps": [10, 8], "volumes": [600, 496]}}

        workout_raw_list = []
        
        for row in db_records:
            dt = row["created_at"]
            unique_days.add(dt.split('T')[0])  # 同一天的訓練只記一次   
            part = row["body_part"]
            part_counter[part] += 1  # 記該部位練了幾次
            name = row["exercise_name"]
            w ,s, r = row["weight"], row["sets"], row["reps"]
            volume = w * s * r  

            # 這是之後要給 LLM 看的返回 (關於所有查詢到的記錄)
            workout_raw_list.append({
                "日期": format_utc_to_tw_time(dt),
                "動作": name, "部位": part, "數據": f"{w}kg x {s}組 x {r}下"
            })

            # 要將同個動作的的不同時間訓練串在一起，這樣就可以知道多次訓練的進步幅度
            if name not in exercise_data:
                exercise_data[name] = {"weights": [], "sets": [], "reps": [], "volume": []}
            exercise_data[name]["weights"].append(w)
            exercise_data[name]["sets"].append(s)
            exercise_data[name]["reps"].append(r)
            exercise_data[name]["volume"].append(volume)

        progress_highlights = []  # 記錄動作的進步狀況，給 LLM 看的

        # 一個動作一個動作判斷
        for name, metrics in exercise_data.items():
            if len(metrics["weights"]) < 2:  # 至少要有兩次訓練才能算進步
                continue

            # 如何判斷有無進步: 將使用者給的時間範圍內的記錄，取前半段和後半段，比較
            mid = len(metrics["weights"]) // 2   # (取整，5 // 2 = 2)

            # 輔助: 判斷 key 這個值的進步幅度
            def get_imp(key):
                past = sum(metrics[key][:mid]) / mid  # 前半段的平均
                recent = sum(metrics[key][mid:]) / (len(metrics[key]) - mid)  # 後半段的平均
                return recent - past

            imp_w = get_imp("weights")
            imp_s = get_imp("sets")
            imp_r = get_imp("reps")
            imp_v = get_imp("volume")

            # 開始判斷所有數據有無進步
            if imp_w > 0:
                progress_highlights.append({"動作": name, "類型": "重量提升", "進步": f"+{imp_w:.1f}kg"})
            if imp_s > 0:
                progress_highlights.append({"動作": name, "類型": "組數提升", "進步": f"+{imp_s:.1f}組"})
            if imp_r > 0.5:  # 次數提升至少要 0.5 下才能算進步
                progress_highlights.append({"動作": name, "類型": "次數提升", "進步": f"+{imp_r:.1f}下"})
            if imp_v > 50:
                progress_highlights.append({"動作": name, "類型": "總量突破", "進步": f"+{imp_v:.1f}kg"})

       # 結構化最後的結果，要返回給 LLM 看的
        analytics = {
            "workout_raw_data": workout_raw_list,
            "summary_stats": {
                "total_days": len(unique_days),  # 這是使用者給的特定 days 內的訓練天數
                "weekly_frequency": f"{len(unique_days) / (days/7):.1f}次",
                "part_distribution": {k: f"{(v/len(db_records))*100:.1f}%" for k, v in part_counter.items()},
                "progress_highlights": progress_highlights
            }
        }
        
        return f"[Tool Output]: {json.dumps(analytics, ensure_ascii=False)}"
    
    except Exception as e:
        print(f"[系統錯誤]: {e}")
        return "[工具調用失敗]：查詢健身記錄失敗，請告知使用者系統發生內部錯誤，稍後再試。"

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
            return "[工具調用失敗]：未找到圖片網址，請告知試著重新傳送圖片。"

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
        return "[工具調用失敗]：分析飲食圖片或寫入資料庫失敗，請告知使用者系統發生內部錯誤，稍後再試。"


@function_tool
async def create_calendar_event(summary: str, start_time: str, user_id: str = "tester_01", duration_minutes: int = 60) -> str:
    """
    當使用者想要「預約」、「安排」、「約定」任何未來的行程（健身、吃飯、上課等）時，必須呼叫此工具。
    這是系統唯一的日曆寫入管道。禁止對使用者說你「無法安排」或「請手動設置」。 
    參數:
        summary: 行程的簡短標題 (例如：去學校、練背)。
        start_time: 開始時間。必須轉為 ISO 8601 格式 (YYYY-MM-DDTHH:MM:SS)，注意：如果你不知道今天的日期，請參考系統當前時間或詢問使用者。
        user_id: 使用者的唯一識別碼。
        duration_minutes: 持續分鐘數，若使用者未提供，則預設為 60 分鐘。
    【重要輸出規則】：
    若此工具回傳包含「http」開頭的連結，你必須『逐字』將該連結呈現給使用者。
    """
    try:
        gm = GoogleManager(user_id)
        # 建立可以操作"該使用者"行事曆的物件
        calendar = gm.get_service('calendar', 'v3')

        # 首次操作 google 服務要先授權
        if not calendar:
            return f"[工具調用失敗]: 需要使用者進行操作，使用者尚未連結 Google 日曆權限。請告知使用者點擊此連結完成授權，否則無法建立行程**[👉 點擊此處連結進行授權](http://localhost:8000/api/v1/auth/google/login)**"
        
        print(f"⚙️ [Tool 執行] create_calendar_event: 正在建立行程 '{summary}'")
        start_dt = datetime.fromisoformat(start_time)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        # 包裝成 API 呼叫的 body 格式
        event = {
            'summary': summary,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'Asia/Taipei'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'Asia/Taipei'},
        }

        # 新增行程 (primary 代表要操作使用者的主要日曆)
        result = calendar.events().insert(calendarId='primary', body=event).execute()
        return f"[Tool Output]✅ 行程已建立！名稱：{summary}，連結：[點我查看]({result.get('htmlLink')})"

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(f"[系統錯誤]: {error_traceback}")
        return f"[工具調用失敗]：建立行程失敗，請告知使用者系統發生內部錯誤，稍後再試。"

@function_tool
def web_search(query: str) -> str:
    """
    當使用者詢問關於健身科學、營養研究、健身動作細節、補給品等等任何關於健身營養的問題，或是任何 AI 知識庫可能過時的即時資訊時，
    呼叫此工具進行聯網搜尋。
    參數:
        query: 搜尋關鍵字，請將使用者的問題轉化為適合搜尋引擎的關鍵字(例如:「肌酸服用時間建議」)。
    """
    if not tavily_client:
        return f"[工具調用失敗]: 系統尚未配置 Tavily API 金鑰，無法進行聯網搜尋。"
    
    try:
        print(f"🌐 [Tool 執行] web search: 正在搜尋 '{query}'")

        response = tavily_client.search(
            query=query,
            search_depth="advanced",   # 會掃描更多高質量的網站
            max_results=3,             
            include_answer=True   # 根據搜尋到的多個網頁內容，讓 Tavily 先幫忙總結一個簡答
        )

        # 整理搜尋結果給 LLM 看，這個結果可能有多個網站的資訊
        search_results = []

        # 若 Tavily 有提供答案則優先放入
        if response.get("answer"):
            search_results.append(f"【核心答案】: {response['answer']}\n")
        
        # 遍歷多個網站的搜尋結果，使用更直觀的標籤
        for i, result in enumerate(response.get("results", []), 1):
            search_results.append(
                f"--- 來源 {i} ---\n"
                f"網站標題: {result['title']}\n"
                f"網址連結: {result['url']}\n"
                f"內容內容: {result['content']}\n"
            )
            
        final_output = "\n".join(search_results)

        if not final_output:
            return "[工具調用失敗]: 搜尋不到相關結果，請試著更換提問方式。"
        
        # 強制 AI 如何「引用」的關鍵 Meta-prompt
        meta_prompt = (
            "\n\n[指令: 請根據上述資訊回答，並嚴格遵守以下格式規範：\n"
            "1. 你的回答正文應保持專業且溫暖，可以不用在正文中嵌入連結。\n"
            "2. **在回覆內容的最後**，必須新增一個標題為『### 參考來源』的區塊。\n"
            "3. 在該區塊中，請以列表形式顯示你參考的所有網站真實網址，可以讓使用者點擊跳轉到該網站。\n"
            "4. 範例：『- 肌酸補充指南：[https://example.com/creatine-guide](https://example.com/creatine-guide)』。]\n"
        )
        return f"[Tool Output]: \n\n{final_output}{meta_prompt}"
    
    except Exception as e:
        print(f"[聯網搜尋錯誤]: {e}")
        return f"[工具調用失敗]: 聯網搜尋時發生錯誤，請稍後再試。"


# 將所有 tools 打包成一個 list，給 AI 讀取
AGENT_TOOLS = [log_workout, get_workout_analytics, log_food_record, create_calendar_event, web_search]
        
        