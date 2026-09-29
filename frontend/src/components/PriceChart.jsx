import React, { useState, useEffect } from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine
} from 'recharts';
import { productService } from '../services/api';
import { formatCurrency, formatChartDate, formatDate } from '../utils/formatters';
import { TrendingDown, Calendar, Loader2 } from 'lucide-react';

export default function PriceChart({ productId, targetPrice }) {
  const [range, setRange] = useState('all');
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    const fetchHistory = async () => {
      setLoading(true);
      try {
        const res = await productService.getHistory(productId, range);
        if (isMounted) {
          setData(res.items || []);
        }
      } catch (err) {
        console.error('Failed to load price history', err);
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchHistory();
    return () => {
      isMounted = false;
    };
  }, [productId, range]);

  const ranges = [
    { key: '24h', label: '24 Giờ' },
    { key: '7d', label: '7 Ngày' },
    { key: '30d', label: '30 Ngày' },
    { key: 'all', label: 'Tất cả' },
  ];

  // Calculate min & max for Y-axis domain padding
  const prices = data.map((d) => d.price);
  const minPrice = prices.length ? Math.min(...prices) : 0;
  const maxPrice = prices.length ? Math.max(...prices) : 0;
  const yDomainMin = Math.max(0, Math.floor(minPrice * 0.95));
  const yDomainMax = Math.ceil(maxPrice * 1.05);

  const CustomTooltip = ({ active, payload, label }) => {
    if (active && payload && payload.length) {
      const item = payload[0].payload;
      return (
        <div className="bg-slate-900/95 text-white p-3 rounded-xl shadow-xl border border-slate-700 text-xs backdrop-blur-md">
          <p className="text-slate-400 mb-1 flex items-center">
            <Calendar className="h-3 w-3 mr-1" />
            {formatDate(item.checked_at)}
          </p>
          <p className="text-base font-extrabold text-rose-400">
            {formatCurrency(item.price)}
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 sm:p-6 border border-slate-200 dark:border-slate-800">
      {/* Header & Range Filters */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-6">
        <div>
          <h4 className="text-base font-bold text-slate-800 dark:text-slate-100 flex items-center">
            <TrendingDown className="h-5 w-5 mr-2 text-orange-500" />
            Biến động lịch sử giá
          </h4>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Dữ liệu ghi nhận từ các chu kỳ kiểm tra tự động
          </p>
        </div>

        <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl">
          {ranges.map((r) => (
            <button
              key={r.key}
              onClick={() => setRange(r.key)}
              className={`px-3 py-1 text-xs font-semibold rounded-lg transition-all ${
                range === r.key
                  ? 'bg-white dark:bg-slate-900 text-orange-600 dark:text-orange-400 shadow-sm'
                  : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
            >
              {r.label}
            </button>
          ))}
        </div>
      </div>

      {/* Chart Box */}
      <div className="w-full h-72">
        {loading ? (
          <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
            <Loader2 className="h-8 w-8 animate-spin text-orange-500 mb-2" />
            <span className="text-xs font-medium">Đang tải lịch sử giá...</span>
          </div>
        ) : data.length === 0 ? (
          <div className="w-full h-full flex flex-col items-center justify-center text-slate-400">
            <span className="text-sm font-medium">Chưa có đủ dữ liệu lịch sử giá.</span>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 10, right: 10, left: 10, bottom: 0 }}>
              <defs>
                <linearGradient id="priceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f43f5e" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#f43f5e" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" className="dark:stroke-slate-800" />
              <XAxis
                dataKey="checked_at"
                tickFormatter={formatChartDate}
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                domain={[yDomainMin, yDomainMax]}
                tickFormatter={(val) => `${Math.round(val / 1000)}k`}
                stroke="#94a3b8"
                fontSize={11}
                tickLine={false}
                axisLine={false}
                width={50}
              />
              <Tooltip content={<CustomTooltip />} />
              {targetPrice && (
                <ReferenceLine
                  y={targetPrice}
                  stroke="#10b981"
                  strokeDasharray="4 4"
                  label={{
                    value: `Target: ${formatCurrency(targetPrice)}`,
                    fill: '#10b981',
                    fontSize: 11,
                    position: 'insideBottomRight',
                  }}
                />
              )}
              <Area
                type="monotone"
                dataKey="price"
                stroke="#f43f5e"
                strokeWidth={2.5}
                fillOpacity={1}
                fill="url(#priceGradient)"
                activeDot={{ r: 6, fill: '#e11d48', stroke: '#ffffff', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
