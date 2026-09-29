import React, { useState } from 'react';
import { 
  Bell, 
  Plus, 
  Trash2, 
  Check, 
  Power, 
  Target, 
  TrendingDown, 
  TrendingUp, 
  Percent, 
  Crown,
  Loader2 
} from 'lucide-react';
import { alertService } from '../services/api';
import { formatCurrency, formatDate } from '../utils/formatters';

export default function AlertManager({ 
  productId, 
  alerts = [], 
  onAlertsChange,
  currentPrice 
}) {
  const [addingType, setAddingType] = useState('TARGET_PRICE');
  const [targetPriceInput, setTargetPriceInput] = useState(
    currentPrice ? Math.round(currentPrice * 0.9).toString() : '1000000'
  );
  const [percentageInput, setPercentageInput] = useState('10');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);

  const alertTypeConfig = {
    TARGET_PRICE: {
      label: 'Giá mục tiêu (<= Target)',
      icon: Target,
      desc: 'Thông báo khi giá giảm bằng hoặc thấp hơn mức bạn đặt',
      color: 'text-emerald-500 bg-emerald-50 dark:bg-emerald-950/40 border-emerald-200 dark:border-emerald-800',
    },
    PRICE_DROP: {
      label: 'Bất kỳ khi nào giá giảm',
      icon: TrendingDown,
      desc: 'Thông báo mỗi khi giá giảm so với lần kiểm tra trước',
      color: 'text-rose-500 bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-800',
    },
    PRICE_INCREASE: {
      label: 'Bất kỳ khi nào giá tăng',
      icon: TrendingUp,
      desc: 'Thông báo khi giá có xu hướng tăng',
      color: 'text-blue-500 bg-blue-50 dark:bg-blue-950/40 border-blue-200 dark:border-blue-800',
    },
    PERCENT_DROP: {
      label: 'Giảm ít nhất X%',
      icon: Percent,
      desc: 'Thông báo khi giá giảm sâu ít nhất X% so với lần trước',
      color: 'text-amber-500 bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800',
    },
    NEW_LOWEST_PRICE: {
      label: 'Kỷ lục giá thấp nhất lịch sử',
      icon: Crown,
      desc: 'Thông báo khi giá thấp hơn toàn bộ lịch sử theo dõi',
      color: 'text-purple-500 bg-purple-50 dark:bg-purple-950/40 border-purple-200 dark:border-purple-800',
    },
  };

  const handleAddAlert = async (e) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      const payload = {
        alert_type: addingType,
        enabled: true,
      };

      if (addingType === 'TARGET_PRICE') {
        const val = parseInt(targetPriceInput.replace(/[^\d]/g, ''), 10);
        if (isNaN(val) || val <= 0) {
          setError('Vui lòng nhập giá mục tiêu hợp lệ.');
          setIsSubmitting(false);
          return;
        }
        payload.target_price = val;
      } else if (addingType === 'PERCENT_DROP') {
        const pct = parseFloat(percentageInput);
        if (isNaN(pct) || pct <= 0 || pct > 90) {
          setError('Vui lòng nhập phần trăm giảm từ 1% đến 90%.');
          setIsSubmitting(false);
          return;
        }
        payload.percentage = pct;
      }

      await alertService.create(productId, payload);
      onAlertsChange();
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể tạo cảnh báo.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleToggle = async (alert) => {
    try {
      if (alert.enabled) {
        await alertService.disable(alert.id);
      } else {
        await alertService.enable(alert.id);
      }
      onAlertsChange();
    } catch (err) {
      console.error('Failed to toggle alert', err);
    }
  };

  const handleDelete = async (alertId) => {
    try {
      await alertService.delete(alertId);
      onAlertsChange();
    } catch (err) {
      console.error('Failed to delete alert', err);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 sm:p-6 border border-slate-200 dark:border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h4 className="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center">
            <Bell className="h-5 w-5 mr-2 text-amber-500" />
            Quy tắc cảnh báo Telegram
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Hệ thống có cơ chế chống spam thông minh, chỉ gửi khi điều kiện thỏa mãn
          </p>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 rounded-xl bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 text-xs border border-red-200 dark:border-red-900">
          {error}
        </div>
      )}

      {/* Active Alerts List */}
      <div className="space-y-2.5 mb-6">
        {alerts.length === 0 ? (
          <p className="text-xs text-slate-400 py-3 text-center italic">
            Chưa có quy tắc cảnh báo nào được kích hoạt. Hãy tạo một quy tắc bên dưới!
          </p>
        ) : (
          alerts.map((a) => {
            const config = alertTypeConfig[a.alert_type] || {
              label: a.alert_type,
              icon: Bell,
              desc: '',
              color: 'text-slate-500 bg-slate-50 dark:bg-slate-800 border-slate-200',
            };
            const Icon = config.icon;

            return (
              <div
                key={a.id}
                className={`p-3.5 rounded-xl border flex items-center justify-between transition-all ${
                  a.enabled
                    ? 'bg-slate-50 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700'
                    : 'bg-slate-100/50 dark:bg-slate-900/40 border-slate-200/60 opacity-60'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-lg border ${config.color}`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
                        {config.label}
                      </span>
                      {a.target_price && (
                        <span className="px-2 py-0.5 rounded-md text-xs font-black bg-emerald-100 text-emerald-800 dark:bg-emerald-950/80 dark:text-emerald-300">
                          {formatCurrency(a.target_price)}
                        </span>
                      )}
                      {a.percentage && (
                        <span className="px-2 py-0.5 rounded-md text-xs font-black bg-amber-100 text-amber-800 dark:bg-amber-950/80 dark:text-amber-300">
                          ≥ {a.percentage}%
                        </span>
                      )}
                      {a.is_triggered && (
                        <span className="px-1.5 py-0.5 rounded text-[10px] font-bold bg-orange-500 text-white">
                          Đang trigger
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-400 block mt-0.5">
                      {config.desc}
                    </span>
                  </div>
                </div>

                <div className="flex items-center space-x-1.5">
                  <button
                    onClick={() => handleToggle(a)}
                    className={`p-1.5 rounded-lg border text-xs font-medium transition-colors ${
                      a.enabled
                        ? 'bg-emerald-50 text-emerald-600 border-emerald-200 dark:bg-emerald-950/40 dark:border-emerald-800'
                        : 'bg-slate-200 text-slate-500 border-slate-300 dark:bg-slate-800 dark:border-slate-700'
                    }`}
                    title={a.enabled ? 'Đang bật - Bấm để tắt' : 'Đang tắt - Bấm để bật'}
                  >
                    <Power className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => handleDelete(a.id)}
                    className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-950/40 transition-colors"
                    title="Xóa cảnh báo này"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Add New Rule Form */}
      <form onSubmit={handleAddAlert} className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700/60">
        <span className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-3">
          + Thêm điều kiện cảnh báo mới
        </span>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-3">
          {/* Select alert type */}
          <div className="sm:col-span-2">
            <select
              value={addingType}
              onChange={(e) => setAddingType(e.target.value)}
              className="w-full px-3 py-2 rounded-xl text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-500"
            >
              <option value="TARGET_PRICE">🎯 Đạt mức giá mục tiêu (TARGET_PRICE)</option>
              <option value="PRICE_DROP">📉 Khi giá giảm (PRICE_DROP)</option>
              <option value="PERCENT_DROP">🔥 Giảm theo phần trăm (PERCENT_DROP)</option>
              <option value="NEW_LOWEST_PRICE">👑 Giá thấp nhất lịch sử (NEW_LOWEST_PRICE)</option>
              <option value="PRICE_INCREASE">📈 Khi giá tăng (PRICE_INCREASE)</option>
            </select>
          </div>

          {/* Conditional inputs */}
          {addingType === 'TARGET_PRICE' && (
            <div>
              <input
                type="number"
                placeholder="VD: 1000000"
                value={targetPriceInput}
                onChange={(e) => setTargetPriceInput(e.target.value)}
                className="w-full px-3 py-2 rounded-xl text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-500"
                required
              />
            </div>
          )}

          {addingType === 'PERCENT_DROP' && (
            <div className="flex items-center space-x-2">
              <input
                type="number"
                placeholder="10"
                min="1"
                max="90"
                value={percentageInput}
                onChange={(e) => setPercentageInput(e.target.value)}
                className="w-full px-3 py-2 rounded-xl text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-orange-500"
                required
              />
              <span className="text-xs font-bold text-slate-500">%</span>
            </div>
          )}
        </div>

        <button
          type="submit"
          disabled={isSubmitting}
          className="w-full py-2 px-4 rounded-xl text-xs font-bold text-white bg-slate-900 hover:bg-slate-800 dark:bg-orange-600 dark:hover:bg-orange-500 transition-colors flex items-center justify-center space-x-1.5"
        >
          {isSubmitting ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              <Plus className="h-4 w-4" />
              <span>Thêm quy tắc</span>
            </>
          )}
        </button>
      </form>
    </div>
  );
}
