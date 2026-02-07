import os
from openai import OpenAI
from app.schema import FoodAnalysisResult, AnalyzeRequest
from dotenv import load_dotenv
import traceback

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class OpenAIService:
    @staticmethod
    def analyze_food_image(base64_image: str, food_name: str, meal_type: str) -> FoodAnalysisResult:  # 強制回傳格式
        """
        發送圖片給 GPT-4o 進行分析，強制回傳 FoodAnalysisResult 物件
        """
        # 若圖片字串前綴帶有 base64，要先清除前面的所有字串，避免重複
        if "base64," in base64_image:
            base64_image = base64_image.split("base64,")[1]
            
        system_prompt = """
            你是一位專業的台灣營養師與健身教練。你的專長是視覺化營養估算。
            你的任務是從使用者的食物照片中，精準估算營養成分。
            ⚠️ 特別注意：請不要將**熱量**與**蛋白質**估得太高。

            ## 分析步驟
            請在輸出 JSON 之前，先在腦中進行以下推理步驟：
            1. **識別食物**：辨識盤中的每一項食材（例如：白飯、炸雞腿、炒高麗菜）。
            2. **估算份量**：根據你所能觀察到的食物的大小 (被遮擋的部分請不要過度猜測大小，以保守為主)，推估每項食材的重量（公克）。
            3. **對照資料庫**：參考常見連鎖餐廳網路上的數據，例如麥當勞套餐大約在 400~700 大卡，除非是多人分享餐，否則不太可能超過 1000 大卡
            4. **計算總和**：將所有食材的營養加總。
            5. 請給出簡短的飲食建議 (約 50~80 字)

            ## 估算準則
            1. **請就照片中能觀察到的各項食物的大小去進行推算，若被遮擋的部分請不要過度猜測大小，大小會重點影響營養素多寡**
            2. **保守原則**：如果無法確定，請給出一個合理的範圍平均值，不要過度高估。
            
            ## 評分準則
            使用者目標為「增肌」，評分邏輯如下 (0-5分)：
            - **高分關鍵**：高蛋白質是首要條件，總熱量足夠 (不低於 500 kcal)。
            1. **熱量過低** (例如 < 400 kcal)：無法支持增肌，視為不合格。
            2. **蛋白質或碳水不足** (例如 < 20g)：無法修復肌肉。

            請嚴格遵守 JSON 格式輸出。
        """

        user_prompt = f"""
        這是一張飲食照片，食物名稱是：『{food_name}』。
        請執行以下分析：請分析其熱量、蛋白質、碳水與脂肪，並給出評分與整體建議。
        """

        try:
            # Strutured output 可以確保回傳格式一致
            completion = client.beta.chat.completions.parse(
                model="o3",  # 支援 Strutured Output 的最新模型
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content":[
                            # image process 的固定格式
                            {
                                "type": "text", 
                                "text": user_prompt
                            },
                            {
                                "type": "image_url",
                                "image_url":{
                                    "url": f"data:image/jpeg:base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ],
                response_format=FoodAnalysisResult,  # 強制回傳 FoodAnalysisResult 物件
            )
            result = completion.choices[0].message.parsed
            return result  # 這個 result 會是 FoodAnalysisResult 物件 (有被強制輸出格式)
        except Exception as e:
            error_traceback = traceback.format_exc()
            print(f"AI 分析圖片失敗，OpneAI API error: {error_traceback}")
            raise e

        