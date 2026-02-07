"use client";

import React, { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
    Camera, ArrowLeft, UploadCloud,
    CheckCircle, RefreshCw, X,
    Coffee, Sun, Moon, Cookie,
    Star, StarHalf
} from 'lucide-react';

export default function AddFoodPage() {
    const router = useRouter();
    // 用 useRef 就不會重新渲染畫面，這裡使用它來取得 html 元素
    const fileInputRef = useRef(null);

    // --- 1. 狀態管理 ---
    // status: idle (填寫中)、analyzing(分析中)、review (確認結果)、success (完成)
    const [status, setStatus] = useState('idle');
    const [formData, setFormData] = useState({
        food_name: '',
        meal_type: 'Lunch',  // 預設午餐
    });

    // 圖片預覽 (顯示在畫面讓使用者確認，還未上傳)
    const [previewUrl, setPreviewUrl] = useState(null);
    const [file, setFile] = useState(null);

    // AI 分析的結果，並非使用者輸入
    const [aiResult, setAiResult] = useState({
        calories: 0,
        protein: 0,
        carbs: 0,
        fat: 0,
        score: 0,          // 飲食評分：0~5
        coach_comment: ''  // 評語
    });

    const mealOptions = ['Breakfast', 'Lunch', 'Dinner', 'Snack', 'MidnightSnack']
    const meal_Chinese = { 'Breakfast': '早餐', 'Lunch': '午餐', 'Dinner': '晚餐', 'Snack': '點心', 'MidnightSnack': '宵夜' }

    // 避免記憶體洩漏：當重新上傳照片使 previewUrl 改變時，釋放舊的 URL
    useEffect(() => {
        return () => {
            if (previewUrl) {
                URL.revokeObjectURL(previewUrl);
            }
        };
    }, [previewUrl]);

    // 2. 處理函式 ---

    // 照片被選擇後觸發
    const handleFileChange = (e) => {
        const selectedFile = e.target.files[0];
        if (selectedFile) {
            setFile(selectedFile);  // 照片存進去
            // 建立一個暫時的網址，讓網頁能顯示圖片給使用者預覽 (這個暫時網址並不是後續要存進資料庫的網址)
            setPreviewUrl(URL.createObjectURL(selectedFile));
        }
    };

    // 將使用者上傳的 File 物件轉成 Base64 字串
    const fileToBase64 = (file) => {
        return new Promise((resolve, reject) => {
            // 建立瀏覽器閱讀器物件
            const reader = new FileReader();
            reader.readAsDataURL(file);     // 轉成 base64
            reader.onload = () => resolve(reader.result);
            reader.onerror = error => reject(error);
        })
    };

    // 點選"新增"按鈕後觸發，呼叫並等待 AI 分析
    const handleAnalyze = async () => {
        // meal_type 預設為 Lunch，所以不需檢查
        if (!file) return alert("請先上傳照片！");
        if (!formData.food_name) return alert("請輸入食物名稱！");

        // 若所有欄位都填妥，上傳後轉換狀態．開始分析
        setStatus('analyzing');

        // AI 分析
        try {
            // 1. 將圖片轉成 Base64
            const base64String = await fileToBase64(file);

            // 2. 呼叫後端 API 進行 AI 分析
            const response = await fetch('http://127.0.0.1:8000/api/v1/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({  // 將前端的資料轉成字串，傳入定義好的 AnalyzeRequest 物件的格式
                    image_base64: base64String,
                    food_name: formData.food_name,
                    meal_type: formData.meal_type
                }),
            });

            if (!response.ok) {
                throw new Error('分析失敗');
            }
            // 將後端回傳的結果轉成 JS 物件
            const data = await response.json();

            // 3. 將後端回傳的分析結果存入 State
            setAiResult({
                calories: data.calories,
                protein: data.protein,
                carbs: data.carbs,
                fat: data.fat,
                score: data.score,
                coach_comment: data.coach_comment,
            });
            // 資料庫寫入成功與否會顯示不同確認視窗
            if (data.is_saved === false) {
                alert("AI 分析成功，但資料未寫入資料庫，請稍後再試\n或聯絡管理員：a0938692163@gmail.com")
                setStatus('review_with_dberror');  // 資料寫進資料庫失敗，需讓使用者點擊後直接跳出彈出視窗 (但仍要 review)
            }
            else {
                setStatus('review');  // 分析完後更新 setAiResult 狀態，並將 status 轉為 review，畫面會轉變
            }
        }
        catch (error) {
            console.error('分析失敗:', error);
            alert('AI 分析失敗，請稍後再試\n或聯絡管理員：a0938692163@gmail.com');
            setStatus('idle');
        }
    };

    // 點選確認儲存，關閉跳轉視窗
    const handleConfirmUpload = async () => {
        setStatus('success');  // 資料庫寫完後，代表成功儲存，跳到成功畫面
    };

    // 將所有資料清空
    const handleReset = () => {
        setFile(null);
        setPreviewUrl(null);
        setFormData({ ...formData, food_name: '' })
        setAiResult({ calories: 0, protein: 0, carbs: 0, fat: 0, score: 0, coach_comment: '' });
        setStatus('idle');  // 轉換回初始狀態，會結束彈出視窗跳回 food/add 主頁面
    };

    return (
        <div className="min-h-screen bg-slate-50 font-sans pb-20">
            {/* --- Header --- */}
            <header className="bg-white px-6 py-4 flex items-center gap-4 sticky top-0 z-10 shadow-sm">
                {/* 返回上一頁 (food page) 按鈕 */}
                <Link href="/food">
                    <button className="p-2 -ml-2 text-slate-400 hover:text-slate-600 rounded-full hover:bg-slate-100 transition-colors">
                        <ArrowLeft size={24} />
                    </button>
                </Link>
                <h1 className="text-xl font-bold text-slate-800">新增飲食記錄</h1>
            </header>

            {/* --- 主畫面區域 (新增項目區塊 Main) --- */}
            <main className="p-6 max-w-xl mx-auto space-y-8">
                {/* 1. 圖片上傳區 */}
                <div
                    // 點擊這個 div 區塊，就會觸發被隱藏起來的 input 的點擊事件，點了之後開啟檔案選擇介面
                    // current 指向這個唯一的 html 元素
                    onClick={() => fileInputRef.current.click()}
                    className={`
                        aspect-video rounded-2xl border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all overflow-hidden relative group
                        ${previewUrl ? 'border-orange-300 bg-orange-50' : 'border-slate-300 bg-white hover:border-orange-400 hover:bg-slate-50'}
                    `}
                >
                    {previewUrl ? (  // 有上傳就顯示預覽圖片
                        <img src={previewUrl} alt="Preview" className="w-full h-full object-contain" />
                    ) : (
                        <>
                            <div className="w-16 h-16 bg-orange-100 text-orange-500 rounded-full flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                                <Camera size={32} />
                            </div>
                            <p className="text-slate-400 font-bold text-sm">點擊上傳你吃的東東！</p>
                        </>
                    )}
                    {/* 被隱藏起來的 input 元素，accept="image/*" 限制只能上傳圖片*/}
                    {/* ref={fileInputRef} 代表讓 fileInputRef 變數指向這個 input 元素 */}
                    {/* 當有檔案上傳時，檔案選擇畫面被關閉，然後觸發 onChange 事件 */}
                    <input type="file" accept="image/*" ref={fileInputRef} onChange={handleFileChange} className="hidden"></input>
                </div>

                {/* 2. 表單區 */}
                <div className="space-y-6">
                    <div className="space-y-2">
                        <label className="text-sm font-bold text-slate-500 uppercase tacking-wider">吃了什麼？</label>
                        <input
                            type="text"
                            value={formData.food_name}
                            placeholder="例如：牛肉麵"
                            // 使用者輸入會不斷更新 formData，...formData 意思是把原本 formData 的屬性都複製過來
                            onChange={(e) => setFormData({ ...formData, food_name: e.target.value })}
                            className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-orange-400 transition-all text-slate-700 font-bold text-lg"
                        />
                    </div>
                    <div className="space-y-6">
                        <label className="text-sm font-bold text-slate-500 uppercase tacking-wider">什麼時候吃的？</label>
                        <div className="grid grid-cols-5 gap-2">
                            {/* 迴圈建立五個按鈕 */}
                            {mealOptions.map((type) => (
                                // 使用下方定義的元件
                                <MealTypeBtn
                                    key={type}  // 傳入一個識別陣列元素的唯一 key
                                    type={type}
                                    current={formData.meal_type}
                                    // State 更新後又會觸發渲染
                                    setType={(t) => setFormData({ ...formData, meal_type: t })}
                                />
                            ))}
                        </div>
                    </div>
                </div>

                {/* 按鈕區 */}
                <button
                    onClick={handleAnalyze}
                    className="w-2/5 mx-auto py-4 bg-slate-800 text-white rounded-xl font-bold text-lg shadow-lg hover:bg-slate-700 active:scale-95 transition-all flex items-center justify-center gap-2"
                >
                    <UploadCloud size={24} />
                    新增
                </button>
            </main>

            {/* --- Modal (互動視窗) 區域 --- */}
            {/* 這邊要判斷 status 狀態，只要不是 idle，就會跳出互動視窗，再依不同狀態調整頁面 */}
            {status !== 'idle' && (  // 只要 status 不是 idle，就執行 && 後面的程式碼 (後面還有一層一層判斷下去)
                <div className="fixed inset-0 z-50 flex items-center justify-center px-4">
                    <div className="absolute inset-0 bg-slate-900/60 backdrop-blur-sm"></div>
                    <div className="bg-white w-full max-w-lg rounded-3xl shadow-2xl relative z-10 overflow-hidden animate-in fade-in zoom-in duration-300">
                        {/* 這邊會根據不同 status 顯示不同內容 */}

                        {/* a. 狀態：分析中 */}
                        {status === 'analyzing' && (
                            <div className="p-10 flex flex-col items-center justify-center space-y-6">
                                <div className="relative">
                                    <div className="w-36 h-36 border-4 border-slate-100 border-t-orange-500 rounded-full animate-spin"></div>
                                    <div className="absolute inset-0 flex items-center justify-center text-orange-500"><Camera size={18} /></div>
                                </div>
                                <div>
                                    <h3 className="text-xl font-black text-slate-800">AI 幫你分析...</h3>
                                    <p className="text-slate-500 mt-2 text-sm">正在分析營養成分與健康評級</p>
                                </div>
                            </div>
                        )}

                        {/* b. 狀態：確認 (review) */}
                        {status === 'review' && (
                            <div className="p-6">
                                <h2 className="text-center font-bold text-slate-400 uppercase tracking-widest text-xs mb-4">分析完成</h2>

                                <div className="bg-slate-50 rounded-2xl p-4 mb-6 border border-slate-100">
                                    {/* 顯示圖片與基本資訊 */}
                                    <div className="flex gap-6 items-start mb-4 border-b border-slate-200 pb-4">
                                        <img src={previewUrl} className="w-42 h-42 rounded-lg object-cover bg-white shadow-sm" />
                                        <div>
                                            <p className="font-bold text-2xl text-slate-800">{formData.food_name}</p>
                                            <span className="text-xs bg-gray-300 text-gray-600 px-2 py-0.5 rounded-full font-bold">
                                                {meal_Chinese[formData.meal_type]}
                                            </span>
                                            <br />
                                            <p className="text-sm text-slate-800">{aiResult.coach_comment}</p>
                                        </div>
                                    </div>

                                    {/* 顯示營養素資訊 (Grid) */}
                                    <div className="grid grid-cols-4 gap-1 text-center mb-4">
                                        {/* 使用下方定義好的樣板 MacroItem */}
                                        <MacroItem label="熱量" val={aiResult.calories} unit="kcal" />
                                        <MacroItem label="蛋白質" val={aiResult.protein} unit="g" />
                                        <MacroItem label="碳水" val={aiResult.carbs} unit="g" />
                                        <MacroItem label="脂肪" val={aiResult.fat} unit="g" />
                                    </div>

                                    {/* 健康評分顯示區 */}
                                    <div className="bg-white p-3 rounded-xl border border-slate-100 flex items-center justify-between">
                                        <span className="text-base font-bold text-slate-400 uppercase">健康評分</span>
                                        <div className="flex items-center gap-2">
                                            {/* 呼叫星星組件 */}
                                            <StarRating score={aiResult.score} />
                                            <span className="font-bold text-slate-700 text-lg">{aiResult.score}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* 按鈕區，分別觸發兩個不同函式 */}
                                <div className="grid grid-cols-2 gap-3">
                                    <button onClick={handleReset} className="py-3 rounded-xl border border-slate-200 text-slate-600 font-bold hover:bg-slate-50 transition-colors flex items-center justify-center gap-2">
                                        <RefreshCw size={18} /> 再傳一筆
                                    </button>
                                    <button onClick={handleConfirmUpload} className="py-3 rounded-xl bg-orange-500 text-white font-bold hover:bg-orange-600 shadow-md shadow-orange-200 transition-colors flex items-center justify-center gap-2">
                                        <CheckCircle size={18} /> 確認儲存
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* c. 狀態：寫入資料庫失敗，但仍需確認 AI 分析結果 (review_with_dberror) */}
                        {status === 'review_with_dberror' && (
                            <div className="p-6">
                                <h2 className="text-center font-bold text-slate-400 uppercase tracking-widest text-xs mb-4">分析完成</h2>

                                <div className="bg-slate-50 rounded-2xl p-4 mb-6 border border-slate-100">
                                    {/* 顯示圖片與基本資訊 */}
                                    <div className="flex gap-6 items-start mb-4 border-b border-slate-200 pb-4">
                                        <img src={previewUrl} className="w-42 h-42 rounded-lg object-cover bg-white shadow-sm" />
                                        <div>
                                            <p className="font-bold text-2xl text-slate-800">{formData.food_name}</p>
                                            <span className="text-xs bg-gray-300 text-gray-600 px-2 py-0.5 rounded-full font-bold">
                                                {meal_Chinese[formData.meal_type]}
                                            </span>
                                        </div>
                                    </div>

                                    {/* 顯示營養素資訊 (Grid) */}
                                    <div className="grid grid-cols-4 gap-1 text-center mb-4">
                                        {/* 使用下方定義好的樣板 MacroItem */}
                                        <MacroItem label="熱量" val={aiResult.calories} unit="kcal" />
                                        <MacroItem label="蛋白質" val={aiResult.protein} unit="g" />
                                        <MacroItem label="碳水" val={aiResult.carbs} unit="g" />
                                        <MacroItem label="脂肪" val={aiResult.fat} unit="g" />
                                    </div>

                                    {/* 健康評分顯示區 */}
                                    <div className="bg-white p-3 rounded-xl border border-slate-100 flex items-center justify-between">
                                        <span className="text-base font-bold text-slate-400 uppercase">健康評分</span>
                                        <div className="flex items-center gap-2">
                                            {/* 呼叫星星組件 */}
                                            <StarRating score={aiResult.score} />
                                            <span className="font-bold text-slate-700 text-lg">{aiResult.score}</span>
                                        </div>
                                    </div>
                                </div>

                                {/* 按鈕區，分別觸發兩個不同函式 */}
                                <div className="grid grid-cols-2 gap-3">
                                    <button onClick={handleReset} className="py-3 rounded-xl border border-slate-200 text-slate-600 font-bold hover:bg-slate-50 transition-colors flex items-center justify-center gap-2">
                                        <RefreshCw size={18} /> 重新上傳
                                    </button>
                                    <button onClick={() => router.push('/food')} className="py-3 rounded-xl bg-orange-500 text-white font-bold hover:bg-orange-600 shadow-md shadow-orange-200 transition-colors flex items-center justify-center gap-2">
                                        <CheckCircle size={18} /> 返回飲食列表
                                    </button>
                                </div>
                            </div>
                        )}

                        {/* d. 成功 */}
                        {status === 'success' && (
                            <div className="p-8 text-center flex flex-col items-center">
                                <div className="w-20 h-20 bg-green-100 text-green-500 rounded-full flex items-center justify-center mb-6 animate-bounce">
                                    <CheckCircle size={40} />
                                </div>
                                <h3 className="text-2xl font-black text-slate-800 mb-2">新增成功！</h3>
                                <p className="text-slate-500 mb-8">飲食記錄與 AI 評分已存入資料庫</p>

                                {/* 讓使用者選擇兩種路徑 */}
                                <div className="w-full space-y-3">
                                    {/* 點擊後會執行將所有資料清空，但因為資料已存入，所以沒關係 */}
                                    <button onClick={handleReset} className="w-full py-3.5 bg-slate-800 text-white rounded-xl font-bold shadow-lg hover:bg-slate-700 transition-all">
                                        再記一筆！
                                    </button>
                                    <button onClick={() => router.push('/food')} className="w-full py-3.5 text-slate-500 font-bold hover:bg-slate-100 rounded-xl transition-all">
                                        返回飲食列表
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}

function StarRating({ score }) {
    const stars = [1, 2, 3, 4, 5];
    return (
        <div className="flex text-yellow-400 gap-0.5">
            {stars.map((star) => {
                // 邏輯：迴圈會將每個陣列元素與 score 比大小
                // 1. 若分數 >= 當前星星數，顯示全星
                // 2. 若分數 >= 當前星星數 - 0.5 (如 4.5 >= 4.5)，顯示半星
                // 3. 否則星星為空 (以灰色星星顯示)
                if (score >= star) {
                    return <Star key={star} size={18} fill="currentColor" />;
                }
                else if (score >= star - 0.5) {
                    return <StarHalf key={star} size={18} fill="currentColor" />;
                }
                else {
                    return <Star key={star} size={18} className="text-slate-200" fill="currentColor" />;
                }
            })}
        </div>
    )
}

// 建立「一個按鈕」的樣版
// meal_type 被選擇後會發生的事情，type 為我是哪個按鈕，current 則是目前被點擊的是誰，setType 則是把點擊的種類傳回父層的函式
function MealTypeBtn({ type, current, setType }) {
    const isSelected = current === type;  // 判斷目前點擊的是不是我這個按鈕
    const icons = { Breakfast: <Coffee size={20} />, Lunch: <Sun size={20} />, Dinner: <Moon size={20} />, Snack: <Cookie size={20} />, MidnightSnack: <Star size={20} /> };
    const labels = { Breakfast: '早餐', Lunch: '午餐', Dinner: '晚餐', Snack: '點心', MidnightSnack: '宵夜' };

    return (
        <button
            onClick={() => setType(type)}  // 點擊時就執行 setType，將 type 更新到 formData 裡
            className={`flex flex-col items-center justify-center p-3 rounded-xl border-2 transition-all duration-200 ${isSelected ? 'border-orange-500 bg-orange-50 text-orange-600' : 'border-slate-100 bg-white text-slate-400 hover:border-slate-200'}`}
        >
            <div className={`mb-1 ${isSelected ? 'scale-110' : ''} transition-transform`}>{icons[type]}</div>
            <span className="text-xs font-bold">{labels[type]}</span>
        </button>
    )
}

function MacroItem({ label, val, unit }) {
    return (
        <div className="flex flex-col items-center">
            {/* 顯示標題、數值、以及單位 */}
            <span className="text-[12px] text-slate-400 uppercase font-bold">{label}</span>
            <span className="font-black text-slate-700 text-xl leading-tight">{val}</span>
            <span className="text-[12px] text-slate-400">{unit}</span>
        </div>
    )
}