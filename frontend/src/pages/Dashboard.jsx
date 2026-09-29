import React, { useState, useEffect, useCallback } from 'react';
import { 
  Search, 
  SlidersHorizontal, 
  Filter, 
  PlusCircle, 
  PackageSearch, 
  RefreshCw,
  Loader2,
  TrendingDown,
  Target
} from 'lucide-react';
import Navbar from '../components/Navbar';
import StatsBar from '../components/StatsBar';
import ProductCard from '../components/ProductCard';
import ProductModal from '../components/ProductModal';
import ProductDetailModal from '../components/ProductDetailModal';
import TelegramTestModal from '../components/TelegramTestModal';
import Toast from '../components/Toast';
import { useDarkMode } from '../hooks/useDarkMode';
import { productService, statsService, telegramService } from '../services/api';

export default function Dashboard() {
  const [isDark, toggleDarkMode] = useDarkMode();

  // State
  const [products, setProducts] = useState([]);
  const [stats, setStats] = useState(null);
  const [telegramStatus, setTelegramStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  // Filters & Search
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('');
  const [filterStatus, setFilterStatus] = useState('');

  // Modals
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isTelegramOpen, setIsTelegramOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [isDetailOpen, setIsDetailOpen] = useState(false);

  // Notifications
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 4000);
  };

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      const [prodRes, statRes, teleRes] = await Promise.all([
        productService.list({ search, sort_by: sortBy, filter_status: filterStatus }),
        statsService.getStats(),
        telegramService.getStatus(),
      ]);

      setProducts(prodRes.items || []);
      setStats(statRes);
      setTelegramStatus(teleRes);
    } catch (err) {
      console.error('Failed to load dashboard data', err);
      showToast('Không thể tải dữ liệu từ máy chủ.', 'error');
    } finally {
      setLoading(false);
    }
  }, [search, sortBy, filterStatus]);

  useEffect(() => {
    const timer = setTimeout(() => {
      loadData();
    }, 250);
    return () => clearTimeout(timer);
  }, [loadData]);

  // Single product refresh handler
  const handleRefreshProduct = async (id) => {
    try {
      const updated = await productService.refresh(id);
      showToast(`Đã làm mới giá cho sản phẩm: ${updated.name.slice(0, 30)}...`);
      // Update item in place
      setProducts((prev) => prev.map((p) => (p.id === id ? updated : p)));
      // If currently viewing detail, update it too
      if (selectedProduct && selectedProduct.id === id) {
        setSelectedProduct(updated);
      }
      // Refresh stats
      const newStats = await statsService.getStats();
      setStats(newStats);
    } catch (err) {
      showToast('Không thể làm mới giá sản phẩm.', 'error');
    }
  };

  // Delete product handler
  const handleDeleteProduct = async (id, name) => {
    if (window.confirm(`Bạn có chắc muốn xóa theo dõi sản phẩm "${name.slice(0, 40)}..."?`)) {
      try {
        await productService.delete(id);
        showToast('Đã xóa sản phẩm khỏi danh sách theo dõi.');
        loadData();
        if (isDetailOpen && selectedProduct?.id === id) {
          setIsDetailOpen(false);
        }
      } catch (err) {
        showToast('Lỗi khi xóa sản phẩm.', 'error');
      }
    }
  };

  // Open detail modal
  const handleViewDetails = async (product) => {
    try {
      const full = await productService.getById(product.id);
      setSelectedProduct(full);
      setIsDetailOpen(true);
    } catch (err) {
      setSelectedProduct(product);
      setIsDetailOpen(true);
    }
  };

  // Refresh single product details after alert changes
  const handleProductUpdated = async () => {
    if (selectedProduct) {
      const refreshed = await productService.getById(selectedProduct.id);
      setSelectedProduct(refreshed);
      setProducts((prev) => prev.map((p) => (p.id === refreshed.id ? refreshed : p)));
      const newStats = await statsService.getStats();
      setStats(newStats);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 transition-colors">
      
      {/* Top Navbar */}
      <Navbar
        isDark={isDark}
        toggleDarkMode={toggleDarkMode}
        onOpenAddModal={() => setIsAddOpen(true)}
        onOpenTelegramModal={() => setIsTelegramOpen(true)}
        telegramStatus={telegramStatus}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* KPI Metrics */}
        <StatsBar stats={stats} />

        {/* Filters and Controls Toolbar */}
        <div className="bg-white dark:bg-slate-900 rounded-2xl p-4 border border-slate-200 dark:border-slate-800 shadow-sm mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          
          {/* Search box */}
          <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
            <input
              type="text"
              placeholder="Tìm kiếm sản phẩm theo tên..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-10 pr-4 py-2 text-xs sm:text-sm rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-orange-500"
            />
          </div>

          {/* Quick Filter Tabs & Sort Selection */}
          <div className="flex flex-wrap items-center gap-2">
            
            {/* Filter mode */}
            <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-xl text-xs font-semibold">
              <button
                onClick={() => setFilterStatus('')}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  filterStatus === ''
                    ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-sm'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
                }`}
              >
                Tất cả
              </button>
              <button
                onClick={() => setFilterStatus('target_reached')}
                className={`px-3 py-1.5 rounded-lg transition-all flex items-center space-x-1 ${
                  filterStatus === 'target_reached'
                    ? 'bg-emerald-500 text-white shadow-sm'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
                }`}
              >
                <Target className="h-3 w-3" />
                <span>Đạt Target</span>
              </button>
              <button
                onClick={() => setFilterStatus('price_drop')}
                className={`px-3 py-1.5 rounded-lg transition-all flex items-center space-x-1 ${
                  filterStatus === 'price_drop'
                    ? 'bg-rose-500 text-white shadow-sm'
                    : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-300'
                }`}
              >
                <TrendingDown className="h-3 w-3" />
                <span>Đang giảm giá</span>
              </button>
            </div>

            {/* Sort Dropdown */}
            <div className="flex items-center space-x-1.5 bg-slate-50 dark:bg-slate-800 px-3 py-1 rounded-xl border border-slate-200 dark:border-slate-700">
              <SlidersHorizontal className="h-3.5 w-3.5 text-slate-400" />
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-transparent text-xs font-semibold text-slate-700 dark:text-slate-300 focus:outline-none cursor-pointer"
              >
                <option value="">Sắp xếp mặc định</option>
                <option value="price_asc">Giá tăng dần</option>
                <option value="price_desc">Giá giảm dần</option>
                <option value="discount_desc">% Giảm giá cao nhất</option>
                <option value="drop_desc">Mức giảm vừa qua</option>
              </select>
            </div>

            {/* Manual Refresh All Button */}
            <button
              onClick={loadData}
              className="p-2 rounded-xl border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors"
              title="Làm mới danh sách"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-orange-500' : ''}`} />
            </button>

          </div>

        </div>

        {/* Product Cards Grid or Loading/Empty State */}
        {loading && products.length === 0 ? (
          <div className="py-20 flex flex-col items-center justify-center text-slate-400">
            <Loader2 className="h-10 w-10 animate-spin text-orange-500 mb-3" />
            <p className="text-sm font-semibold">Đang tải danh sách sản phẩm theo dõi...</p>
          </div>
        ) : products.length === 0 ? (
          <div className="py-16 px-4 bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 text-center shadow-sm max-w-lg mx-auto">
            <div className="w-16 h-16 rounded-2xl bg-orange-100 dark:bg-orange-950/60 text-orange-600 dark:text-orange-400 flex items-center justify-center mx-auto mb-4">
              <PackageSearch className="h-8 w-8" />
            </div>
            <h3 className="text-lg font-extrabold text-slate-800 dark:text-slate-100 mb-2">
              Chưa có sản phẩm nào được theo dõi
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mb-6 leading-relaxed">
              Dán URL bất kỳ sản phẩm nào từ Lazada để hệ thống tự động kiểm tra giá định kỳ và gửi thông báo khi có biến động giá.
            </p>
            <button
              onClick={() => setIsAddOpen(true)}
              className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-2xl text-xs sm:text-sm font-bold text-white bg-gradient-to-r from-orange-500 to-rose-500 hover:from-orange-600 hover:to-rose-600 shadow-md shadow-orange-500/25 transition-all"
            >
              <PlusCircle className="h-4 w-4" />
              <span>Thêm sản phẩm đầu tiên</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 sm:gap-6">
            {products.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
                onRefresh={handleRefreshProduct}
                onViewDetails={handleViewDetails}
                onDelete={handleDeleteProduct}
              />
            ))}
          </div>
        )}

      </main>

      {/* Modals */}
      <ProductModal
        isOpen={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        onSuccess={() => {
          showToast('Đã thêm sản phẩm vào danh sách theo dõi!');
          loadData();
        }}
      />

      <ProductDetailModal
        isOpen={isDetailOpen}
        product={selectedProduct}
        onClose={() => setIsDetailOpen(false)}
        onRefresh={handleRefreshProduct}
        onProductUpdated={handleProductUpdated}
      />

      <TelegramTestModal
        isOpen={isTelegramOpen}
        onClose={() => setIsTelegramOpen(false)}
        telegramStatus={telegramStatus}
        onTested={loadData}
      />

      {/* Toast Notification */}
      <Toast toast={toast} onClose={() => setToast(null)} />

    </div>
  );
}
