"use client";  // 這裡標記為 Client Component

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Dumbbell, Utensils, MessageSquare, Activity, Settings } from 'lucide-react';

export default function Sidebar() {
    // 取得當前路徑
    const pathname = usePathname();

    return (
        <aside className="w-64 h-screen sticky top-0 flex flex-col bg-white/80 backdrop-blur-md border-r border-orange-100 shadow-sm z-50">
            {/* Logo 區 */}
            <div className="p-8 pb-4">
                <Link href="/">
                    <div className="flex items-center gap-2 cursor-pointer hover:opacity-80 transition-opacity">
                        <Activity className="w-8 h-8 text-orange-500" />
                        <div>
                            <h1 className="text-2xl font-extrabold text-slate-800 leading-none">FlowFit</h1>
                            <p className="text-[10px] text-slate-400 font-bold tracking-[0.2em] mt-0.5 ml-0.5">AI COACH</p>
                        </div>
                    </div>
                </Link>
            </div>

            {/* 導航選單 */}
            <nav className="flex-1 px-4 space-y-2 mt-4">
                {/* active會決定導航按鈕的顏色是否呈現橘色，代表目前頁面 */}
                <NavLink href="/" icon={<LayoutDashboard size={20} />} label="總覽儀表板" active={pathname === "/"} />
                <NavLink href="/workouts" icon={<Dumbbell size={20} />} label="訓練日誌" active={pathname.startsWith("/workouts")} />
                <NavLink href="/food" icon={<Utensils size={20} />} label="飲食追蹤" active={pathname.startsWith("/food")} />
                <NavLink href="/chat" icon={<MessageSquare size={20} />} label="AI 教練" active={pathname.startsWith("/chat")} />
            </nav>

            {/* 底部設定 */}
            <div className="p-4 border-t border-slate-100">
                <button className="flex items-center gap-3 px-4 py-3 w-full text-slate-400 hover:text-slate-600 hover:bg-slate-50 rounded-xl transition-all text-sm font-bold">
                    <Settings size={20} />
                    設定
                </button>
            </div>
        </aside>
    );
}

// 自行封裝 NavLink 組件，在建立導航選單時不用重複程式碼
function NavLink({ href, icon, label, active }) {
    return (
        <Link href={href}>
            <div className={`flex items-center gap-3 px-4 py-3.5 rounded-xl transition-all font-bold text-sm group cursor-pointer ${active
                ? 'bg-orange-100 text-orange-700 shadow-sm'
                : 'text-slate-500 hover:bg-white hover:shadow-sm hover:text-orange-600'
                }`}>
                <span className={`transition-colors ${active ? 'text-orange-600' : 'text-slate-400 group-hover:text-orange-500'}`}>
                    {icon}
                </span>
                {label}
            </div>
        </Link>
    );
}