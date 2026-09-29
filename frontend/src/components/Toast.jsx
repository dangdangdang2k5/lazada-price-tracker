import React from 'react';
import { CheckCircle, AlertCircle, X } from 'lucide-react';

export default function Toast({ toast, onClose }) {
  if (!toast) return null;

  const isSuccess = toast.type === 'success';

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-in slide-in-from-bottom-5 duration-300">
      <div className={`p-4 rounded-2xl shadow-2xl border flex items-center space-x-3 text-xs sm:text-sm font-semibold max-w-md ${
        isSuccess
          ? 'bg-emerald-900/90 text-white border-emerald-700 backdrop-blur-md'
          : 'bg-rose-900/90 text-white border-rose-700 backdrop-blur-md'
      }`}>
        {isSuccess ? (
          <CheckCircle className="h-5 w-5 text-emerald-400 flex-shrink-0" />
        ) : (
          <AlertCircle className="h-5 w-5 text-rose-400 flex-shrink-0" />
        )}
        <span className="flex-1">{toast.message}</span>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-white/10 text-slate-300 transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
