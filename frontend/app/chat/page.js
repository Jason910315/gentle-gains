"use client";

import React, { useState, useRef, useEffect } from 'react';
import { Send, User, Bot, Loader2 } from 'lucide-react';

export default function ChatPage() {
    const [input, setInput] = useState("");  // 使用者的 query
    const [isLoading, setIsLoading] = useState(false);

    // messages 代表所有對話訊息 (包含使用者和 AI 的)
    const [messages, setMessages] = useState([
        { "role": "assistant", "content": "嗨！我是你的 AI 健身教練 GentleCoach。今天想聊聊飲食還是運動計畫？" }
    ])

    const messageEndRef = useRef(null);

    // messageEndRef 連結的是最底部的 div，因此會滾動到可視底部
    const scrollToButtom = () => {
        messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // 每次 messages 變動時，會自動滾動到底部
    useEffect(() => {
        scrollToButtom();
    }, [messages]);

    // query 送出後，呼叫後端 API 進行處理
    const handleSend = async () => {
        if (isLoading || !input.trim()) return;

        // 更新 UI 
        const userMessage = { "role": "user", "content": input };
        // 將每次的歷史對話訊息與使用者的最新 query 串接起來 (記憶功能，但之後要修改成存資料庫)
        // 會變成 [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}, ...]
        const newHistory = [...messages, userMessage];
        setMessages(newHistory);
        setInput("");  // 送出後要清空輸入 (對話框)
        setIsLoading(true);

        try {
            const response = await fetch('http://127.0.0.1:8000/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ messages: newHistory })  // 傳送完整歷史記錄，包括最新對話，messages: []
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
                            px-4 py-2 rounded-2xl max-w-[80%] text-sm leading-relaxed shadow-sm
                            ${msg.role === 'user'
                                ? 'bg-gray-800 text-white rounded-tr-none'
                                : 'bg-white text-gray-700 border rounded-tl-none'}
                        `}>
                            {msg.content} {/* 訊息內容 */}
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