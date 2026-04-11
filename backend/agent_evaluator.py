import os, asyncio, json, statistics
from datetime import datetime
from dotenv import load_dotenv
from langsmith import Client, aevaluate
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from typing import TypedDict, Annotated

from agents import Agent, Runner, AsyncOpenAI, OpenAIChatCompletionsModel
from app.tools import tools
from app.data.repositories import ChatRepository
from app.services.agent_instructions import get_agent_instructions
from openai.types.responses import ResponseTextDeltaEvent

load_dotenv()

# 定義 SLO 評估指標
# 評測結束後會比對所有 evaluator 的平均分數是否達標
AGENT_SLO = {
    "tool_selection":   0.90,   # 工具選擇正確率 ≥ 90%
    "tool_args":        0.85,   # 工具參數正確率 ≥ 85%
    "framework":        0.70,   # 框架合規分數 ≥ 70%（0~1）
}

# ──────────────────────────────────────────────
# 定義執行函數 (Run Function)
# ──────────────────────────────────────────────
# aevaluate 會把 dataset 每筆的 inputs 傳進來 run_agent() 跑
# 回傳的 dict 會成為 run.outputs，供所有 evaluator 使用
async def run_agent(inputs: dict) -> dict:
    """
    直接在評測中建立 Agent 並執行
    """
    # 取得系統時間
    now_str = datetime.now().strftime("%Y-%m-%d (%A)")
    
    # 初始化 OpenAI Client (評測時不需特別 wrap，evaluate 會自動追蹤此函式)
    async_client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    # 建立 Agent 實例，這些都與 agent_service 內建立 Agent 的模式一樣
    agent_model = OpenAIChatCompletionsModel(
        model="gpt-4o",
        openai_client=async_client
    )
    coach_agent = Agent(
        name="GentleCoach",
        instructions=get_agent_instructions(now_str),
        tools=tools.AGENT_TOOLS,
        model=agent_model
    )

    query = inputs.get("user_query", "")
    image_url = inputs.get("image_url", None)   # 可能沒有圖片
    session_id = "afc433a0-3898-4f1c-8423-934e553c716f"
    # 撈取歷史對話記錄，這裡會由最舊的對話開始往後走 (最多50筆)
    chat_history = ChatRepository().get_recent_messages(session_id, limit=50)

    # 先把歷史對話組進去，再加當次 user message
    processed_messages = []
    for msg in chat_history:
        role = msg["role"]
        text = msg["content"]
        history_image_url = msg.get("image_url")

        # 若這則訊息帶有圖片，則要傳入文字與圖片
        if history_image_url:
            processed_messages.append({
                "role": role,
                "content": [
                    {"type": "input_text", "text": text},
                    {"type": "input_image", "image_url": history_image_url},  # LLM 透過此網址看到圖片
                ]
            })
        else:
            processed_messages.append({"role": role, "content": text})
    
    processed_messages.append({"role": "user", "content": query})

    # 再把當下 user message 組進去
    if image_url:
        processed_messages.append({"role": "user", "content": [
            {"type": "input_text", "text": query},
            {"type": "input_image", "image_url": image_url}, 
        ]})
    else:
        processed_messages.append({"role": "user", "content": query})

    full_text = ""
    actual_tool_calls = []
    start_time = datetime.now()

    # 這裡也是一樣用 agent_service 內的呼叫方法
    try:
        # 使用 Runner 執行對話
        result = Runner.run_streamed(
            coach_agent,
            input=processed_messages
        )
        async for event in result.stream_events():
            if event.type == "run_item_stream_event":
                if event.item.type == "tool_call_item":
                    actual_tool_calls.append({
                        "tool": event.item.raw_item.name,
                        "args": event.item.raw_item.arguments
                    })
            elif event.type == "raw_response_event":
                if isinstance(event.data, ResponseTextDeltaEvent) and event.data.delta:
                    full_text += event.data.delta
    except Exception as e:
        print(f"[Evaluation error]: Error during agent run: {e}")

    latency = (datetime.now() - start_time).total_seconds()

    return {
        "output": full_text,
        "tool_calls": actual_tool_calls,
        "latency_seconds": latency,
    }


# 共用工具函式
def _get_outputs(run, example):
    """統一取出 run.outputs 和 example.outputs，相容物件與 dict 兩種格式"""
    run_out = run.outputs if hasattr(run, "outputs") else run.get("outputs", {}) or {}
    ex_out = example.outputs if hasattr(example, "outputs") else example.get("outputs", {}) or {}
    return run_out, ex_out

# ──────────────────────────────────────────────
# 定義 Evaluator
# ──────────────────────────────────────────────

# Evaluator A：工具選擇正確性（第一層 - 單步評估），只檢查「有沒有呼叫對的工具」，不管參數
def tool_selection_evaluator(run, example):
    run_out, ex_out = _get_outputs(run, example)

    actual_calls = run_out.get("tool_calls", [])  # tool_calls 裡面包含 tool、args
    expected_tools = ex_out.get("expected_tools", [])  

    # 預期不呼叫工具
    if not expected_tools:
        if not actual_calls:
            return {"score": 1, "comment": "✅ 正確：未調用任何工具"}
        return {"score": 0, "comment": f"❌ 錯誤：預期不調用工具，但實際調用了 {actual_calls[0]['tool']}"}

    # 預期要呼叫工具
    if not actual_calls:
        return {"score": 0, "comment": f"❌ 錯誤：預期調用 {expected_tools}，但未調用任何工具"}

    actual_tool = actual_calls[0]["tool"]
    if actual_tool == expected_tools:
        return {"score": 1, "comment": f"✅ 正確：成功調用 {expected_tools}"}
    else:
        return {"score": 0, "comment": f"❌ 錯誤：預期調用 {expected_tools}，但實際調用了 {actual_tool}"}


# Evaluator B：工具參數正確性（第一層 - 單步評估），在工具選對的前提下，進一步驗證傳入的參數是否正確
def tool_args_evaluator(run, example):
    run_out, ex_out = _get_outputs(run, example)

    actual_calls = run_out.get("tool_calls", [])
    expected_args = ex_out.get("expected_args")  # expected_args 在 dataset 裡是有多個 key 的 dict，包括所有預期參數
    expected_tools = ex_out.get("expected_tools", [])

    # 不需要呼叫工具的案例，跳過參數驗證（給滿分不影響統計）
    if not expected_tools or not expected_args:
        return {"score": 1, "comment": "➖ 跳過：此案例不需要工具參數驗證"}

    # 工具都沒調用到，參數也無從驗證
    if not actual_calls:
        return {"score": 0, "comment": "❌ 無工具調用，無法驗證參數"}

    # 取出實際傳入的參數
    try:
        actual_args_raw = actual_calls[0].get("args", "{}")
        # Agent 實際執行後返回的 args 是一個字串型別，要檢查，並轉換成 dict
        actual_args = json.loads(actual_args_raw) if isinstance(actual_args_raw, str) else actual_args_raw
    except json.JSONDecodeError:
        return {"score": 0, "comment": f"❌ 參數解析失敗：{actual_args_raw}"}

    # 逐一比對 expected_args 的每個欄位
    errors = []
    matched = []
    for key, expected_val in expected_args.items():
        actual_val = actual_args.get(key)  # 取出那個 key 對應的參數值
        if actual_val is None:
            errors.append(f"缺少欄位 `{key}`")

        # 該參數值是否是預期的
        elif str(actual_val) != str(expected_val):
            errors.append(f"`{key}` 預期 {expected_val}，實際 {actual_val}")
        else:
            matched.append(key)

    total = len(expected_args)
    score = round(len(matched) / total, 2) 

    if errors:
        return {"score": score, "comment": f"⚠️ 參數部分錯誤：{'; '.join(errors)}"}
    return {"score": 1.0, "comment": f"✅ 所有參數正確：{matched}"}


# Evaluator C：框架合規評估（第三層 - LLM-as-Judge），評估回覆是否符合 GentleCoach 的專業框架，同時對照 reference_response 給出品質分數

# 定義 judge LLM 輸出格式的模板
class FrameworkGrade(TypedDict):
    reasoning: Annotated[str, ..., "解釋為何給出此分數，需具體指出哪個框架段落有問題"] # Annotated 裡的字串是給 LLM 看的欄位說明，讓 with_structured_output 知道每個欄位代表什麼意思。
    framework_score: Annotated[int, ..., "四段式框架合規程度（0-5）：溫暖開場/數據對齊/深度洞察/教練叮嚀"]
    quality_score: Annotated[int, ..., "與 reference_response 相比的整體品質（0-5）"]
    # 最後 LLM 會輸出像 {"reasoning": "...", "score": 5} 這樣的 JSON 格式

# .with_structured_output() 強制讓輸出符合 FrameworkGrade 的格式，這裡用 Claude 模型來評估
judge_llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    api_key=os.environ.get("ANTHROPIC_API_KEY")
).with_structured_output(FrameworkGrade)
 
async def framework_evaluator(run, example):
    run_out, ex_out = _get_outputs(run, example)
 
    actual_response = run_out.get("output", "")
    reference = ex_out.get("reference_response", "")  # dataset 預期的輸出回覆
 
    if not actual_response:
        return {"score": 0, "comment": "❌ 無回覆內容"}
 
    ref_section = f"\n\n【參考回覆】（僅供品質對比，不要求完全一致）\n{reference}" if reference else ""
 
    prompt = f"""請評估 GentleCoach（健身教練 AI）的回覆品質。
 
            【四段式專業框架】
            1. 溫暖開場：以鼓勵或親切的語氣開始
            2. 數據對齊／列表：整理並回應用戶提供的具體數據
            3. 教練深度洞察：給出專業分析或建議，不只是表面回答
            4. 教練叮嚀：以激勵或提醒作結尾
            
            【實際回覆】
            {actual_response}{ref_section}
            
            評分標準：
            - framework_score：回覆涵蓋幾個框架段落？完整 4 段 = 5 分，缺 1 段 = 4 分，以此類推
            - quality_score：資訊的準確性、專業深度、與 reference_response 的品質差距"""
 
    try:
        grade = await judge_llm.ainvoke(prompt)
        # 兩個分數各佔 50% 合成最終分數，除以 10 是因為兩個分數加起來滿分為 10
        combined = round((grade["framework_score"] + grade["quality_score"]) / 10.0, 2)
        return {
            "score": combined,
            "comment": f"框架:{grade['framework_score']}/5 品質:{grade['quality_score']}/5 | {grade['reasoning']}"
        }
    except Exception as e:
        return {"score": 0, "comment": f"❌ Judge 評估失敗：{e}"}
 
 
# ──────────────────────────────────────────────
# SLO 檢查器
# 評測結束後計算各 evaluator 的指標平均分數，並透過 create_feedback 寫回 LangSmith
# ──────────────────────────────────────────────
def check_slo_and_upload(client: Client, experiment_name: str, result_list: list) -> dict:
    """
    1. result_list 是所有測評案例的結果，這裡收集各案例的 evaluator 分數
    2. 用 create_feedback 把 SLO 結果寫回 LangSmith 實驗
    3. 額外建一個 run 存 summary
    """
    # 初始化各指標的分數列表 (key 是 SLO key，value 是分數列表)
    scores: dict[str, list[float]] = {key: [] for key in AGENT_SLO}
 
    # evaluator function name → SLO key 的對應 (因為 result 取出來會是 evaluator function name)
    evaluator_key_map = {
        "tool_selection_evaluator":  "tool_selection",
        "tool_args_evaluator":       "tool_args",
        "framework_evaluator":       "framework",
    }
    # result_list 是 aevaluate 的輸出，
    # 結構為 {"run": <Run>, "example": <Example>, "evaluation_results": {...}}
    for result in result_list:  # 每一筆 result 是一個案例的評測結果
        run = result.get("run") if isinstance(result, dict) else getattr(result, "run", None)
        run_id = None
        if run:
            # 取出這個案例的 id (知道在哪個 experiment 下的哪個 run)
            run_id = str(run.id if hasattr(run, "id") else run.get("id", "")) or None
 
        # 取出來後結構為 'result':[EvaluationResult[], EvaluationResult[],...]，每個 EvaluationResult 是一個測評項目的結果
        eval_results = result.get("evaluation_results", {}) 

        # 收集這筆 run 的各 evaluator 分數
        per_run_scores: dict[str, float] = {}
        for er in eval_results.get("results", []):
            key = evaluator_key_map.get(getattr(er, "key", None))  # 取出目前這個測評項目是什麼 ("tool_selection_evaluator"...)，然後再取對應的 SLO key
            score = getattr(er, "score", None)
            if key and score is not None:
                scores[key].append(float(score))    # 所有案例
                per_run_scores[key] = float(score)  # 當前案例
 
        # 對每筆 run 打上 per-run SLO pass/fail tag
        # 只要這筆 run 有拿到分數、且 run_id 存在，就寫 feedback
        if run_id and per_run_scores:
            try:
                for slo_key, threshold in AGENT_SLO.items():
                    run_score = per_run_scores.get(slo_key)
                    if run_score is None:
                        continue  # 此 run 沒有這個 evaluator 的分數（例如跳過案例）
                    passed = run_score >= threshold   # 大於 threshold 的分數才算 pass
                    client.create_feedback(
                        run_id=run_id,     # 要寫在哪個 experiment 中的哪個 run
                        key=f"{slo_key}",  # 這個 feedback 要叫什麼
                        score=1.0 if passed else 0.0,
                        comment=f"{'✅' if passed else '❌'} {slo_key}: score={run_score:.2f} threshold={threshold}",
                    )
            except Exception as e:
                print(f"⚠️  per-run tag 寫入失敗（run_id={run_id}）：{e}")
 
    # ── 計算平均分、對比 threshold ──
    report = {}
    all_passed = True
 
    print("\n" + "=" * 52)
    print("📊 SLO 達標報告")
    print("=" * 52)
 
    for slo_key, threshold in AGENT_SLO.items():
        vals = scores.get(slo_key, [])  # score 是全部 run 的分數列表
        if not vals:
            print(f"  ➖ {slo_key:<24} 無資料")
            report[slo_key] = {"avg": None, "threshold": threshold, "passed": None}
            continue
 
        avg = round(statistics.mean(vals), 3)   # 算這個測評項目的平均分
        passed = avg >= threshold  # 大於 threshold 的平均分才算 pass
        if not passed:
            all_passed = False
 
        status = "✅" if passed else "❌"
        print(f"  {status} {slo_key:<24} avg={avg:.3f}  threshold={threshold}")
        report[slo_key] = {"avg": avg, "threshold": threshold, "passed": passed}
 
    overall_verdict = "Dataset 全部通過" if all_passed else "Dataset 有指標未達標"
    print("=" * 52)
    print(f"  整體判定：{'🎉 ' if all_passed else '⚠️  '}{overall_verdict}")
    print("=" * 52 + "\n")
 
    # ── 把 SLO 結果寫回 LangSmith ──
    # 為這次實驗建立一個 run，SLO feedback 都掛在它底下
    try:
        import uuid
        summary_run_id = str(uuid.uuid4())
 
        # 建立 summary run（type="chain" 讓它在 UI 顯示為一個獨立節點）
        client.create_run(
            id=summary_run_id,
            name="SLO Summary",  # 這個 run 節點的名稱
            run_type="chain",
            inputs={"experiment": experiment_name},
            outputs={
                "overall_passed": all_passed,
                "verdict": overall_verdict,
                "slo_report": report,
            },
            project_name=experiment_name,  # 要寫在哪個 project 底下 (在 tracing 頁面下顯示的)
        )
        client.update_run(summary_run_id, end_time=datetime.now())
 
        # 每個 SLO 指標寫一筆 feedback 到 summary run
        # score=1 代表達標，score=0 代表未達標，方便在 UI 上用顏色區分
        for slo_key, info in report.items():
            if info["avg"] is None:
                continue
            client.create_feedback(
                run_id=summary_run_id,
                key=f"{slo_key}",
                score=1.0 if info["passed"] else 0.0,
                value=f"avg={info['avg']} threshold={info['threshold']}",
                comment="✅ 達標" if info["passed"] else "❌ 未達標",
            )
 
        print(f"📤 SLO 結果已寫入 LangSmith（project: {experiment_name}）")
 
    except Exception as e:
        # SLO 上傳失敗不影響評測結果，只印警告
        print(f"⚠️  SLO 寫入 LangSmith 失敗（不影響評測）：{e}")
 
    return report
 
 
# 主程式
async def main():
    client = Client() # langsmith client
    dataset_name = "GentleCoach_Eval_20260411-185326"
    today_time = datetime.now().strftime("%Y%m%d-%H%M%S")
 
    print(f"🚀 開始完整評測（dataset: {dataset_name}）...")
 
    results = await aevaluate(
        run_agent,
        data=dataset_name,
        evaluators=[
            tool_selection_evaluator,   # A: 工具選擇
            tool_args_evaluator,        # B: 工具參數
            framework_evaluator,        # C: 框架合規（LLM-as-Judge）
        ],
        experiment_prefix=f"gentlecoach-test-{today_time}",
    )
 
    print("✅ 評測完成！正在計算 SLO...")
 
    # aevaluate 回傳的是可迭代物件，轉成 list 才能多次使用
    result_list = [r async for r in results] if hasattr(results, "__aiter__") else list(results)

    # 計算 SLO 並寫回 LangSmith（在實驗頁可直接看到達標狀況）
    experiment_name = f"gentlecoach-test-{today_time}"
    check_slo_and_upload(client, experiment_name, result_list)
 
    print("🔗 詳細結果請至 LangSmith 查看")
 
if __name__ == "__main__":
    asyncio.run(main())