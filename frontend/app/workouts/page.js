"use client"; // 標記為 Client Component 以使用 useState/useEffect

// useState 定義 React component 的狀態
// useEffect 告訴 React component 在 render 之後要做的事情
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { supabase } from '@/lib/supabaseClient';
import { Activity, Dumbbell, TrendingUp, Calendar, Plus, Clock } from 'lucide-react';

// 定義網頁互動內容
export default function Workout_record() {
    const [workouts, setWorkouts] = useState([]);  // 定義健身資料的狀態
    const [loading, setLoading] = useState(true);  // 記錄是否正在載入
    const [stats, setStats] = useState({ week_count: 0 });  // 設定統計資料

    // [] 表示在 component mount 後執行且只執行一次
    useEffect(() => {
        async function fetchWorkouts() {
            try {
                // 查詢 workout_logs 表的資料
                // {} 解構賦值能取出後方返回物件的內部屬性 (data, error)，適合用在 API 請求接收返回值
                const { data, error } = await supabase
                    .from("workout_logs")
                    .select('*')
                    .order('created_at', { ascending: false });
                if (error) throw error;

                if (data) {
                    // 將資料設定到 workouts
                    setWorkouts(data || []);

                    // 計算今日與週一隔了幾天
                    const now = new Date();
                    const day = now.getDay();  // 0 (Sun) ~ 6 (Sat)
                    // 如果是週日(0)，要往回推 6 天才是週一；否則往回推 day-1 天
                    const diffToMonday = day === 0 ? 6 : day - 1;

                    const startOfWeek = new Date(now);
                    startOfWeek.setDate(now.getDate() - diffToMonday);  // 倒帶回週一
                    startOfWeek.setHours(0, 0, 0, 0); // 重置為週一凌晨 00:00

                    // 篩選出本週的紀錄
                    const weeklyLogs = data.filter(item => new Date(item.created_at) >= startOfWeek);

                    // 更新 Stats 狀態，狀態改變就能觸發 html 重新渲染，使畫面有資料
                    setStats({
                        count: weeklyLogs.length  // 記錄本週內 (週一開始) 訓練次數
                    });
                }
            }
            catch (error) {
                console.log("Error fetching workout logs:", error);
            }
            finally {
                setLoading(false);
            }
        }
        fetchWorkouts();  // 當畫面第一次載入要執行此程式
    }, []);

    return (
        <div className="p-10 font-sans min-h-screen">

            {/* Header 區域：標題 + 新增按鈕 */}
            <header className="max-w-5xl mx-auto mb-8 flex items-end justify-between">
                <div>
                    <h1 className="text-3xl font-extrabold text-slate-800 flex items-center gap-3">
                        <Activity className="w-8 h-8 text-orange-500" />
                        Workout Record
                    </h1>
                    <p className="text-slate-500 mt-1 text-base">
                        歡迎回來，看看你都練了哪些吧？
                    </p>
                </div>

                {/* ★ 新增：前往「新增記錄」頁面的按鈕 */}
                <Link href="/workouts/add">
                    <button className="px-6 py-2.5 bg-slate-800 hover:bg-slate-700 text-white rounded-lg shadow-md hover:shadow-lg hover:-translate-y-0.5 transition-all flex items-center gap-2 font-bold text-base group">
                        <Plus className="w-5 h-5 group-hover:rotate-90 transition-transform" />
                        新增記錄
                    </button>
                </Link>
            </header>

            <main className="max-w-5xl mx-auto space-y-6">

                {/* --- 統計區塊 (2 欄式) --- */}
                <div className="grid grid-cols-3 gap-6">

                    {/* 1. 一週內訓練總次數 */}
                    <div className="bg-white/60 backdrop-blur-sm p-5 rounded-2xl border border-white/50 shadow-sm flex items-center gap-4">
                        <div className="p-3 bg-orange-50 rounded-full text-orange-600">
                            <TrendingUp className="w-6 h-6" />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">這一週內訓練動作數</p>
                            <p className="text-2xl font-bold text-slate-700">
                                {/* 判斷 loading 狀態，並顯示對應資料 */}
                                {loading ? '讀取中...' : stats.count} <span className="text-sm font-normal text-slate-400">個</span>
                            </p>
                        </div>
                    </div>

                    {/* 2. 上次訓練日 */}
                    <div className="bg-white/60 backdrop-blur-sm p-5 rounded-2xl border border-white/50 shadow-sm flex items-center gap-4">
                        <div className="p-3 bg-purple-50 rounded-full text-purple-600">
                            <Calendar className="w-6 h-6" />
                        </div>
                        <div>
                            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider">上次訓練</p>
                            <p className="text-lg font-bold text-slate-700">
                                {loading ? '讀取中...' : (workouts.length > 0 ? new Date(workouts[0].created_at).toLocaleDateString() : '尚未開始')}
                            </p>
                        </div>
                    </div>
                </div>

                {/* --- 列表 Header --- */}
                <div className="px-6 flex text-xs font-bold text-slate-400 uppercase tracking-wider">
                    <div className="w-1/3">動作與時間</div>
                    <div className="w-2/3 flex justify-end pr-8">訓練數據</div>
                </div>

                {/* --- 列表區塊 --- */}
                <div className="space-y-3">
                    {loading ? (
                        <div className="text-center py-10 text-slate-500 animate-pulse">數據讀取中...</div>
                    ) : workouts.length === 0 ? (
                        <div className="text-center py-20 bg-white/30 rounded-2xl border-2 border-dashed border-slate-200">
                            <Dumbbell className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                            <p className="text-slate-500 text-lg font-medium">目前沒有訓練紀錄，快去新增吧！</p>
                        </div>
                    ) : (
                        // map 會建立一個新陣列，內容是 workouts 中的每一個元素，便可以在函式中使用它
                        workouts.map((log) => (
                            <div
                                key={log.id}
                                className="bg-white/80 backdrop-blur-md p-5 rounded-xl shadow-sm border border-slate-100/50 hover:shadow-md hover:border-orange-300 transition-all flex flex-row justify-between items-center group relative overflow-hidden"
                            >
                                {/* 左側：運動項目與部位 */}
                                <div className="w-1/3 flex flex-col gap-1">
                                    <div className="flex items-center gap-3">
                                        <h3 className="text-xl font-bold text-slate-800 group-hover:text-orange-600 transition-colors">
                                            {log.exercise_name}
                                        </h3>
                                        {/* Body Part 灰底樣式 */}
                                        <span className="px-2.5 py-0.5 rounded-md bg-slate-100 text-slate-500 text-[10px] font-bold border border-slate-200">
                                            {log.body_part || '全身'}
                                        </span>
                                    </div>
                                    {/* 顯示日期與時間 */}
                                    <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                                        <span className="flex items-center gap-1">
                                            <Calendar className="w-3.5 h-3.5" />
                                            {new Date(log.created_at).toLocaleDateString('zh-TW')}
                                        </span>
                                        <span className="flex items-center gap-1">
                                            <Clock className="w-3.5 h-3.5" />
                                            {new Date(log.created_at).toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit' })}
                                        </span>
                                    </div>
                                </div>

                                {/* 右側：數據 */}
                                <div className="w-2/3 flex justify-end gap-12 pr-8">
                                    <div className="text-right min-w-[70px]">
                                        <p className="text-[10px] text-slate-400 uppercase tracking-wider font-bold mb-0.5">Weight</p>
                                        <p className="text-2xl font-bold text-slate-700 tabular-nums">
                                            {log.weight}<span className="text-xs ml-1 text-slate-400 font-normal">kg</span>
                                        </p>
                                    </div>
                                    <div className="text-right min-w-[70px]">
                                        <p className="text-[10px] text-slate-400 uppercase tracking-wider font-bold mb-0.5">Sets</p>
                                        <p className="text-2xl font-bold text-slate-700 tabular-nums">{log.sets}</p>
                                    </div>
                                    <div className="text-right min-w-[70px]">
                                        <p className="text-[10px] text-slate-400 uppercase tracking-wider font-bold mb-0.5">Reps</p>
                                        <p className="text-2xl font-bold text-slate-700 tabular-nums">{log.reps}</p>
                                    </div>
                                </div>

                                {/* 裝飾：Hover 時顯示的右側橘色線條 */}
                                <div className="absolute right-0 top-0 bottom-0 w-1 bg-orange-400 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            </div>
                        ))
                    )}
                </div>
            </main>
        </div>
    );
}