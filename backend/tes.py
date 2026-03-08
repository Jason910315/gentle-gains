import os
from app.services.google_manager import GoogleManager
from dotenv import load_dotenv

load_dotenv()

def run_test():
    print("🚀 開始測試 GoogleManager...")
    
    # 1. 建立管理器實例 (請確保 Supabase 裡已有 tester_01 的資料)
    user_id = "tester_01"
    try:
        gm = GoogleManager(user_id=user_id)
        
        # 2. 嘗試獲取 Calendar 服務
        print(f"📡 正在嘗試連線 Google Calendar 服務...")
        calendar = gm.get_service('calendar', 'v3')
        
        if not calendar:
            print("❌ 失敗：無法取得服務物件，請檢查資料庫是否有 Token 資料。")
            return

        # 3. 呼叫 API：列出接下來 10 個行程
        print("🔍 正在抓取行事曆行程...")
        # 'primary' 代表使用者的主日曆
        events_result = calendar.events().list(
            calendarId='primary', 
            maxResults=10, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        if not events:
            print("✅ 連線成功！但目前行事曆中沒有任何行程。")
        else:
            print(f"🎉 成功！找到 {len(events)} 個行程：")
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(f" - [{start}] {event.get('summary', '無標題')}")

    except Exception as e:
        print(f"💥 測試過程中發生錯誤：{str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_test()