import React, { useEffect, useState } from 'react';
import { ArrowDown, ArrowUp, CheckCircle2, KeyRound, PauseCircle, Play, Plus, Trash2, X } from 'lucide-react';
import { lazadaSessionService } from '../services/api';

const statusStyle = {
  VALID: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300',
  UNKNOWN: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
  EXPIRED: 'bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300',
};

export default function LazadaSessionModal({ onClose, onSaved }) {
  const [value, setValue] = useState('');
  const [label, setLabel] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [data, setData] = useState({ profiles: [], paused: false, active_profile_id: null });

  const load = async () => {
    try { setData(await lazadaSessionService.listProfiles()); } catch { setError('Không thể đọc danh sách cookie.'); }
  };
  useEffect(() => { load(); }, []);

  const parseCookies = () => {
    const parsed = JSON.parse(value);
    return Array.isArray(parsed) ? parsed : (parsed.cookies || []);
  };

  const add = async () => {
    try {
      setSaving(true); setError('');
      await lazadaSessionService.addProfile(label.trim() || `Cookie ${data.profiles.length + 1}`, parseCookies());
      setValue(''); setLabel(''); await load(); onSaved?.();
    } catch (e) { setError(e.response?.data?.detail || 'Cookie JSON không hợp lệ'); }
    finally { setSaving(false); }
  };

  const activate = async (id) => {
    try { setError(''); await lazadaSessionService.activateProfile(id); await load(); onSaved?.(); }
    catch (e) { setError(e.response?.data?.detail || 'Không thể kích hoạt cookie này'); }
  };

  const remove = async (id) => {
    if (!window.confirm('Xóa profile cookie này? Giá trị cookie sẽ bị xóa khỏi VPS.')) return;
    try { await lazadaSessionService.deleteProfile(id); await load(); }
    catch { setError('Không thể xóa cookie này'); }
  };

  const move = async (index, direction) => {
    const copy = [...data.profiles];
    const target = index + direction;
    if (target < 0 || target >= copy.length) return;
    [copy[index], copy[target]] = [copy[target], copy[index]];
    try { await lazadaSessionService.reorderProfiles(copy.map((profile) => profile.id)); await load(); }
    catch { setError('Không thể đổi thứ tự ưu tiên'); }
  };

  return <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
    <div className="bg-white dark:bg-slate-900 rounded-2xl w-full max-w-2xl p-6 shadow-xl max-h-[92vh] overflow-y-auto">
      <div className="flex justify-between items-center mb-2"><h2 className="text-lg font-bold flex gap-2 items-center"><KeyRound className="text-orange-500"/> Cookie Lazada</h2><button onClick={onClose}><X/></button></div>
      <p className="text-sm text-slate-500 mb-4">Cookie gốc chỉ lưu trong thư mục secrets của VPS, không hiển thị lại, không ghi log và không đưa vào Telegram.</p>

      <div className={`mb-4 rounded-xl p-3 text-sm ${data.paused ? 'bg-amber-50 text-amber-800 dark:bg-amber-950/40 dark:text-amber-200' : 'bg-slate-100 dark:bg-slate-800'}`}>
        {data.paused ? <span className="flex gap-2 items-center"><PauseCircle className="h-4 w-4"/> Đang tạm dừng yêu cầu cần session: chưa có profile hợp lệ.</span> : 'Profile đang active sẽ được dùng trước. Chỉ chuyển profile khi Lazada xác nhận session đã hết hạn.'}
      </div>

      <div className="space-y-2 mb-5">
        {data.profiles.map((profile, index) => <div key={profile.id} className="border border-slate-200 dark:border-slate-700 rounded-xl p-3 flex gap-3 items-center">
          <span className="w-6 text-center text-xs font-bold text-slate-400">{index + 1}</span>
          <div className="flex-1 min-w-0"><div className="flex gap-2 items-center"><span className="font-semibold text-sm truncate">{profile.label}</span>{profile.active && <span className="text-[10px] px-2 py-0.5 rounded-full bg-sky-100 text-sky-700">Đang dùng</span>}<span className={`text-[10px] px-2 py-0.5 rounded-full ${statusStyle[profile.status] || statusStyle.UNKNOWN}`}>{profile.status}</span></div><p className="text-[11px] text-slate-400 mt-1">{profile.last_error_code ? `Kết quả gần nhất: ${profile.last_error_code}` : profile.last_verified_at ? `Xác thực: ${new Date(profile.last_verified_at).toLocaleString('vi-VN')}` : 'Chưa xác thực'}</p></div>
          <div className="flex gap-1"><button disabled={index === 0} onClick={() => move(index, -1)} title="Ưu tiên cao hơn" className="p-1.5 disabled:opacity-30"><ArrowUp className="h-4 w-4"/></button><button disabled={index === data.profiles.length - 1} onClick={() => move(index, 1)} title="Ưu tiên thấp hơn" className="p-1.5 disabled:opacity-30"><ArrowDown className="h-4 w-4"/></button><button onClick={() => activate(profile.id)} title="Dùng profile này" className="p-1.5 text-sky-600"><Play className="h-4 w-4"/></button><button onClick={() => remove(profile.id)} title="Xóa" className="p-1.5 text-rose-500"><Trash2 className="h-4 w-4"/></button></div>
        </div>)}
        {!data.profiles.length && <p className="text-sm text-slate-400 text-center py-3">Chưa có profile cookie.</p>}
      </div>

      <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
        <h3 className="font-semibold text-sm mb-3 flex gap-2 items-center"><Plus className="h-4 w-4 text-orange-500"/> Thêm profile cookie</h3>
        <input value={label} onChange={e => setLabel(e.target.value)} className="w-full rounded-xl border p-3 text-sm dark:bg-slate-800 mb-2" placeholder={`Tên gợi nhớ, ví dụ Cookie ${data.profiles.length + 1}`} maxLength={100}/>
        <textarea value={value} onChange={e => setValue(e.target.value)} rows={7} className="w-full rounded-xl border p-3 text-xs font-mono dark:bg-slate-800" placeholder='Dán JSON cookie tại đây. Giá trị chỉ được gửi một lần để lưu trong secrets.'/>
        {error && <p className="text-sm text-red-500 mt-2">{error}</p>}
        <div className="flex justify-end gap-2 mt-4"><button onClick={onClose} className="px-4 py-2">Đóng</button><button disabled={saving || !value.trim()} onClick={add} className="px-4 py-2 rounded-xl bg-orange-500 text-white flex gap-2 items-center">{saving ? 'Đang lưu...' : <><CheckCircle2 className="h-4 w-4"/> Lưu profile</>}</button></div>
      </div>
    </div>
  </div>;
}
