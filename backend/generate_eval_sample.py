from datetime import datetime
import json, os, time
from typing import List, Dict, Any
from openai import OpenAI
from langsmith import Client
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
ls_client = Client()

def load_eval_examples(file_path: str) -> List[Dict[str, Any]]:
    """讀取本地評估範例 JSON 資料集"""
    if not os.path.exists(file_path):
        print(f"找不到本地範例檔案: {file_path}，請先建立")
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_more_examples(eval_examples: List[Dict[str, Any]], n: int = 10) -> List[Dict[str, Any]]:
    """使用 GPT-4o 根據評估範例擴展更多資料"""

    # 原始的 golden_dataset
    eval_str = json.dumps(eval_examples, ensure_ascii=False, indent=2)

    prompt = f"""你是一位 AI Agent 測試工程師，專門為健身 AI 教練 'GentleCoach' 產生評估資料集。
    以下是現有的評估範例 (Eval Examples)，涵蓋基本問答、工具調用、多輪對話、邊界陷阱題與複雜推理：

    {eval_str}

    請根據這些範例的風格、多樣性與複雜度，額外產生 {n} 組新的資料。
    要求：
    1. **結構完全一致**：每筆資料必須包含頂層欄位 "id"、"inputs"、"outputs"，格式如下：
       - **id**：格式為 "GD-XXX"，編號從現有資料集最大 id 後面接續往下排。
       - **inputs**：必填 "user_query"；若需要圖片則加 "image_url"；若是多輪對話則加 "conversation_history"（陣列，每項含 "role" 與 "content"）。
       - **outputs 依 test_type 分兩種結構**：
         - **test_type "positive"（Agent 應正常回答或呼叫工具）**：
           {{"expected_tools": ["<工具名>"] 或 [], "expected_args": {{...}}（只在有工具時加入）, "test_type": "positive", "category": "<細分類>", "intent": "...", "difficulty": "<難度>", "reference_response": "..."}}
         - **test_type "negative"（Trap，Agent 不應呼叫工具）**：
           {{"expected_tools": [], "test_type": "negative", "category": "<細分類>", "intent": "...", "difficulty": "<難度>", "reasoning": "解釋為何不應呼叫工具", "reference_response": "..."}}
       注意：
         - expected_tools 一律為陣列，不呼叫工具時填 []，不可為 null。
         - test_type 為 "negative" 時不得含 expected_args，必須含 reasoning。
         - test_type 為 "positive" 且有工具時才加 expected_args，無工具的 positive 案例不加 expected_args。
         - reference_response 在所有類型中均為必填。
    2. **category 細分類型**（從以下選擇，按情境選最合適的）：
       - "basic_qa" — 基礎健身/營養知識問答，不需呼叫工具
       - "tool_use" — 明確需要呼叫特定工具
       - "multi_turn" — 多輪對話，需理解前文脈絡
       - "boundary" — 邊界陷阱題，看起來像需要工具但實際不應呼叫
       - "complex_reasoning" — 複雜推理，需整合多個面向給出深入分析
    3. **difficulty 難度**：依問題複雜度填入 "easy"、"medium" 或 "hard"。
    4. **圖片網址規範**：若 inputs 中包含 image_url，請務必統一使用 `https://gcwpcyivbfwhombmwbud.supabase.co/storage/v1/object/public/food_images/food_images/1774161197360-vn5obuv8gab.jpg`，不要自行虛構網址。
    5. **多樣性**：
        - 涵蓋不同 category 與 difficulty，不要所有資料集中在同一類型。
        - 產生新的動作記錄（如：引體向上、硬舉、波比跳、肩推）。
        - 產生多輪對話案例，conversation_history 需與 user_query 有連貫脈絡。
        - 產生更口語、甚至帶有情緒的對話內容。
    6. **工具清單**（expected_tools 只能填以下工具名稱）：record_workout_exercise、analyze_workout_progress、record_food_intake_with_vision、web_search、schedule_appointment。
    7. **格式要求**：只回傳純 JSON 陣列格式，不要包含 Markdown 的 ```json 標籤，也不要任何解釋文字。

    請開始生成："""

    print(f"🚀 正在使用 GPT-4o 擴展 {n} 筆新資料...")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "你是一個專業的 JSON 資料生成器。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8
        )

        raw_content = response.choices[0].message.content.strip()
        # 移除可能存在的 Markdown 標籤
        if raw_content.startswith("```"):
            raw_content = raw_content.split("\n", 1)[1].rsplit("\n", 1)[0]

        new_data = json.loads(raw_content)
        return new_data
    except Exception as e:
        print(f"❌ 生成失敗: {e}")
        return []

def main():
    # 讀取範例
    eval_file = "golden_dataset_v2.json"
    eval_examples = load_eval_examples(eval_file)
    if not eval_examples:
        return

    # 擴展資料 (例如產生 30 筆，加上原本 20 筆湊齊 50 筆)
    new_examples = generate_more_examples(eval_examples, n=2)

    if not new_examples:
        print("未生成任何新資料。")
        return

    # 合併新舊資料
    final_dataset = new_examples
    print(f"✅ 擴展完成，目前共有 {len(final_dataset)} 筆資料。")

    # 儲存擴展後的資料到本地 (備份)
    output_file = "full_eval_dataset.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(final_dataset, f, ensure_ascii=False, indent=2)
    print(f"💾 已儲存完整資料集至 {output_file}")

    # 上傳至 LangSmith
    today_time = datetime.now().strftime("%Y%m%d-%H%M%S")
    dataset_name = f"GentleCoach_Eval_{today_time}"
    print(f"📤 正在上傳至 LangSmith 資料集: {dataset_name}...")

    try:
        dataset = ls_client.create_dataset(
            dataset_name=dataset_name,
            description="GentleCoach 健身教練評估資料集 (自動擴展版)"
        )

        for example in final_dataset:
            ls_client.create_example(
                inputs=example["inputs"],
                outputs=example["outputs"],
                dataset_id=dataset.id
            )

        print(f"🎉 成功！請前往 LangSmith 平台查看資料集。")
    except Exception as e:
        print(f"❌ 上傳 LangSmith 失敗: {e}")

if __name__ == "__main__":
    main()
