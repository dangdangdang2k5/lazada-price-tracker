import React from 'react';
import { Package, BellRing, Target, ArrowDownRight, Clock } from 'lucide-react';

export default function StatsBar({ stats }) {
  const items = [
    {
      label: 'Sản phẩm đang theo dõi',
      value: stats?.total_products || 0,
      icon: Package,
      gradient: 'from-blue-500 to-indigo-600',
      textColor: 'text-blue-600 dark:text-blue-400',
      bgColor: 'bg-blue-50 dark:bg-blue-950/40',
      borderColor: 'border-blue-100 dark:border-blue-900/50',
    },
    {
      label: 'Đã đạt giá mục tiêu',
      value: stats?.reached_target_count || 0,
      icon: Target,
      gradient: 'from-emerald-500 to-teal-600',
      textColor: 'text-emerald-600 dark:text-emerald-400',
      bgColor: 'bg-emerald-50 dark:bg-emerald-950/40',
      borderColor: 'border-emerald-100 dark:border-emerald-900/50',
      highlight: (stats?.reached_target_count || 0) > 0,
    },
    {
      label: 'Số lần giá giảm',
      value: stats?.price_drops_count || 0,
      icon: ArrowDownRight,
      gradient: 'from-rose-500 to-pink-600',
      textColor: 'text-rose-600 dark:text-rose-400',
      bgColor: 'bg-rose-50 dark:bg-rose-950/40',
      borderColor: 'border-rose-100 dark:border-rose-900/50',
    },
    {
      label: 'Quy tắc cảnh báo active',
      value: stats?.total_alerts_count || 0,
      icon: BellRing,
      gradient: 'from-amber-500 to-orange-600',
      textColor: 'text-amber-600 dark:text-amber-400',
      bgColor: 'bg-amber-50 dark:bg-amber-950/40',
      borderColor: 'border-amber-100 dark:border-amber-900/50',
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 mb-8">
      {items.map((item, idx) => {
        const Icon = item.icon;
        return (
          <div
            key={idx}
            className={`p-4 rounded-2xl border ${item.bgColor} ${item.borderColor} transition-all duration-200 hover:shadow-md flex flex-col justify-between`}
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-slate-600 dark:text-slate-400 line-clamp-1">
                {item.label}
              </span>
              <div className={`p-2 rounded-xl bg-white dark:bg-slate-900 shadow-sm ${item.textColor}`}>
                <Icon className="h-4 w-4" />
              </div>
            </div>
            <div className="flex items-baseline space-x-2">
              <span className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                {item.value}
              </span>
              {item.highlight && (
                <span className="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500 text-white animate-pulse">
                  HOT
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
