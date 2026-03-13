"use client";

import React, { useState, useRef, useEffect } from 'react';
import remarkBreaks from 'remark-breaks';
import { Send, User, Bot, Loader2, Trash2, Command, Image as ImageIcon, X} from 'lucide-react';
import ReactMarkdown from 'react-markdown';  // 將 md 轉成人類的語言
import remarkGfm from 'remark-gfm'; // 支援表格與程式碼區塊
import { supabase } from '@/lib/supabaseClient';

const CURRENT_SESSION_ID = "afc433a0-3898-4f1c-8423-934e553c716f" // 暫時的 session_id

export default function ChatPage() {
    const [input, setInput] = useState("");   // 使用者輸入框內的 query
    const [loadingMessage, setLoadingMessage] = useState("");  // LLM 思考文字
    const [selectedFile, setSelectedFile] = useState(null);   // 使用者選擇的圖片
    const [imagePreview, setImagePreview] = useState(null);   // 對話框的圖片
    // messages 代表所有歷史對話訊息 (包含使用者和 AI 的，所以當其中一方有傳訊息，就要更新狀態，重新渲染前端)
    const [messages, setMessages] = useState([])
    const [showCommandMenu, setShowCommandMenu] = useState(false);  // 是否要顯示快捷鍵視窗
    const COMMANDS = [
        {
            id: 'clear',
            label: 'clear messages',
            icon: <Trash2 size={16} />,
            action: () => {   // 一按快捷鍵，要執行的動作 (清空訊息狀態，等於清空前端訊息框)，但不動資料庫
                setMessages([]);
                setShowCommandMenu(false);
                setInput("");
            }
        }
    ];

    const messageEndRef = useRef(null);
    const fileInputRef = useRef(null);

    // messageEndRef 連結的是最底部的 div，因此會滾動到可視底部
    const scrollToButtom = () => {
        messageEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    // 每次 messages 變動時，會自動滾動到底部
    useEffect(() => {
        scrollToButtom();
    }, [messages]);

    // 頁面重新載入時，先去後端抓取歷史對話記錄，才能在前端顯示完整的對話
    useEffect(() => {
        const fetch_caht_history = async () => {
            try {
                // limit=0 代表歷史對話要取全部
                const res = await fetch(`http://127.0.0.1:8000/api/v1/chat/history/${CURRENT_SESSION_ID}?limit=0`);

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

    // 使用者每次在輸入框打字，都會觸發
    const handleInputChange = (e) => {
        const value = e.target.value;
        setInput(value);   // 每打一個字都會更新 input，進而重新渲染頁面

        if (value === '/') {  // 當輸入框內容為 / 時，就顯示快捷鍵選單
            setShowCommandMenu(true);
        }
        else {
            setShowCommandMenu(false);
        }
    };

    // 使用者選擇電腦中的照片後觸發
    // 有選擇照片這裡 selectedFile 的狀態就會是有值，這樣就可以協助下方判斷要不要傳圖片給後端 AI
    const handleFileChange = (e) => {
        const file = e.target.files[0];  // 取得圖片物件
        if(file){
            setSelectedFile(file);
            // 建立一個暫時的網址，讓網頁能顯示圖片給使用者預覽 (這個暫時網址並不是後續要存進資料庫的網址)
            setImagePreview(URL.createObjectURL(file));
        }
    }

    // 輔助上傳圖片到 bucket 上，並回傳公開網址
    const uploadChatImage = async(file) => {
        const fileExt = file.name.split('.')[1];  // 取得圖片副檔名
        const fileName = `${Date.now()}-${Math.random().toString(36).substring(2)}.${fileExt}`; // 生成唯一的檔名，避免重複
        const filePath = `${CURRENT_SESSION_ID}/${fileName}`;  // 圖片要上傳到 bucket 的儲存路徑

        // 上傳到名字叫 chat_images 的 bucket 上
        const {data, error} = await supabase.storage
            .from('chat_images')
            .upload(filePath, file);

        if (error) throw new error;

        // 取得該圖片的公開存取網址
        const result = supabase.storage
            .from('chat_images')
            .getPublicUrl(filePath);
        const publicUrl = result.data.publicUrl;

        return publicUrl;
    }

    // 刪除使用者選取的圖片
    const clearSelectedFile = () => {
        if(imagePreview){
            // 避免記憶體洩漏：當刪除照片使 imagePreview 改變時，釋放舊的 URL
            URL.revokeObjectURL(imagePreview);
        }
        // 清空 State
        setSelectedFile(null);
        setImagePreview(null);

        // 很重要! 如果不重置，使用者刪除圖後再選同一張圖，onChange 事件不會觸發，也就不會去預覽等等
        if (fileInputRef.current) {
            fileInputRef.current.value = "";
        }
    }

    // query 送出後，呼叫後端 API 進行處理 (memory 功能轉由後端處理)
    const handleSend = async () => {
        // 若 LLM 還在思考或接收到空字串，則不執行
        if (loadingMessage || !input.trim() && !selectedFile) return;

        setShowCommandMenu(false);   // 確保快捷鍵選單有關閉

        let uploadImageUrl = null;
        const currentInput = input;   // 使用者輸入的文字
        const currentImage = selectedFile;  // 使用者選擇的圖片

        // 送出後要清空使用者輸入框的所有資訊
        setInput("")   
        setSelectedFile(null);
        setImagePreview(null);

        setLoadingMessage("Agent 正在思考中...");

        try {
            // 1. 先處理有無圖片
            if (currentImage){
                // 上傳圖片到 supabase，可以透過 uploadImageUrl 存取
                uploadImageUrl = await uploadChatImage(currentImage);  // await 暫停函式，直到上傳完成才繼續往下執行
            }

            // 2. 顯示使用者的提問，包含文字和圖片
            setMessages((prev) => [
                ...prev,
                {
                    "role": "user",
                    "content":currentInput,
                    "image_url": uploadImageUrl
                }
            ])

            setMessages((prev) => [...prev, { "role": "assistant", "content": "" }]);
            
            // 3. 這樣就可以拿之前的 image_url 當作參數傳給後端呼叫 chat api
            const response = await fetch('http://127.0.0.1:8000/api/v1/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                // 後端要求的是 ChatRequest 物件
                body: JSON.stringify({
                    session_id: CURRENT_SESSION_ID,
                    content: currentInput,
                    image_url: uploadImageUrl
                }),
            });

            if (!response.ok) throw new Error("chat API error");

            const reader = response.body.getReader();  // 取得串流
            const decoder = new TextDecoder("utf-8");  // 將接收到的串流二進位位元組解碼成文字

            // 只要持續有資料傳入，就會一直執行
            while (true) {
                // done (布林值)：後端是否已經傳輸完畢並關閉連線
                // value (二進位資料)：剛接到的那包原始資料
                const { done, value } = await reader.read();  // 每次讀取的串流資料
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                // 後端傳的資料用 SSE 格式，是以兩個換行符號 \n\n 分隔
                const lines = chunk.split("\n\n");
                console.log(lines);

                // 解析每一個資料包
                for (const line of lines) {
                    if (line.startsWith("data: ")) {  // 檢查是否為 SSE 格式
                        const jsonStr = line.substring(6);
                        if (!jsonStr) continue;

                        try {
                            setLoadingMessage("");  // 到這一步代表已經開始工具調用或產出回覆，Loading 文字便清空
                            const parseData = JSON.parse(jsonStr);  // 把字串轉換回 JavaScript 的物件
                            setMessages((prev) => {
                                const newMessages = [...prev];
                                const lastIndex = newMessages.length - 1;  // 剛剛的空 AI 回覆的結尾
                                newMessages[lastIndex] = {
                                    ...newMessages[lastIndex],
                                    // 覆寫最後一則訊息的 content，若沒有 content (已經完成) 就接收空字串
                                    "content": newMessages[lastIndex].content + (parseData.content || "")
                                };
                                return newMessages;
                            });
                        }
                        catch (e) {
                            console.error("Tool call JSON parse error:", e, line);
                        }
                    }
                }
            }
        }
        catch (error) {
            console.error("Chat API Error:", error);
            // 發生錯誤時，如果 AI 還沒講任何話，補上錯誤提示
            setLoadingMessage("");
            setMessages((prev) => {
                const newMessages = [...prev];
                const lastIndex = newMessages.length - 1;
                if (newMessages[lastIndex].content === "") {
                    newMessages[lastIndex].content = "抱歉，GentleCoach 大腦暫時短路了，請稍後再試🙏";
                }
                return newMessages;
            });
        }
        // 結束後一定要呼叫清空，否則下一則訊息會一直帶著這張圖
        clearSelectedFile();
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

            {/* 完整對話區域 */}
            <main className="flex-1 overflow-y-auto space-y-4 p-6">

                {/* 把每一條訊息遞迴顯示在對話框中，才不會只顯示最新的那筆 (包含使用者和 AI 的)，msg 是從資料庫查出的每條訊息 */}
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
                            max-w-[80%] text-sm leading-relaxed break-words
                            ${msg.role === 'user'
                                ? 'px-4 py-2 rounded-2xl bg-gray-200 rounded-tr-none shadow-sm'
                                : 'text-gray-700 py-2'}
                        `}>
                            {/* 如果這則訊息有圖片，也要顯示圖片 (用剛剛取得的公開網址存取) */}
                            {msg.image_url && (
                                <img src={msg.image_url} className="rounded-lg mb-2 max-h-60" alt="chat-img" />
                            )}
                            <ReactMarkdown>{msg.content}</ReactMarkdown>
                        </div>
                    </div>
                ))}

                {/* Loading State */}
                {loadingMessage && (
                    <div className="flex gap-3">
                        <div className="w-8 h-8 bg-white border rounded-full flex items-center justify-center">
                            <Bot size={16} className="text-orange-500" />
                        </div>
                        <div className="bg-white px-4 py-2 rounded-2xl rounded-tl-none border flex items-center shadow-sm">
                            <Loader2 className="animate-spin text-gray-400" size={16} />
                            <span className="text-gray-800 text-xs ml-2">{loadingMessage}</span>
                        </div>
                    </div>
                )}

                {/* 將底部連結到 useRef 物件，每次 message 改變都會觸發 useEffect，進而執行 scrollToButtom()，自動滾動到底部 */}
                <div ref={messageEndRef}></div>
            </main>

            {/* 訊息輸入方框 */}
            <footer className="p-4 bg-white border-t relative">
                {/* 1. 圖片預覽區: 顯示圖片預覽 */}
                {imagePreview && (
                    <div className="absolute bottom-full left-4 mb-2 z-30">
                        <div className="relative group">
                            <img
                                src={imagePreview}
                                alt="Preview"
                                className="w-25 h-25 object-cover rounded-lg border"
                            />
                            {/* 刪除圖片按鈕 */}
                            <button
                                onClick={clearSelectedFile}
                                className="absolute -top-1.5 -right-1.5 bg-gray-400/80 text-white rounded-full p-0.5 hover:bg-gray-600 transition-colors"
                            >
                                <X size={14} />
                            </button>
                        </div>
                    </div>
                )}

                {/* 2. 快捷鍵選單 (showCommandMenu 狀態為 true 時觸發)*/}
                {showCommandMenu && (
                    <div className="absolute bottom-full left-4 mb-2 w-64 bg-white border rounded-xl shadow-xl overflow-hidden z-20 animate-in slide-in-from-bottom-2 fade-in duration-200">
                        <div className="bg-gray-50 px-3 py-2 border-b text-xs font-medium text-gray-500 flex items-center gap-2">
                            <Command size={12} />
                            快捷指令
                        </div>
                        {/* 將 COMMANDS 陣列每一個指令渲染成一個按鈕 */}
                        {COMMANDS.map((cmd) => (
                            <button
                                key={cmd.id}
                                onClick={cmd.action}
                                className="w-full text-left px-3 py-3 hover:bg-orange-50 transition-colors flex items-center gap-3 group"
                            >
                                <div className="text-gray-400 group-hover:text-orange-500">
                                    {cmd.icon}
                                </div>
                                <div className="text-sm font-medium text-gray-700 group-hover:text-orange-600">
                                    /{cmd.label}
                                </div>
                            </button>
                        ))}
                    </div>
                )}

                {/* 3. 輸入框區 */}
                <div className="max-w-3xl mx-auto flex gap-2">
                    {/* 圖片輸入區 */}
                    <input
                        type="file"
                        ref={fileInputRef}   // 將 ref 綁定到 input 元素上
                        onChange={handleFileChange}
                        accept="image/*"
                        className="hidden"
                    />

                    <button
                        onClick={() => fileInputRef.current.click()}  // 點這個按鈕就觸發 fileInputRef 點擊
                        disabled={loadingMessage}
                        className={`p-3 rounded-xl transition-all ${
                            selectedFile 
                            ? 'bg-orange-100 text-orange-600' 
                            : 'text-gray-400 hover:bg-gray-100 hover:text-gray-600'
                        }`}
                    >
                        <ImageIcon size={20} />
                    </button>

                    {/* 文字輸入區 */}
                    <input
                        type="text"
                        value={input}
                        onChange={handleInputChange}  // 每輸入一個字都改變狀態，讓畫面能看到輸入的字
                        // 按下 enter 鍵時觸發 handleSend()，但不包括 shift + enter (換行)
                        onKeyDown={(e) => {
                            if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                                e.preventDefault();
                                handleSend();
                            }
                        }}
                        placeholder="輸入訊息...，或輸入 / 使用指令"
                        className="flex-1 px-4 py-3 bg-gray-100 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-300 transition-all"
                        disabled={loadingMessage}  // 若 isLoading 是 true 則鎖住輸入框
                    />

                    {/* 最後送出所有訊息的按鈕 */}
                    <button
                        onClick={handleSend}  // 不只按 enter，按按鈕送出也觸發
                        disabled={loadingMessage || (!input.trim() && !selectedFile)}
                        className="p-3 bg-gray-800 text-white rounded-xlhover:bg-gray-700 disabled:opacity-50 transition-colors"
                    >
                        <Send size={20} />
                    </button>
                </div>
            </footer>
        </div>
    )
}