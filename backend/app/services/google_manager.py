import os, datetime, json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# 我的 google oauth2 憑證位址
current_file = Path(__file__).resolve()
BASE_DIR = current_file.parent.parent
CREDENTIALS_PATH= os.path.join(BASE_DIR, "AI_playground_jason_gentlegains.json")

# 可被操作的服務
GOOGLE_SCOPES = os.getenv("GOOGLE_SCOPES").split()

class GoogleManager:
    """
    負責處理多個 Google API (Calendar, Gmail, etc.) 的認證與連線
    """
    def __init__(self, user_id: str):
        self.user_id = user_id  # 目前要使用 google 服務的那個人
        self.supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        self.client_config = self._load_client_config()  # 這個是 gentle-gains 網頁程式的憑證，不是使用者的
        self.creds = self._load_and_refresh_credentials()  # 使用者的 token
        
    # 讀取 json 憑證內的內容
    def _load_client_config(self):
        # for railway 部署
        credentials_json = os.getenv("GOOGLE_CREDENTIALS_JSON")
        if credentials_json:
            return json.loads(credentials_json).get("web")

        # for 畚箕開發部署
        with open(CREDENTIALS_PATH, 'r') as f:
            return json.load(f).get("web")

    def _load_and_refresh_credentials(self):
        """
        從資料庫讀取 Token，並在過期時可以用 refresh_token 換取新的 access token
        """
        response = self.supabase.table("user_oauth_tokens") \
            .select("*").eq("user_id", self.user_id).single().execute()

        token_data = response.data
        if not token_data:
            print(f"Warning: No OAuth token found for user {self.user_id}")
            return None
        
        # 建立通行證，把所有資訊包裝成 Credentials 物件
        creds = Credentials(
            token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=self.client_config['client_id'],
            client_secret=self.client_config['client_secret'],
            scopes=GOOGLE_SCOPES,
        )

        # 如果 refresh_token 是這個，就代表使用者還未開通權限
        if creds and creds.refresh_token == '未開通權限':
            return None

        # 檢查 acces token 是否過期
        if creds and creds.expired and creds.refresh_token:
            print(f"Token expired, refreshing for user {self.user_id}")
            creds.refresh(Request())  # 用 refresh_token 換取新的 access token

            # 將新的資訊更新回資料庫
            self.supabase.table("user_oauth_tokens").update({
                "access_token": creds.token,
                "updated_at": datetime.datetime.now().isoformat()
            }).eq("user_id", self.user_id).execute()

        return creds

    def get_service(self, service_name: str, version: str):
        if not self.creds:
            return None
        
        # 會自動檢查 creds 物件，並返回一個能操作指定 API 的物件
        return build(service_name, version, credentials=self.creds)
