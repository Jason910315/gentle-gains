from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.router import api
import traceback

app = FastAPI(title="GentlGains API endpoints")

# 解決前後端網域不同問題
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允許前端所有網域發送請求
    allow_credentials=True,  
    allow_methods=["*"],  # 允許所有方法 (GET, POST, PUT, DELETE)
    allow_headers=["*"],  # 允許所有標頭
)

# 將 api 掛載進來
app.include_router(api.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)





