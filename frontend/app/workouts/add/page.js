"use client";

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';  // 用於頁面跳轉
import { supabase } from '@/lib/supabaseClient';
import { ArrowLeft, Save, Dumbbell, Loader2, Eraser } from 'lucide-react';
import Link from 'next/link';

export default function AddWorkoutPage() {
    const router = useRouter();
    const [isSubmitting, setIsSubmitting] = useState(false);  // 控制按鈕 Loading 狀態

    // 定義初始值為常數
    const INITIAL_STATE = {
        exercise_name: '',
        body_part: '胸部',  // 預設值
        weight: '',
        sets: '',
        reps: '',
    }

    // 定義表單狀態 (記錄健身資訊)，用常數初始化
    const [formData, setFormData] = useState(INITIAL_STATE);

    // 處理使用者輸入使欄位變更 (由 React 控制 Input 內容)
    const handleChange = (e) => {   // 事件處理函式 (onChange) 會預設塞入 event 物件作為參數
        const { name, value } = e.target;  // target 指向觸發事件的 html 元素，注意 value 是你當前輸入的東西，還未更新到 State
        // 更新表單狀態
        setFormData((prev) => {
            var newObj = {};
            // 要保留未修改的欄位的值
            for (var key in prev) {
                newObj[key] = prev[key];
            }
            newObj[name] = value;  // 將剛輸入的 value 更新到 key 是 name 的位置
            return newObj;
        })
    };

    // 清空表單
    const handleClear = () => {
        setFormData((prev) => ({
            ...prev,       // 先把「所有」舊資料複製進來
            weight: '',    // 覆蓋要清空的欄位
            sets: '',
            reps: ''
        }));
    }

    // 處理表單送出
    const handleSubmit = async (e) => {
        e.preventDefault();  // 阻止正在執行的 event 的預設行為 (例如送出表單會重整頁面)

        // 驗證資料
        const errorMessage = [];

        if (!formData.exercise_name.trim()) {
            errorMessage.push("請輸入動作名稱!");;
        }
        // 檢查訓練的數據
        if (!formData.weight || Number(formData.weight) <= 0) {
            errorMessage.push("訓練重量不能為 0 或空白");
        }
        if (!formData.reps || Number(formData.reps) <= 0) {
            errorMessage.push("訓練次數至少要 1 次！");
        }
        if (!formData.sets || Number(formData.sets) <= 0) {
            errorMessage.push("訓練組數至少要 1 組！");
        }

        if (errorMessage.length > 0) {
            alert(`⚠️ 儲存失敗！請檢查以下欄位: \n\n${errorMessage.join('\n')}`)
            return; // 失敗就不能往下執行
        }
        // 驗證通過才送出表單
        setIsSubmitting(true);

        try {
            if (!formData.exercise_name) {
                alert("請輸入動作名稱！");
                return;
            }
            const { error } = await supabase
                .from('workout_logs')
                .insert([
                    {
                        exercise_name: formData.exercise_name,
                        body_part: formData.body_part,
                        weight: Number(formData.weight) || 0,  // 轉成數字，若為空則變為 0
                        sets: Number(formData.sets) || 0,
                        reps: Number(formData.reps) || 0,
                        // created_at 會由資料庫自動產生
                    }
                ]);

            if (error) throw error;

            router.push('/workouts');
        }
        catch (error) {
            console.error('Error adding workout:', error);
            alert('新增健身記錄失敗，請檢查網路連線');
        }
        finally {
            setIsSubmitting(false);  // 無論成功失敗，都要把 Loading 狀態關掉
        }
    };

    return (
        <div className="p-10 font-sans min-h-screen flex justify-center items-start pt-20">
            <div className="w-full max-w-2xl bg-white/80 backdrop-blur-md p-8 rounded-3xl shadow-xl border border-orange-100/50 relative overflow-hidden">
                <div className="absolute top-0 left-0 right-0 h-2 bg-gradient-to-r from-orange-400 to-yellow-400"></div>

                {/* Header: 返回按鈕與標題 */}
                <header className="flex items-center gap-4 mb-8">
                    <Link href="/workouts">
                        {/* 設定一個可以返回前一頁的按鈕，並設定為箭頭樣式 */}
                        <button className="p-2 rounded-full hover:bg-slate-100 text-slate-500 hover:text-slate-600 transition-colors">
                            <ArrowLeft size={24} />
                        </button>
                    </Link>
                    <div>
                        <h1 className="text-2xl font-extrabold text-slate-800 flex items-center gap-2">
                            <Dumbbell className="text-orange-500" size={24} />
                            新增健身記錄
                        </h1>
                        <p className="text-sm text-slate-400">今天練了什麼？記錄下來吧！</p>
                    </div>
                </header>

                {/* Form 表單區域，用 handleSubmit 來處理表單送出 */}
                <form onSubmit={handleSubmit} className="space-y-6">

                    {/* 第一列：動作名稱 ＆ 部位 (兩欄)*/}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* 動作名稱 */}
                        <div className="space-2">
                            <label className="text-sm font-bold text-slate-500 uppercase tracking-wider">練了啥動作啊？</label>
                            {/* 現在 input 的內容交給 State 控制 */}
                            {/* 使用者打字會觸發 handleChange()，讓函式去更新 State，一更新就會重新渲染畫面 */}
                            <input
                                type="text"
                                name="exercise_name"
                                value={formData.exercise_name} // 重新渲染後，input 的值會自動更新成 State 的值
                                onChange={handleChange}   // input 的 onChange 屬性接收上方定義的 handleChange 函數
                                placeholder="例如：啞鈴臥推"
                                className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-orange-400 transition-all text-slate-700 font-bold placeholder:font-normal"
                            />
                        </div>
                        {/* 訓練部位 */}
                        <div className="space-y-2">
                            <label className="text-sm font-bold text-slate-500 uppercase tracking-wider">練了哪裡啊？</label>

                            <div className="relative">
                                <select
                                    name="body_part"
                                    value={formData.body_part}
                                    onChange={handleChange}
                                    className="w-full px-4 py-3 bg-white border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-orange-200 focus:border-orange-400 transition-all text-slate-700 font-bold appearance-none cursor-pointer"
                                >
                                    <option claue="胸部">胸部</option>
                                    <option claue="胸部">背部</option>
                                    <option claue="胸部">腿部</option>
                                    <option claue="胸部">肩膀</option>
                                    <option claue="胸部">手臂</option>
                                    <option claue="胸部">核心</option>
                                    <option claue="胸部">全身</option>
                                </select>
                                {/* 自訂下拉箭頭 */}
                                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
                                    <svg className="w-4 h-4 fill-current" viewBox="0 0 20 20"><path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" /></svg>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* 第二列：健身數據輸入*/}
                    <div className="grid grid-cols-3 gap-6">
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-400 uppercase text-center block">重量 (Kg)</label>
                            <input
                                type="number"
                                name="weight"
                                value={formData.weight}
                                onChange={handleChange}
                                placeholder="0"
                                className="w-full px-2 py-3 text-center bg-slate-50 border-none rounded-xl text-2xl font-black text-slate-700 focus:ring-2 focus:ring-orange-200 transition-all placeholder:text-slate-300"
                                min="0" step="0.5" // 重量最少要 1kg
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-400 uppercase text-center block">組數 (Sets)</label>
                            <input
                                type="number"
                                name="sets"
                                value={formData.sets}
                                onChange={handleChange}
                                placeholder="0"
                                className="w-full px-2 py-3 text-center bg-slate-50 border-none rounded-xl text-2xl font-black text-slate-700 focus:ring-2 focus:ring-orange-200 transition-all placeholder:text-slate-300"
                                min="0"
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-400 uppercase text-center block">次數 (Reps)</label>
                            <input
                                type="number"
                                name="reps"
                                value={formData.reps}
                                onChange={handleChange}
                                placeholder="0"
                                className="w-full px-2 py-3 text-center bg-slate-50 border-none rounded-xl text-2xl font-black text-slate-700 focus:ring-2 focus:ring-orange-200 transition-all placeholder:text-slate-300"
                                min="0"
                            />
                        </div>
                    </div>

                    {/* 第三列：Action Button*/}
                    <div className="pt-6 flex gap-12">
                        {/* 取消鈕 */}
                        <button
                            type="button"  // 這裡不是 submit 鈕
                            onClick={handleClear}  // 取消鈕則清空表單
                            className="flex-2 py-3.5 rounded-xl border border-slate-200 text-slate-500 font-bold hover:bg-slate-50 transition-all flex justify-center items-center gap-2 text-sm"
                        >
                            <Eraser className="w-5 h-5" />
                            取消
                        </button>

                        {/* 表單送出鈕 */}
                        <button
                            type="submit"  // 往上找 form 裡定義的 submit
                            disabled={isSubmitting}   // disabled 代表禁用與否
                            className="flex-2 py-2.5 rounded-xl bg-slate-800 text-white font-bold hover:bg-slate-700 shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all flex justify-center items-center gap-2 disabled:opacity-70 disabled:cursor-not-allowed text-sm"
                        >
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    儲存中...
                                </>
                            ) : (
                                <>
                                    {/* 代表目前表單還未送出 */}
                                    <Save className="w-5 h-5" />
                                    儲存紀錄
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}