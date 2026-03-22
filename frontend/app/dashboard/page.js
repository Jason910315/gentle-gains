"use client";

import React, { useEffect, useState } from 'react';
import { ResponsiveContainer, PieChart, Pie, Cell, RadarChart, PolarGrid, PolarAngleAxis, Radar,Tooltip, Legend } from 'recharts';
import { Activity, Flame, Target, Trophy, Dumbbell, Utensils } from 'lucide-react';

const Dashboard = () => {
  const [data, setData] = useState(null);  // DashboardSummary 物件
  const [loading, setLoading] = useState(true);  // 重新載入頁面一開始都是載入中

  // 每次頁面載入時都會重新抓取後端資料，並更新 data 狀態
  useEffect(() => {
    const fetchData = async () => {
      const response = await fetch('http://localhost:8000/api/v1/dashboard/summary', {
        method: 'GET', 
        headers: {
            'Content-Type': 'application/json'
        },
      });
      if (!response.ok) throw new Error("Dashboard API Error");
      const data = await response.json();
      setData(data);
      setLoading(false);
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-50 text-gray-500">
        無法讀取數據，請確保後端正在運行。
      </div>
    );
  }

  const { nutrition, heatmap, distribution, insight } = data;  // data 是剛剛呼叫 API 拿到的 DashboardSummary 物件

  // --- 計算圓餅圖數據與顏色 ---
  const nutritionChartData = [
    { name: '蛋白質', value: nutrition.protein * 4, color: '	#84C1FF' }, // Indigo 500
    { name: '脂肪', value: nutrition.fat * 9, color: '	#B9B9FF' },    // Rose 500
    { name: '碳水', value: nutrition.carbs * 4, color: '#D9FFFF' },   // Emerald 500
  ];

  // 要顯示在圓餅圖中央的資訊
  const totalCals = nutrition.calories;
  const targetCals = nutrition.target_calories;
  const percent = Math.round((totalCals / targetCals) * 100);

  // --- 自定義外部標籤渲染 ---
  const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, value, name }) => {
    const RADIAN = Math.PI / 180;
    const radius = outerRadius * 1.3; // 標籤離圓心的距離
    const x = cx + radius * Math.cos(-midAngle * RADIAN);
    const y = cy + radius * Math.sin(-midAngle * RADIAN);

    return (
      <g>
        {/* 小箭頭/線條 */}
        <line 
          x1={cx + outerRadius * Math.cos(-midAngle * RADIAN)} 
          y1={cy + outerRadius * Math.sin(-midAngle * RADIAN)}
          x2={x}
          y2={y}
          stroke="#9CA3AF"
        />
        <text 
          x={x + (x > cx ? 5 : -5)} 
          y={y} 
          fill="#4B5563" 
          textAnchor={x > cx ? 'start' : 'end'} 
          dominantBaseline="central"
          className="text-[11px] font-bold"
        >
          {`${name} ${value}kcal`}  {/* 標籤文字：營養素名稱 + 卡路里數 */}
        </text>
      </g>
    );
  };

  // 身體部位 Radar 圖
  const radarData = distribution.map(item => ({
    subject: item.body_part,   // 雷達圖每個角的標題
    A: item.count,             // 該區域的強度用 count 表示
    fullMark: Math.max(...distribution.map(d => d.count), 5)
  }));

  const today = new Date();
  const year = today.getFullYear();
  const month = today.getMonth();  // 注意!! JS 的月份是從 0 開始算
  
  // 算出當前月份有幾天
  // month + 1 先跳到下個月，然後取 0 就是取得下個月 1 號的前一天，也就是當前月份的最後一天 
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  
  const HeapArray = Array.from({ length: daysInMonth });  // 建立一個長度為當前月份天數的陣列

  // 訓練次數 Heatmap
  const heatmapBoxes = HeapArray.map((_, i) => {   // i 為索引
    const day = i + 1;
    // 組成跟 Supabase 裡日期格式一樣的字串 (padStart 是填滿字串，會自動補齊成兩位數)
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
    // 後端 heatmap 格式是 [{"date": k, "count": v} for k, v in heatmap.items()]
    const entry = heatmap.find((h) => h.date === dateStr);
    // 新陣列裡每個元素長這樣
    return {
      date: dateStr,
      day: day,
      count: entry ? entry.count : 0  // 那一天練了多少動作
    };
  });

  // 判斷 Heatmap 格子的顏色
  const getHeatmapColor = (count) => {
    if (count === 0) return 'bg-gray-100';
    return 'bg-blue-600 text-white font-bold'; // 只要有訓練就顯示深藍色
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-6xl mx-auto space-y-6">
        <header className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">總覽儀表板</h1>
            <p className="text-gray-500">歡迎回來！這是你今日與近期的狀態概覽。</p>
          </div>
        </header>

        {/* --- Layer 1: 每日飲食 --- */}
        <div className="bg-white p-8 rounded-3xl shadow-sm border border-gray-100 flex flex-col lg:flex-row items-center gap-12">
          {/* 左側：大圓餅圖 */}
          <div className="w-full lg:w-3/5 h-[350px]">
            <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center">
              <Utensils className="mr-2 text-indigo-500" size={24} /> 今日營養攝取分佈
            </h3>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={nutritionChartData}
                  cx="40%"
                  cy="40%"
                  innerRadius={80}  // 圓環內部半徑
                  outerRadius={110}  // 圓環外部半徑
                  paddingAngle={3}  // 每個扇形之間的間距
                  dataKey="value"   // 用 value 來決定每個扇形的面積大小
                  label={renderCustomizedLabel}   // 使用上面自定義的標籤函式拉出引導線
                  labelLine={false}
                >
                  {nutritionChartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                {/* 中央顯示每日卡路里的攝取量的文字 */}
                <text x="41%" y="40%" textAnchor="middle" dominantBaseline="middle" className="text-4xl font-black fill-gray-800">
                  {percent}%
                </text>
                <text x="41%" y="49%" textAnchor="middle" dominantBaseline="middle" className="text-xs font-bold fill-gray-400">
                  {totalCals}/{targetCals} kcal
                </text>
                {/* 當滑鼠移上去時出現的浮動視窗 */}
                
              </PieChart>
            </ResponsiveContainer>
          </div>

          {/* 右側：水杯進度設計 */}
          <div className="w-full lg:w-2/5 flex justify-around items-end h-[300px] pb-4">
            {/* 熱量水杯 */}
            <div className="flex flex-col items-center gap-4">
              <div className="relative w-24 h-60 border-4 border-gray-200 rounded-b-3xl rounded-t-lg overflow-hidden bg-gray-50 shadow-inner">
                {/* 水面波浪效果 */}
                <div 
                  className="absolute bottom-0 left-0 w-full bg-blue-400 transition-all duration-1000 ease-in-out"
                  // 若攝取超過 100%，則顯示 100%
                  style={{ height: `${Math.min((nutrition.calories / nutrition.target_calories) * 100, 100)}%` }}
                >
                  <div className="absolute top-0 left-0 w-full h-4 bg-blue-300/50 -translate-y-2 animate-pulse"></div>
                </div>
                {/* 刻度 */}
                <div className="absolute inset-0 flex flex-col justify-between p-2 pointer-events-none">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="w-4 h-0.5 bg-gray-300/50"></div>
                  ))}
                </div>
              </div>
              <div className="text-center">
                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Calories</p>
                <p className="text-lg font-black text-blue-600">{nutrition.calories} kcal</p>
              </div>
            </div>

            {/* 蛋白質水杯 */}
            <div className="flex flex-col items-center gap-4">
              <div className="relative w-24 h-60 border-4 border-gray-200 rounded-b-3xl rounded-t-lg overflow-hidden bg-gray-50 shadow-inner">
                {/* 水面波浪效果 */}
                <div 
                  className="absolute bottom-0 left-0 w-full bg-indigo-500 transition-all duration-1000 ease-in-out"
                  style={{ height: `${Math.min((nutrition.protein / nutrition.target_protein) * 100, 100)}%` }}
                >
                  <div className="absolute top-0 left-0 w-full h-4 bg-indigo-400/50 -translate-y-2 animate-pulse"></div>
                </div>
                {/* 刻度 */}
                <div className="absolute inset-0 flex flex-col justify-between p-2 pointer-events-none">
                  {[...Array(5)].map((_, i) => (
                    <div key={i} className="w-4 h-0.5 bg-gray-300/50"></div>
                  ))}
                </div>
              </div>
              <div className="text-center">
                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">Protein</p>
                <p className="text-lg font-black text-indigo-600">{nutrition.protein} g</p>
              </div>
            </div>
          </div>
        </div>

        {/* --- Layer 2: 訓練資訊 --- */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* 左側: 當月訓練熱點圖 */}
          <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
            <h3 className="text-lg font-bold text-gray-800 mb-4 flex items-center">
              <Activity className="mr-2 text-blue-500" size={20} /> 當月訓練熱點 ({month + 1}月)
            </h3>
            <div className="grid grid-cols-7 gap-2">
              {/* 遍歷 heatmapBoxes，並將每個元素的資訊顯示在熱點圖上 */}
              {heatmapBoxes.map((box, i) => (
                <div 
                  key={i} 
                  // 有紀錄就會有顏色
                  className={`h-10 rounded-lg ${getHeatmapColor(box.count)} transition-all hover:scale-105 cursor-pointer flex items-center justify-center text-[10px] ${box.count > 0 ? 'text-white font-bold' : 'text-gray-400'}`}
                  title={`${box.date}: ${box.count} 次訓練`}
                >
                  {box.day}   {/* 每一個格子內顯示當天是幾號 */}
                </div>
              ))}
            </div>
            <div className="mt-6 flex justify-between items-center text-xs text-gray-400">
              <div className="flex space-x-4">
                <div className="flex items-center"><div className="w-3 h-3 bg-gray-100 rounded mr-1"></div> 未訓練</div>
                <div className="flex items-center"><div className="w-3 h-3 bg-blue-600 rounded mr-1"></div> 已訓練</div>
              </div>
            </div>
          </div>

          {/* 右側: 當月訓練部位雷達圖 */}
          <div className="bg-white p-6 rounded-3xl shadow-sm border border-gray-100">
            <h3 className="text-lg font-bold text-gray-800 mb-2 flex items-center">
              <Dumbbell className="mr-2 text-blue-500" size={20} /> 當月部位平衡 ({month + 1}月)
            </h3>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart cx="50%" cy="50%" outerRadius="80%" data={radarData}>  {/* 下方每個資訊都用到 radarData */}
                  <PolarGrid />
                  <PolarAngleAxis dataKey="subject" />  {/* 雷達圖每個角的標題是 body_part */}
                  <Radar
                    name="訓練頻率"
                    dataKey="A"  // 每個角的強度是 count                    
                    stroke="#3B82F6"
                    fill="#3B82F6"
                    fillOpacity={0.6}
                  />
                  <Tooltip 
                    itemStyle={{ fontSize: '12px', padding: '0px' }} 
                    // 連外框（標題）一起縮小
                    contentStyle={{ padding: '4px 8px' }} 
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* --- Layer 3: GentleCoach's 建議 --- */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="md:col-span-4 bg-white p-6 rounded-3xl shadow-sm border border-gray-100 flex items-start space-x-4">
            <div className="bg-blue-100 p-3 rounded-2xl shrink-0">
              <Target className="text-blue-600" size={24} />
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-800 mb-2 flex items-center">
                GentleCoach's Insight
              </h3>
              <p className="text-gray-600 leading-relaxed italic">
                "{insight}"
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
