// app/layout.js
import { Inter } from "next/font/google";
import "./globals.css";
import Sidebar from "./sidebar"; // 引入 sidebar 定義的組件

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
    title: "FlowFit - AI Fitness Coach",
    description: "Track your workouts with AI",
};

// 接收 children 作為參數，代表目前在哪個頁面，需要渲染那個頁面的內容
export default function RootLayout({ children }) {
    return (
        <html lang="zh-TW">
            <body className={`${inter.className} flex min-h-screen bg-gradient-to-br from-orange-50 via-amber-50 to-yellow-50 text-slate-800`}>

                {/* 左側區域使用拆分出來的 sidebar 組件 */}
                <Sidebar />

                {/* 右側內容區 */}
                <main className="flex-1 relative z-10 overflow-x-hidden">
                    {/* 背景裝飾 */}
                    <div className="fixed inset-0 z-0 pointer-events-none">
                        <div className="absolute top-[-10%] left-[-20%] w-[500px] h-[500px] bg-orange-200 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob"></div>
                        <div className="absolute bottom-[-10%] right-[-20%] w-[500px] h-[500px] bg-yellow-200 rounded-full mix-blend-multiply filter blur-3xl opacity-40 animate-blob animation-delay-2000"></div>
                    </div>

                    {children}
                </main>
            </body>
        </html>
    );
}