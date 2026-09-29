import React, { useState } from 'react';
import { 
  X, 
  Send, 
  CheckCircle2, 
  AlertCircle, 
  Loader2, 
  HelpCircle,
  KeyRound,
  MessageSquare
} from 'lucide-react';
import { telegramService } from '../services/api';

export default function TelegramTestModal({ isOpen, onClose, telegramStatus, onTested }) {
  const [botToken, setBotToken] = useState('');
  const [chatId, setChatId] = useState('');
  const [customMsg, setCustomMsg] = useState('');
  const [testing, setTesting] = useState(false);
  const [result, setResult] = useState(null);

  if (!isOpen) return null;

  const handleTest = async (e) => {
    e.preventDefault();
    setTesting(true);
    setResult(null);

    try {
      const payload = {};
      if (botToken.trim()) payload.bot_token = botToken.trim();
      if (chatId.trim()) payload.chat_id = chatId.trim();
      if (customMsg.trim()) payload.custom_message = customMsg.trim();

      const res = await telegramService.testConnection(payload);
      setResult(res);
      if (res.success && onTested) {
        onTested();
      }
    } catch (err) {
      setResult({
        success: false,
        message: err.response?.data?.detail || 'Lỗi khi gửi yêu cầu test Telegram.',
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-lg bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-xl bg-sky-100 dark:bg-sky-950/60 flex items-center justify-center text-sky-600 dark:text-sky-400">
              <Send className="h-4 w-4" />
            </div>
            <h3 className="font-extrabold text-base sm:text-lg text-slate-800 dark:text-slate-100">
              Cấu hình & Test Telegram Bot
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleTest} className="p-6 space-y-4">
          
          {/* Status info box */}
          <div className={`p-4 rounded-2xl border text-xs ${
            telegramStatus?.configured
              ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
              : 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200'
          }`}>
            <div className="flex items-center space-x-2 font-bold mb-1">
              {telegramStatus?.configured ? (
                <>
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  <span>Backend đã nhận cấu hình từ file .env:</span>
                </>
              ) : (
                <>
                  <AlertCircle className="h-4 w-4 text-amber-500" />
                  <span>Chưa cấu hình Telegram trong file .env</span>
                </>
              )}
            </div>
            {telegramStatus?.configured && (
              <div className="space-y-0.5 text-[11px] opacity-90 pl-6">
                <div>Bot Token: <code className="font-mono bg-emerald-100/50 dark:bg-emerald-900/50 px-1 rounded">{telegramStatus.bot_token_masked}</code></div>
                <div>Chat ID: <code className="font-mono bg-emerald-100/50 dark:bg-emerald-900/50 px-1 rounded">{telegramStatus.chat_id}</code></div>
              </div>
            )}
          </div>

          {/* Override inputs */}
          <div className="space-y-3">
            <span className="text-xs font-bold text-slate-600 dark:text-slate-400 block">
              Ghi đè thông tin Test (Tùy chọn nếu đã đặt trong .env):
            </span>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 flex items-center">
                <KeyRound className="h-3.5 w-3.5 mr-1 text-slate-400" />
                Telegram Bot Token:
              </label>
              <input
                type="text"
                placeholder="1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ"
                value={botToken}
                onChange={(e) => setBotToken(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
              />
            </div>

            <div>
              <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1 flex items-center">
                <MessageSquare className="h-3.5 w-3.5 mr-1 text-slate-400" />
                Telegram Chat ID:
              </label>
              <input
                type="text"
                placeholder="VD: 987654321 hoặc @your_channel"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
                className="w-full px-3.5 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
              />
            </div>
          </div>

          {/* Test result status message */}
          {result && (
            <div className={`p-3.5 rounded-2xl border text-xs flex items-start space-x-2 ${
              result.success
                ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
                : 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300'
            }`}>
              {result.success ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-500 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertCircle className="h-4 w-4 text-rose-500 flex-shrink-0 mt-0.5" />
              )}
              <div>
                <p className="font-bold">{result.message}</p>
                {result.chat_title && (
                  <p className="text-[11px] mt-0.5">Tên phòng chat: <b>{result.chat_title}</b></p>
                )}
              </div>
            </div>
          )}

          {/* Guide hint */}
          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 space-y-1">
            <p className="font-bold text-slate-700 dark:text-slate-300 flex items-center">
              <HelpCircle className="h-3.5 w-3.5 mr-1 text-sky-500" />
              Hướng dẫn lấy Token & Chat ID:
            </p>
            <p>1. Mở Telegram, tìm <b>@BotFather</b> và gõ <code>/newbot</code> để tạo bot và lấy <b>Token</b>.</p>
            <p>2. Nhắn tin <code>/start</code> vào bot bạn vừa tạo.</p>
            <p>3. Tìm bot <b>@userinfobot</b> để xem <b>Id (Chat ID)</b> của bạn.</p>
          </div>

          {/* Action buttons */}
          <div className="pt-2 flex justify-end space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            >
              Đóng
            </button>
            <button
              type="submit"
              disabled={testing}
              className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-sky-600 hover:bg-sky-500 shadow-md shadow-sky-500/20 transition-all flex items-center space-x-1.5"
            >
              {testing ? (
                <>
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  <span>Đang gửi test...</span>
                </>
              ) : (
                <>
                  <Send className="h-3.5 w-3.5" />
                  <span>Gửi tin nhắn Test Telegram</span>
                </>
              )}
            </button>
          </div>

        </form>

      </div>
    </div>
  );
}
