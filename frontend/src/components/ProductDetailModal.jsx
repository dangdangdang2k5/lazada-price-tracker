import React, { useState } from 'react';
import { 
  X, 
  ExternalLink, 
  RefreshCw, 
  TrendingDown, 
  Target, 
  Calendar, 
  Tag, 
  Bell, 
  LineChart, 
  ListOrdered 
} from 'lucide-react';
import PriceChart from './PriceChart';
import AlertManager from './AlertManager';
import { formatCurrency, formatDate } from '../utils/formatters';

export default function ProductDetailModal({
  isOpen,
  product,
  onClose,
  onRefresh,
  onProductUpdated,
}) {
  const [activeTab, setActiveTab] = useState('chart'); // 'chart' | 'alerts'
  const [isRefreshing, setIsRefreshing] = useState(false);

  if (!isOpen || !product) return null;

  const handleRefresh = async () => {
    try {
      setIsRefreshing(true);
      await onRefresh(product.id);
    } finally {
      setIsRefreshing(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden max-h-[92vh] flex flex-col">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className="px-2.5 py-1 rounded-full text-xs font-black bg-orange-100 text-orange-700 dark:bg-orange-950 dark:text-orange-300 uppercase tracking-wider">
              Chi tiết theo dõi
            </span>
            <span className="text-xs text-slate-400">ID #{product.id}</span>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-4 sm:p-6 overflow-y-auto space-y-6 flex-1">
          
          {/* Top Info Banner */}
          <div className="flex flex-col sm:flex-row gap-5 p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800">
            {/* Image */}
            <div className="w-full sm:w-36 h-36 rounded-2xl overflow-hidden bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 flex-shrink-0">
              {product.image_url ? (
                <img
                  src={product.image_url}
                  alt={product.name}
                  className="w-full h-full object-cover object-center"
                  onError={(e) => {
                    e.target.onerror = null;
                    e.target.src = 'https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=500&auto=format&fit=crop&q=60';
                  }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center text-slate-400">
                  <Tag className="h-10 w-10" />
                </div>
              )}
            </div>

            {/* Details */}
            <div className="flex-1 flex flex-col justify-between">
              <div>
                <h3 className="text-base sm:text-lg font-bold text-slate-900 dark:text-white leading-tight mb-2">
                  {product.name}
                </h3>

                <div className="flex flex-wrap items-baseline gap-2 mb-3">
                  <span className="text-2xl font-black text-rose-600 dark:text-rose-400">
                    {product.formatted_current_price}
                  </span>
                  {product.original_price && product.original_price > product.current_price && (
                    <span className="text-sm text-slate-400 line-through">
                      {product.formatted_original_price}
                    </span>
                  )}
                  {product.discount_percent && (
                    <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-rose-500 text-white">
                      -{product.discount_percent}%
                    </span>
                  )}
                </div>

                {/* Grid metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2 text-xs">
                  <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-400 text-[10px] block uppercase font-bold">Thấp nhất:</span>
                    <span className="font-bold text-emerald-600 dark:text-emerald-400">
                      {product.formatted_lowest_price}
                    </span>
                  </div>
                  <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <span className="text-slate-400 text-[10px] block uppercase font-bold">Cao nhất:</span>
                    <span className="font-bold text-slate-700 dark:text-slate-300">
                      {product.formatted_highest_price}
                    </span>
                  </div>
                  <div className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 col-span-2 sm:col-span-1">
                    <span className="text-slate-400 text-[10px] block uppercase font-bold">Giá mục tiêu:</span>
                    <span className="font-bold text-orange-600 dark:text-orange-400">
                      {product.target_price ? formatCurrency(product.target_price) : 'Chưa đặt'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Action bar */}
              <div className="flex items-center space-x-2 mt-3 pt-3 border-t border-slate-200 dark:border-slate-700">
                <button
                  onClick={handleRefresh}
                  disabled={isRefreshing}
                  className="px-3 py-1.5 rounded-xl text-xs font-bold bg-slate-900 hover:bg-slate-800 text-white dark:bg-slate-100 dark:hover:bg-white dark:text-slate-900 flex items-center space-x-1.5 transition-colors"
                >
                  <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? 'animate-spin' : ''}`} />
                  <span>Cập nhật giá ngay</span>
                </button>
                <a
                  href={product.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-xl text-xs font-bold border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 flex items-center space-x-1.5 transition-colors"
                >
                  <ExternalLink className="h-3.5 w-3.5" />
                  <span>Xem trên Lazada</span>
                </a>
              </div>
            </div>
          </div>

          {/* Navigation Tabs */}
          <div className="flex border-b border-slate-200 dark:border-slate-800">
            <button
              onClick={() => setActiveTab('chart')}
              className={`flex items-center space-x-2 py-2.5 px-4 text-xs sm:text-sm font-bold border-b-2 transition-all ${
                activeTab === 'chart'
                  ? 'border-orange-500 text-orange-600 dark:text-orange-400'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
              }`}
            >
              <LineChart className="h-4 w-4" />
              <span>Biểu đồ & Lịch sử giá</span>
            </button>
            <button
              onClick={() => setActiveTab('alerts')}
              className={`flex items-center space-x-2 py-2.5 px-4 text-xs sm:text-sm font-bold border-b-2 transition-all ${
                activeTab === 'alerts'
                  ? 'border-orange-500 text-orange-600 dark:text-orange-400'
                  : 'border-transparent text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
              }`}
            >
              <Bell className="h-4 w-4" />
              <span>Quản lý Cảnh báo Telegram ({product.alerts?.length || 0})</span>
            </button>
          </div>

          {/* Tab Content */}
          {activeTab === 'chart' ? (
            <PriceChart productId={product.id} targetPrice={product.target_price} />
          ) : (
            <AlertManager
              productId={product.id}
              alerts={product.alerts || []}
              currentPrice={product.current_price}
              onAlertsChange={onProductUpdated}
            />
          )}

        </div>

      </div>
    </div>
  );
}
