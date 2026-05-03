// Vercel 會去讀環境變數裡面叫做 NEXT_PUBLIC_API_URL 的值，若是本機開發則用預設的 127.0.0.1:8000
export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"