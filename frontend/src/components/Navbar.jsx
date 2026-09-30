import React from 'react';
import { 
  Bell, 
  Moon, 
  Sun, 
  Send, 
  CheckCircle2, 
  AlertCircle,
  PlusCircle,
  TrendingDown
} from 'lucide-react';

export default function Navbar({ 
  isDark, 
  toggleDarkMode, 
  onOpenAddModal, 
  onOpenTelegramModal,
  onOpenLazadaSession,
  telegramStatus 
}) {
  return (
    <header className="sticky top-0 z-30 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Title */}
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-orange-500 to-rose-500 flex items-center justify-center text-white shadow-md shadow-orange-500/20">
              <TrendingDown className="h-6 w-6 stroke-[2.5]" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-extrabold text-lg sm:text-xl tracking-tight bg-gradient-to-r from-orange-600 via-rose-600 to-pink-600 bg-clip-text text-transparent">
                  Lazada Price Tracker
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 text-[10px] font-bold bg-orange-100 text-orange-700 dark:bg-orange-950/60 dark:text-orange-300 rounded-full uppercase tracking-wider">
                  PRO
                </span>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 hidden sm:block">
                Tự động theo dõi giá & nhận thông báo Telegram 24/7
              </p>
            </div>
          </div>

          {/* Right Action buttons */}
          <div className="flex items-center space-x-2 sm:space-x-3">
            
            {/* Telegram Status / Test Button */}
            <button
              onClick={onOpenTelegramModal}
              className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border ${
                telegramStatus?.configured 
                  ? 'bg-sky-50 text-sky-700 border-sky-200 hover:bg-sky-100 dark:bg-sky-950/40 dark:text-sky-300 dark:border-sky-800' 
                  : 'bg-amber-50 text-amber-700 border-amber-200 hover:bg-amber-100 dark:bg-amber-950/40 dark:text-amber-300 dark:border-amber-800'
              }`}
              title="Cấu hình & kiểm tra kết nối Telegram Bot"
            >
              <Send className="h-3.5 w-3.5" />
              <span className="hidden md:inline">Telegram:</span>
              <span className="flex items-center">
                {telegramStatus?.configured ? (
                  <>
                    <CheckCircle2 className="h-3 w-3 text-emerald-500 mr-1" />
                    <span>Đã kết nối</span>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-3 w-3 text-amber-500 mr-1" />
                    <span>Chưa cấu hình</span>
                  </>
                )}
              </span>
            </button>

            {/* Dark Mode Toggle */}
            <button onClick={onOpenLazadaSession} className="px-3 py-2 rounded-lg text-xs font-semibold border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800" title="Cập nhật cookie/session Lazada local">
              Session Lazada
            </button>

            {/* Dark Mode Toggle */}
            <button
              onClick={toggleDarkMode}
              className="p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Chuyển đổi giao diện Sáng / Tối"
            >
              {isDark ? <Sun className="h-5 w-5 text-amber-400" /> : <Moon className="h-5 w-5 text-slate-600" />}
            </button>

            {/* Add Product Button */}
            <button
              onClick={onOpenAddModal}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-sm font-bold text-white bg-gradient-to-r from-orange-500 to-rose-500 hover:from-orange-600 hover:to-rose-600 shadow-md shadow-orange-500/25 transition-all transform active:scale-95"
            >
              <PlusCircle className="h-4 w-4" />
              <span>Thêm sản phẩm</span>
            </button>
          </div>

        </div>
      </div>
    </header>
  );
}
