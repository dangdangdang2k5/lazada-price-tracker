import React, { useState } from 'react';
import { 
  RefreshCw, 
  ExternalLink, 
  TrendingDown, 
  TrendingUp, 
  Target, 
  Trash2, 
  BarChart2, 
  Bell, 
  Clock, 
  ShieldCheck,
  Tag
} from 'lucide-react';
import { formatCurrency, formatDate } from '../utils/formatters';

export default function ProductCard({
  product,
  onRefresh,
  onViewDetails,
  onDelete,
}) {
  const [isRefreshing, setIsRefreshing] = useState(false);

  const handleRefresh = async (e) => {
    e.stopPropagation();
    try {
      setIsRefreshing(true);
      await onRefresh(product.id);
    } finally {
      setIsRefreshing(false);
    }
  };

  const hasDrop = product.price_change_from_prev !== null && product.price_change_from_prev < 0;
  const hasIncrease = product.price_change_from_prev !== null && product.price_change_from_prev > 0;
  const isTargetReached = product.is_target_reached;

  return (
    <div 
      onClick={() => onViewDetails(product)}
      className="group relative bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-xl dark:hover:border-slate-700 transition-all duration-300 flex flex-col overflow-hidden cursor-pointer"
    >
      {/* Top badges */}
      <div className="absolute top-3 left-3 z-10 flex flex-wrap gap-1.5">
        {isTargetReached && (
          <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-extrabold bg-emerald-500 text-white shadow-sm shadow-emerald-500/30 animate-pulse">
            🎯 Đạt Target
          </span>
        )}
        {product.discount_percent && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-rose-600 text-white shadow-sm">
            -{product.discount_percent}%
          </span>
        )}
        {hasDrop && (
          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300">
            <TrendingDown className="h-3 w-3 mr-0.5" />
            {product.price_change_from_prev}%
          </span>
        )}
      </div>

      {/* Product Image */}
      <div className="relative w-full pt-[70%] bg-slate-100 dark:bg-slate-800/60 overflow-hidden">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="absolute inset-0 w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-500"
            onError={(e) => {
              e.target.onerror = null;
              e.target.src = 'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=500&auto=format&fit=crop&q=60';
            }}
          />
        ) : (
          <div className="absolute inset-0 flex items-center justify-center text-slate-400">
            <Tag className="h-12 w-12 stroke-[1.5]" />
          </div>
        )}
        <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>

      {/* Product Info Content */}
      <div className="p-4 sm:p-5 flex-1 flex flex-col justify-between">
        <div>
          {/* Title */}
          <h3 
            className="font-bold text-sm sm:text-base text-slate-800 dark:text-slate-100 line-clamp-2 mb-2 leading-snug group-hover:text-orange-500 transition-colors"
            title={product.name}
          >
            {product.name}
          </h3>

          {/* SKU Variation Badge & Note */}
          {product.sku_name && (
            <div className="mb-2">
              <span className="inline-flex items-center px-2 py-0.5 rounded-lg text-[11px] font-semibold bg-orange-100 text-orange-800 dark:bg-orange-950/80 dark:text-orange-300 border border-orange-200 dark:border-orange-800/60">
                🏷️ {product.sku_name}
              </span>
            </div>
          )}
          {product.note && (
            <p className="text-xs text-slate-500 dark:text-slate-400 italic mb-2 line-clamp-1">
              📝 {product.note}
            </p>
          )}

          {/* Pricing Row */}
          <div className="mb-4">
            <div className="flex items-baseline space-x-2">
              <span className="text-xl sm:text-2xl font-black text-rose-600 dark:text-rose-400">
                {product.formatted_current_price}
              </span>
              {product.original_price && product.original_price > product.current_price && (
                <span className="text-xs sm:text-sm text-slate-400 line-through">
                  {product.formatted_original_price}
                </span>
              )}
            </div>

            {/* Target Price indicator */}
            {product.target_price && (
              <div className="mt-1.5 flex items-center space-x-1 text-xs text-slate-500 dark:text-slate-400">
                <Target className="h-3.5 w-3.5 text-orange-500 flex-shrink-0" />
                <span>Mục tiêu:</span>
                <span className="font-semibold text-slate-700 dark:text-slate-300">
                  {formatCurrency(product.target_price)}
                </span>
              </div>
            )}
          </div>

          {/* Low/High summary */}
          <div className="grid grid-cols-2 gap-2 p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800 text-xs mb-4">
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Thấp nhất:</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400">
                {product.formatted_lowest_price}
              </span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase font-bold">Cao nhất:</span>
              <span className="font-bold text-slate-700 dark:text-slate-300">
                {product.formatted_highest_price}
              </span>
            </div>
          </div>
        </div>

        {/* Footer info & action buttons */}
        <div>
          <div className="flex items-center justify-between text-[11px] text-slate-400 dark:text-slate-500 mb-3 pt-2 border-t border-slate-100 dark:border-slate-800">
            <span className="flex items-center">
              <Clock className="h-3 w-3 mr-1" />
              {formatDate(product.last_checked_at)}
            </span>
            <span className="flex items-center text-slate-500 dark:text-slate-400">
              <Bell className="h-3 w-3 mr-1 text-amber-500" />
              {product.alerts?.length || 0} alert(s)
            </span>
          </div>

          <div className="grid grid-cols-4 gap-1.5" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="col-span-1 p-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center transition-colors"
              title="Cập nhật giá ngay lập tức"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin text-orange-500' : ''}`} />
            </button>
            <a
              href={product.url}
              target="_blank"
              rel="noopener noreferrer"
              className="col-span-1 p-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center transition-colors"
              title="Mở link trên Lazada"
            >
              <ExternalLink className="h-4 w-4" />
            </a>
            <button
              onClick={() => onViewDetails(product)}
              className="col-span-1 p-2 rounded-xl border border-orange-200 dark:border-orange-900/50 bg-orange-50 dark:bg-orange-950/40 hover:bg-orange-100 dark:hover:bg-orange-900/60 text-orange-600 dark:text-orange-300 flex items-center justify-center font-bold text-xs transition-colors"
              title="Xem biểu đồ giá và cấu hình cảnh báo"
            >
              <BarChart2 className="h-4 w-4" />
            </button>
            <button
              onClick={() => onDelete(product.id, product.name)}
              className="col-span-1 p-2 rounded-xl border border-red-200 dark:border-red-900/40 hover:bg-red-50 dark:hover:bg-red-950/40 text-red-500 flex items-center justify-center transition-colors"
              title="Xóa theo dõi sản phẩm"
            >
              <Trash2 className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
