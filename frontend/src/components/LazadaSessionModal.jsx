import React, { useEffect, useState } from 'react';
import { X, KeyRound } from 'lucide-react';
import { lazadaSessionService } from '../services/api';

export default function LazadaSessionModal({ onClose, onSaved }) {
  const [value, setValue] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState(null);
  useEffect(() => { lazadaSessionService.status().then(setStatus).catch(() => {}); }, []);
  const save = async () => {
    try {
      setSaving(true); setError('');
      const parsed = JSON.parse(value);
      const cookies = Array.isArray(parsed) ? parsed : (parsed.cookies || []);
      await lazadaSessionService.save(cookies);
      onSaved(); onClose();
    } catch (e) { setError(e.response?.data?.detail || 'Cookie JSON không hợp lệ'); }
    finally { setSaving(false); }
  };
  const remove = async () => {
    await lazadaSessionService.clear();
    setStatus({ exists: false, cookie_count: 0, expired_count: 0 });
  };
  return <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
    <div className="bg-white dark:bg-slate-900 rounded-2xl w-full max-w-2xl p-6 shadow-xl">
      <div className="flex justify-between items-center mb-4"><h2 className="text-lg font-bold flex gap-2 items-center"><KeyRound className="text-orange-500"/> Session Lazada local</h2><button onClick={onClose}><X/></button></div>
      <p className="text-sm text-slate-500 mb-3">Dán JSON cookies từ trình duyệt. Dữ liệu chỉ gửi tới backend local và không được log/đưa vào Telegram.</p>
      <div className="mb-3 rounded-xl bg-slate-100 dark:bg-slate-800 p-3 text-sm">
        {status?.exists ? `Đã có ${status.cookie_count} cookies${status.expired_count ? `, hết hạn ${status.expired_count}` : ''}.` : 'Chưa có cookie Lazada.'}
        <button onClick={remove} disabled={!status?.exists} className="ml-3 text-red-600 font-semibold disabled:opacity-40">Xóa cookie</button>
      </div>
      <textarea value={value} onChange={e => setValue(e.target.value)} rows={10} className="w-full rounded-xl border p-3 text-xs font-mono dark:bg-slate-800" placeholder='[{"name":"...","value":"...","domain":".lazada.vn","path":"/"}]'/>
      {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
      <div className="flex justify-end gap-2 mt-4"><button onClick={onClose} className="px-4 py-2">Hủy</button><button disabled={saving} onClick={save} className="px-4 py-2 rounded-xl bg-orange-500 text-white">{saving ? 'Đang lưu...' : 'Lưu session local'}</button></div>
    </div>
  </div>;
}
