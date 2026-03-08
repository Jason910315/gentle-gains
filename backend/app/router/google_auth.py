from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow
from supabase import create_client, Client
import os, datetime, traceback
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

router = APIRouter(prefix="/api/v1/auth/google", tags=["Google Auth"])

# 我的 google oauth2 憑證位址
current_file = Path(__file__).resolve()
BASE_DIR = current_file.parent.parent
CREDENTIALS_PATH= os.path.join(BASE_DIR, "AI_playground_jason_gentlegains.json")

REDIRECT_URI = "http://localhost:8000/api/v1/auth/google/callback"  # 這個要跟 google 設定的 redirect uri 一樣

# 可被操作的服務
GOOGLE_SCOPES = os.getenv("GOOGLE_SCOPES").split()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# 為每個使用者產生 google 的授權網址
@router.get("/login")
async def google_login(request: Request):
    # Flow 負責處理應用程式與 Google 認證伺服器之間的認證，並可以操作授權流程
    flow = Flow.from_client_secrets_file(
        CREDENTIALS_PATH,
        scopes=GOOGLE_SCOPES
    )
    flow.redirect_uri = REDIRECT_URI

    # 產生要讓使用者點擊的授權網址，這個網址會帶有 code 參數，可以換取 access_token 和 refresh_token
    auth_url, state = flow.authorization_url(prompt='consent', access_type='offline')

    # 存入 Session
    request.session['oauth_state'] = state
    # SDK 會自動生成 code_verifier，我們必須把它也存起來
    request.session['code_verifier'] = flow.code_verifier

    # 讓使用者可以直接看到授權畫面 
    return RedirectResponse(url=auth_url)

# 使用者同意後，會導向此 callback，接收 code 並換取長期的 access_token
@router.get("/callback")
async def google_callback(request: Request, code: str, state: str):
    try:

        # 1. 檢查 callback 帶來的 state 是否與當初產生的 state 一致 (防禦攻擊)
        saved_state = request.session.get('oauth_state')
        if not saved_state or state != saved_state:
            raise HTTPException(status_code=400, detail="State 驗證失敗或 Session 已過期")

        # 2. 拿回當初的 code_verifier
        saved_verifier = request.session.get('code_verifier')

        flow = Flow.from_client_secrets_file(
            CREDENTIALS_PATH, 
            scopes=GOOGLE_SCOPES, 
            state=saved_state
        )
        flow.redirect_uri = REDIRECT_URI

        # 去換取 access_token 和 refresh_token
        flow.fetch_token(code=code, code_verifier=saved_verifier)  
        creds = flow.credentials

        if not creds.refresh_token:
            return {"error": "取得 refresh_token 失敗，請至 Google 帳號設定移除權限後重試。"}

        data = {
            "user_id": "tester_01",
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "updated_at": datetime.datetime.now().isoformat()
        }

        # 如果 user_id 存在就更新，不存在就新增
        supabase.table("user_oauth_tokens").upsert(data).execute()

        request.session.pop('oauth_state', None)
        request.session.pop('code_verifier', None)

        # 授權完後回到對話介面，要根據你前段對話介面的網域而定
        frontend_chat_url = "http://192.168.206.1:3001/chat"
        
        # 授權完畢後要直接跳轉回對話介面
        return RedirectResponse(url=frontend_chat_url)

    except Exception as e:
        error_traceback = traceback.format_exc()
        print(error_traceback)
        raise HTTPException(status_code=500, detail=f"授權失敗: {str(e)}")
