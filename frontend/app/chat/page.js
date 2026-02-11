"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2 } from 'lucide-react';
import ReactMarkdown from 'react-markdown';  // 將 md 轉成人類的語言
import remarkGfm from 'remark-gfm'; // 支援表格與代碼塊

const CURRENT_SESSION_ID = "afc433a0-3898-4f1c-8423-934e553c716f" // 暫時的 session_id

export default function ChatPage() {
    const [input, setInput] = useState("");  // 使用者當前的 query
    const [isLoading, setIsLoading] = useState(false);

    // messages 代表所有對話訊息 (包含使用者和 AI 的，所以當其中一方有傳訊息，就要更新狀態，重新渲染前端)
    const [messages, setMessages] = useState([])

    const messageEndRef = useRef(null);

    // messageEndRef 連結的是最底部的 div，因此會滾動到可視底部
    const scrollToButtom = () => {
        messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // 每次 messages 變動時，會自動滾動到底部
    useEffect(() => {
        scrollToButtom();
    }, [messages]);

    // 頁面重新載入時，先去後端抓取歷史對話記錄
    useEffect(() => {
        const fetch_caht_history = async () => {
            try {
                const res = await fetch(`http://127.0.0.1:8000/api/v1/chat/history/${CURRENT_SESSION_ID}`);

                if (!res.ok) throw new Error("Failed to load chat history");

                const historyData = await res.json();

                // 後端回傳的是 [{"role": ..., "content": "..."}, {"role": ..., "content": "..."},...]，直接設定就好
                setMessages(historyData);

                // 若沒有歷史對話，則載入預設訊息
                if (historyData.length === 0) {
                    setMessages([{
                        "role": "assistant",
                        "content": "哈囉！我是你的專屬 AI 健身教練 GentleCoach，很高興為您服務！"
                    }])
                }
            }
            catch (error) {
                console.error("Failed to load chat history:", error);
                setMessages([{ "role": "assistant", "content": "無法載入歷史訊息，請稍後再試" }]);
            }
        };
        fetch_caht_history();
    }, [])  // 代表每次初始載入頁面，都要執行一次載入歷史資料 (每次回來 chat 頁面都是顯示完整對話記錄)

    // query 送出後，呼叫後端 API 進行處理 (memory 功能轉由後端處理)
    const handleSend = async () => {
        if (isLoading || !input.trim()) return;

        // 使用者第一段提問就要更新 UI 
        const userMessage = { "role": "user", "content": input };
        setMessages((prev) => [...prev, userMessage])

        const currentInput = input   // 暫存輸入內容
        setInput("");  // 送出後要清空輸入 (對話框)
        setIsLoading(true);

        try {
            const response = await fetch('http://127.0.0.1:8000/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: CURRENT_SESSION_ID,
                    content: currentInput
                }),  // 傳送 session_id 與使用者提問就好，後端會自動去抓歷史對話記錄
            });

            if (!response.ok) throw new Error("chat API Error");

            const data = await response.json()
            setMessages((prev) => [...prev, data])  // 將 AI 回傳的訊息加入到 messages 陣列中
        }
        catch (error) {
            console.error("Chat API Error:", error)
            setMessages((prev) => [...prev, { "role": "assistant", "content": "抱歉，GentleCoach 大腦暫時短路了，請稍後再試" }])
        }
        finally {
            setIsLoading(false)
        };
    };


    return (
        <div className="flex flex-col h-screen bg-gray-50">
            {/* Header */}
            <header className="bg-white px-6 py-4 shadow-sm border-b flex items-center gap-3 sticky top-0 z-10">
                <div className="bg-orange-100 p-2 rounded-full">
                    <Bot className="text-orange-500" size={24} />
                </div>
                <div>
                    <h1 className="text-xl font-bold text-gray-800">GentleGains AI</h1>
                    <p className="text-xs text-gray-500">你的專屬健身教練</p>
                </div>
            </header>

            {/* 對話區域 */}
            <main className="flex-1 overflow-y-auto space-y-4 p-6">

                {/* 把每一條訊息遞迴顯示在對話框中，才不會只顯示最新的那筆 (包含使用者和 AI 的) */}
                {messages.map((msg, index) => (
                    <div
                        key={index}
                        // 如果是 user 就反轉，讓使用者的訊息在右邊
                        // 預設 (機器人)：順序是 [頭像][訊息框]，靠左對齊
                        className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                    >
                        {/* 頭像 */}
                        <div className={`
                            w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0
                            ${msg.role === 'user' ? 'bg-gray-800 text-white' : 'bg-white border text-orange-500'}
                        `}>
                            {/* 角色顯示不同的頭像 */}
                            {msg.role === 'user' ? <User size={16} /> : <Bot size={16} />}
                        </div>

                        {/* 訊息框 */}
                        <div className={`
                            max-w-[80%] text-sm leading-relaxed
                            ${msg.role === 'user'
                                ? 'px-4 py-2 rounded-2xl bg-gray-800 text-white rounded-tr-none shadow-sm'
                                : 'text-gray-700 py-2'}
                        `}>
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {msg.content}
                            </ReactMarkdown>
                        </div>
                    </div>
                ))}

                {/* Loading State */}
                {isLoading && (
                    <div className="flex gap-3">
                        <div className="w-8 h-8 bg-white border rounded-full flex items-center justify-center">
                            <Bot size={16} className="text-orange-500" />
                        </div>
                        <div className="bg-white px-4 py-2 rounded-2xl rounded-tl-none border flex items-center shadow-sm">
                            <Loader2 className="animate-spin text-gray-400" size={16} />
                            <span className="text-gray-400 text-xs ml-2">思考中...</span>
                        </div>
                    </div>
                )}
                {/* 將底部連結到 useRef 物件，每次 message 改變都會觸發 useEffect，進而執行 scrollToButtom()，自動滾動到底部 */}
                <div ref={messageEndRef}></div>
            </main>

            {/* 訊息輸入方框 */}
            <footer className="p-4 bg-white border-t">
                <div className="max-w-3xl mx-auto flex gap-2">
                    <input
                        type="text"
                        value={input}
                        onChange={((e) => setInput(e.target.value))}  // 每輸入一個字都改變狀態，讓畫面能看到輸入的字
                        // 按下 enter 鍵時觸發 handleSend()，但不包括 shift + enter (換行)
                        onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                        placeholder="輸入訊息..."
                        className="flex-1 px-4 py-3 bg-gray-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-300 transition-all"
                        disabled={isLoading}  // 若 isLoading 是 true 則鎖住輸入框
                    />
                    <button
                        onClick={handleSend}  // 不只按 enter，按按鈕送出也觸發
                        disabled={isLoading || !input.trim()}
                        className="p-3 bg-gray-800 text-white rounded-xlhover:bg-gray-700 disabled:opacity-50 transition-colors"
                    >
                        <Send size={20} />
                    </button>
                </div>
            </footer>
        </div>
    )
}