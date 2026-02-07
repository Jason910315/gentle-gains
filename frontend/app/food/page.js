"use client";

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { supabase } from '@/lib/supabaseClient';
import { Utensils, Plus, Flame, Beef, Wheat, Droplets, Camera } from 'lucide-react';

export default function FoodPage() {
    const [meals, setMeals] = useState([]);  // 資料庫裡抓出來的飲食記錄
    const [loading, setLoading] = useState(true);
    // 營養素統計狀態
    const [stats, setStats] = useState({
        calories: 0,
        protein: 0,
        carbs: 0,
        fat: 0
    });

    // 建立餐點時段的對應表
    const mealOptions = ['Breakfast', 'Lunch', 'Dinner', 'Snack', 'MidnightSnack']
    const meal_Chinese = { 'Breakfast': '早餐', 'Lunch': '午餐', 'Dinner': '晚餐', 'Snack': '點心', 'MidnightSnack': '宵夜' }

    // 每次進入此頁面都會執行一次 fetchFoodLogs (只做一次)
    useEffect(() => {
        const fetchFoodLogs = async () => {
            try {
                const { data, error } = await supabase
                    .from('food_logs')
                    .select('*')
                    .order('created_at', { ascending: false });

                if (error) throw error;

                // 代表有抓到資料
                if (data) {
                    setMeals(data);

                    // 計算一天內的總營養素，累加所有資料庫內的記錄
                    // reduce() 會將陣列中的所有元素依序傳入並累加
                    const calStats = data.reduce((acc, curr) => {
                        return {
                            calories: acc.calories + (curr.calories || 0),
                            protein: acc.protein + (curr.protein || 0),
                            carbs: acc.carbs + (curr.carbs || 0),
                            fat: acc.fat + (curr.fat || 0),
                        }
                    }, { calories: 0, protein: 0, carbs: 0, fat: 0 });

                    // 更新營養素統計狀態，觸發 html 重新渲染，使畫面有資料
                    setStats(calStats);
                }
            }
            catch (error) {
                console.log("Error catching food logs:", error);
            }
            finally {
                setLoading(false);
            }
        };
        fetchFoodLogs();
    }, []);

    return (
        <div className="p-10 font-snas min-h-screen">
            {/* Header */}
            <header className="max-w-5xl mx-auto mb-8 flex items-end justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-3">
                        <Utensils className="text-orange-500" size={24} />
                        Food Tracker
                    </h1>
                    <p className="text-slate-500 mt-1 text-base">
                        You will become what you eat! 記錄你的每一餐
                    </p>
                </div>
                {/* 新增飲食記錄連結 */}
                <Link href="/food/add">
                    <button className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center gap-2 font-bold text-base group">
                        <Plus className="w-5 h-5 group-hover:totate-90 transition-transform" />
                        新增飲食記錄
                    </button>
                </Link>
            </header>

            {/* 主畫面 main */}
            <main className="max-w-5xl ma-auto space-y-8">
                {/* 1. 營養素儀表板 (Dashboard) 每個卡片使用下方定義的 StatCard */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <StatCard
                        icon={<Flame className="w-5 h-5 text-orange-500" />}
                        label="熱量 (kcal)"
                        value={stats.calories}
                        color="bg-orange-50 text-orange-700"
                    />
                    <StatCard
                        icon={<Beef className="w-5 h-5 text-red-500" />}
                        label="蛋白質 (g)"
                        value={stats.protein}
                        color="bg-red-50 text-red-700"
                    />
                    <StatCard
                        icon={<Wheat className="w-5 h-5 text-yellow-500" />}
                        label="碳水 (g)"
                        value={stats.carbs}
                        color="bg-yellow-50 text-yellow-700"
                    />
                    <StatCard
                        icon={<Droplets className="w-5 h-5 text-blue-500" />}
                        label="脂肪 (g)"
                        value={stats.fat}
                        color="bg-blue-50 text-blue-700"
                    />
                </div>

                {/* 2. 餐點列表 (Image) */}
                <div>
                    <h3 className="text-lg font-bold text-slate-700 mb-4 flex items-center gap-2">
                        <Camera className="w-5 h-5" />
                        餐點畫廊
                    </h3>
                    {loading ? (
                        <div className="text-center py-20 text-slate-400">載入美味中...</div>
                    ) : meals.length === 0 ? (   // 沒資料
                        <div className="text-center py-20 bg-white/40 rounded-3xl border-2 border-dashed border-slate-200">
                            <Utensils className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                            <p className="text-slate-500 font-medium">今天還沒有記錄喔！快去吃點好吃的！</p>
                        </div>
                    ) : (   // 有資料
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {/* 迴圈呈現每張飲食圖片 */}
                            {meals.map((meal) => {
                                return (
                                    // map 函式一定要定義 key 做為辨識每個元素的依據
                                    <div key={meal.id} className="bg-white/80 backdrop-blur-md rounded-2xl p-4 shadow-sm border border-slate-100 hover:shadow-md transition-all group">
                                        {/* 圖片區域 (暫位符) */}
                                        <div className="aspect-video w-full bg-slate-100 rounded-xl mb-4 overflow-hidden relative">
                                            {meal.image_url ? (
                                                <img src={meal.image_url} alt={meal.food_name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                            ) : (
                                                <div className="flex items-center justify-center h-full text-slate-300">
                                                    <Camera size={32} />
                                                </div>
                                            )}
                                            {/* 餐點時段 */}
                                            <div className="absolute top-2 left-2 bg-black/50 backdrop-blur-md text-white text-[10px] font-bold px-2 py-1 rounded-md">
                                                {meal_Chinese[meal.meal_type]}
                                            </div>
                                        </div>
                                        {/* 內容區域 */}
                                        <div className="flex justify-between items-start">
                                            <div>
                                                <h4 className="font-bold text-slate-700 text-sm">{meal.food_name}</h4>
                                                <p className="text-xs text-orange-500 font-bold mt-1">{meal.calories} kcal</p>
                                            </div>
                                            {/* 營養素小標籤 */}
                                            <div className="flex gap-1 text-[10px] font medium text-slate-400">
                                                <span className="bg-slate-100 px-1.5 py-0.5 rounded">P: {meal.protein}</span>
                                                <span className="bg-slate-100 px-1.5 py-0.5 rounded">C: {meal.carbs}</span>
                                                <span className="bg-slate-100 px-1.5 py-0.5 rounded">F: {meal.fat}</span>
                                            </div>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}

// 建立營養素卡片的樣式
function StatCard({ icon, label, value, color }) {
    return (
        <div className={`p-5 rounded-2xl border border-white/50 shadow-sm backdrop-blur-sm bg-white/60 flex flex-col gap-3`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${color}`}>
                {icon}
            </div>
            <div>
                {/* 顯示營養素名稱 */}
                <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">{label}</p>
                {/* 顯示營養素數值 */}
                <p className="text-2xl font-black text-slate-700 mt-0.5 tabular-nums">{value}</p>
            </div>
        </div>
    );
}