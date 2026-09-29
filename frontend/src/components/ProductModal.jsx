import React, { useState } from 'react';
import { 
  X, 
  Link as LinkIcon, 
  Search, 
  Loader2, 
  CheckCircle2, 
  Tag, 
  Target, 
  Percent, 
  ArrowDownRight, 
  TrendingUp, 
  Crown,
  AlertCircle
} from 'lucide-react';
import { productService } from '../services/api';
import { formatCurrency } from '../utils/formatters';

export default function ProductModal({ isOpen, onClose, onSuccess }) {
  const [url, setUrl] = useState('');
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [previewData, setPreviewData] = useState(null);
  const [error, setError] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Multi-alert selection state
  const [ruleTargetPrice, setRuleTargetPrice] = useState(true);
  const [targetPriceVal, setTargetPriceVal] = useState('');
  const [rulePriceDrop, setRulePriceDrop] = useState(true);
  const [rulePriceIncrease, setRulePriceIncrease] = useState(false);
  const [rulePercentDrop, setRulePercentDrop] = useState(false);
  const [percentDropVal, setPercentDropVal] = useState('10');
  const [ruleNewLowest, setRuleNewLowest] = useState(true);

  if (!isOpen) return null;

  const handleFetchPreview = async (e) => {
    if (e) e.preventDefault();
    if (!url.trim()) {
      setError('Vui lòng nhập đường dẫn URL sản phẩm Lazada.');
      return;
    }

    setError(null);
    setLoadingPreview(true);
    setPreviewData(null);

    try {
      const data = await productService.preview(url.trim());
      if (data.success && data.price > 0) {
        setPreviewData(data);
        // Default target price = 90% of current price rounded
        setTargetPriceVal(Math.round(data.price * 0.9).toString());
      } else {
        setError(data.error_message || 'Không thể lấy thông tin giá từ Lazada URL này.');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Lỗi kết nối khi lấy thông tin sản phẩm.');
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleCreateProduct = async () => {
    if (!previewData) return;
    setError(null);
    setIsSubmitting(true);

    try {
      const alerts = [];

      if (ruleTargetPrice) {
        const val = parseInt(targetPriceVal.replace(/[^\d]/g, ''), 10);
        if (!isNaN(val) && val > 0) {
          alerts.push({
            alert_type: 'TARGET_PRICE',
            target_price: val,
            enabled: true,
          });
        }
      }

      if (rulePriceDrop) {
        alerts.push({
          alert_type: 'PRICE_DROP',
          enabled: true,
        });
      }

      if (rulePriceIncrease) {
        alerts.push({
          alert_type: 'PRICE_INCREASE',
          enabled: true,
        });
      }

      if (rulePercentDrop) {
        const pct = parseFloat(percentDropVal);
        if (!isNaN(pct) && pct > 0) {
          alerts.push({
            alert_type: 'PERCENT_DROP',
            percentage: pct,
            enabled: true,
          });
        }
      }

      if (ruleNewLowest) {
        alerts.push({
          alert_type: 'NEW_LOWEST_PRICE',
          enabled: true,
        });
      }

      const payload = {
        url: previewData.url,
        name: previewData.name,
        image_url: previewData.image_url,
        current_price: previewData.price,
        original_price: previewData.original_price,
        alerts: alerts,
      };

      await productService.create(payload);
      onSuccess();
      handleClose();
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể lưu sản phẩm. Vui lòng thử lại.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleClose = () => {
    setUrl('');
    setPreviewData(null);
    setError(null);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="relative w-full max-w-xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden max-h-[90vh] flex flex-col">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800">
          <div className="flex items-center space-x-2">
            <div className="h-8 w-8 rounded-xl bg-orange-100 dark:bg-orange-950/60 flex items-center justify-center text-orange-600 dark:text-orange-400">
              <LinkIcon className="h-4 w-4" />
            </div>
            <h3 className="font-extrabold text-base sm:text-lg text-slate-800 dark:text-slate-100">
              Thêm sản phẩm Lazada để theo dõi
            </h3>
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-5 flex-1">
          
          {/* Step 1: URL input */}
          <form onSubmit={handleFetchPreview} className="space-y-2">
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Dán đường dẫn sản phẩm Lazada (URL)
            </label>
            <div className="flex gap-2">
              <div className="relative flex-1">
                <input
                  type="url"
                  placeholder="https://www.lazada.vn/products/..."
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  className="w-full px-4 py-2.5 rounded-2xl text-sm bg-slate-50 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500 transition-all"
                  required
                />
              </div>
              <button
                type="submit"
                disabled={loadingPreview || !url.trim()}
                className="px-4 py-2.5 rounded-2xl bg-slate-900 hover:bg-slate-800 dark:bg-slate-100 dark:hover:bg-white text-white dark:text-slate-900 text-sm font-bold flex items-center space-x-1.5 transition-colors disabled:opacity-50"
              >
                {loadingPreview ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Search className="h-4 w-4" />
                    <span>Lấy tin</span>
                  </>
                )}
              </button>
            </div>
          </form>

          {/* Error display */}
          {error && (
            <div className="p-3.5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/60 text-rose-700 dark:text-rose-300 text-xs flex items-start space-x-2">
              <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Step 2: Product Preview Card */}
          {previewData && (
            <div className="space-y-5 animate-in fade-in duration-300">
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 flex space-x-4">
                {previewData.image_url ? (
                  <img
                    src={previewData.image_url}
                    alt={previewData.name}
                    className="w-20 h-20 rounded-xl object-cover border border-slate-200 dark:border-slate-700 flex-shrink-0"
                  />
                ) : (
                  <div className="w-20 h-20 rounded-xl bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-slate-400">
                    <Tag className="h-8 w-8" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <h4 className="text-xs sm:text-sm font-bold text-slate-800 dark:text-slate-100 line-clamp-2 mb-1.5">
                    {previewData.name}
                  </h4>
                  <div className="flex items-baseline space-x-2">
                    <span className="text-lg font-black text-rose-600 dark:text-rose-400">
                      {previewData.formatted_price}
                    </span>
                    {previewData.formatted_original_price && (
                      <span className="text-xs text-slate-400 line-through">
                        {previewData.formatted_original_price}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {/* Step 3: Configure Multi-rule Alerts */}
              <div className="space-y-3">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block">
                  🔔 Chọn các điều kiện thông báo qua Telegram
                </span>

                <div className="space-y-2.5 bg-slate-50/50 dark:bg-slate-800/30 p-4 rounded-2xl border border-slate-200/80 dark:border-slate-800">
                  
                  {/* Rule 1: Target price */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <label className="flex items-center space-x-2 text-xs font-semibold text-slate-800 dark:text-slate-200 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={ruleTargetPrice}
                        onChange={(e) => setRuleTargetPrice(e.target.checked)}
                        className="rounded text-orange-500 focus:ring-orange-400 h-4 w-4"
                      />
                      <span>Thông báo khi giá ≤ Mức mục tiêu:</span>
                    </label>
                    {ruleTargetPrice && (
                      <div className="flex items-center space-x-1.5">
                        <input
                          type="number"
                          value={targetPriceVal}
                          onChange={(e) => setTargetPriceVal(e.target.value)}
                          placeholder="VD: 1000000"
                          className="w-32 px-2.5 py-1 text-xs font-bold text-right rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-emerald-600 dark:text-emerald-400 focus:outline-none focus:ring-1 focus:ring-orange-500"
                        />
                        <span className="text-xs font-bold text-slate-400">đ</span>
                      </div>
                    )}
                  </div>

                  {/* Rule 2: Price drop */}
                  <label className="flex items-center space-x-2 p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-800 dark:text-slate-200 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rulePriceDrop}
                      onChange={(e) => setRulePriceDrop(e.target.checked)}
                      className="rounded text-orange-500 focus:ring-orange-400 h-4 w-4"
                    />
                    <span>Bất kỳ khi nào giá giảm (Price decreases)</span>
                  </label>

                  {/* Rule 3: Percent drop */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                    <label className="flex items-center space-x-2 text-xs font-semibold text-slate-800 dark:text-slate-200 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={rulePercentDrop}
                        onChange={(e) => setRulePercentDrop(e.target.checked)}
                        className="rounded text-orange-500 focus:ring-orange-400 h-4 w-4"
                      />
                      <span>Giảm sâu ít nhất:</span>
                    </label>
                    {rulePercentDrop && (
                      <div className="flex items-center space-x-1.5">
                        <input
                          type="number"
                          value={percentDropVal}
                          onChange={(e) => setPercentDropVal(e.target.value)}
                          min="1"
                          max="90"
                          className="w-16 px-2.5 py-1 text-xs font-bold text-right rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-orange-600 dark:text-orange-400 focus:outline-none focus:ring-1 focus:ring-orange-500"
                        />
                        <span className="text-xs font-bold text-slate-400">%</span>
                      </div>
                    )}
                  </div>

                  {/* Rule 4: Historical Lowest */}
                  <label className="flex items-center space-x-2 p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-800 dark:text-slate-200 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={ruleNewLowest}
                      onChange={(e) => setRuleNewLowest(e.target.checked)}
                      className="rounded text-orange-500 focus:ring-orange-400 h-4 w-4"
                    />
                    <span>Kỷ lục giá thấp nhất lịch sử (New historical low)</span>
                  </label>

                  {/* Rule 5: Price increase */}
                  <label className="flex items-center space-x-2 p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-semibold text-slate-800 dark:text-slate-200 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={rulePriceIncrease}
                      onChange={(e) => setRulePriceIncrease(e.target.checked)}
                      className="rounded text-orange-500 focus:ring-orange-400 h-4 w-4"
                    />
                    <span>Bất kỳ khi nào giá tăng (Price increases)</span>
                  </label>

                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer actions */}
        <div className="p-4 sm:p-6 border-t border-slate-100 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-900/60 flex items-center justify-end space-x-3">
          <button
            onClick={handleClose}
            className="px-4 py-2.5 rounded-2xl text-xs font-bold text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
          >
            Hủy bỏ
          </button>
          <button
            onClick={handleCreateProduct}
            disabled={!previewData || isSubmitting}
            className="px-6 py-2.5 rounded-2xl text-xs sm:text-sm font-extrabold text-white bg-gradient-to-r from-orange-500 to-rose-500 hover:from-orange-600 hover:to-rose-600 shadow-md shadow-orange-500/25 transition-all disabled:opacity-50 flex items-center space-x-2"
          >
            {isSubmitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Đang lưu...</span>
              </>
            ) : (
              <>
                <CheckCircle2 className="h-4 w-4" />
                <span>BẮT ĐẦU THEO DÕI (START TRACKING)</span>
              </>
            )}
          </button>
        </div>

      </div>
    </div>
  );
}
