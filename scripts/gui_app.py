import os
import sys
import json
import asyncio
import threading
import subprocess
import webbrowser
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk

# Configure paths
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(current_dir)
backend_dir = os.path.join(root_dir, "backend")
sys.path.insert(0, backend_dir)

from app.services.providers.lazada import LazadaPriceProvider
from app.utils.currency import format_currency, parse_currency

PRODUCTS_FILE = os.path.join(root_dir, "products.json")

# Configure CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class VariationSelectDialog(ctk.CTkToplevel):
    """
    Modal dialog allowing user to pick the exact variation/SKU when a product has multiple options.
    """
    def __init__(self, parent, product_name: str, variations: list, on_select_callback):
        super().__init__(parent)
        self.title("🏷️ Chọn Phân Loại Sản Phẩm")
        self.geometry("620x520")
        self.minsize(500, 400)
        self.transient(parent)
        self.grab_set()

        self.variations = variations
        self.on_select_callback = on_select_callback
        self.selected_var_idx = tk.IntVar(value=0)

        # Header
        hdr = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e293b")
        hdr.pack(fill="x", padx=15, pady=12)

        lbl_title = ctk.CTkLabel(
            hdr,
            text="🏷️ CHỌN PHÂN LOẠI / MÀU SẮC",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8"
        )
        lbl_title.pack(anchor="w", padx=12, pady=(10, 2))

        lbl_sub = ctk.CTkLabel(
            hdr,
            text=f"Sản phẩm: {product_name[:70]}...\nTìm thấy {len(variations)} phân loại. Vui lòng chọn bản bạn muốn theo dõi:",
            font=ctk.CTkFont(size=12),
            text_color="#94a3b8",
            justify="left"
        )
        lbl_sub.pack(anchor="w", padx=12, pady=(0, 10))

        # Scrollable variation list
        scroll_frame = ctk.CTkScrollableFrame(self, corner_radius=8)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 12))

        for idx, var in enumerate(variations):
            var_card = ctk.CTkFrame(scroll_frame, corner_radius=6, fg_color="#0f172a" if idx % 2 == 0 else "#1e293b")
            var_card.pack(fill="x", padx=4, pady=4)

            rb = ctk.CTkRadioButton(
                var_card,
                text=var.get("name", f"Phân loại #{var.get('sku_id')}"),
                variable=self.selected_var_idx,
                value=idx,
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color="#f8fafc"
            )
            rb.pack(side="left", padx=12, pady=10, fill="x", expand=True)

            price_val = var.get("price", 0)
            orig_val = var.get("original_price")
            price_str = format_currency(price_val)
            if orig_val and orig_val > price_val:
                price_str += f" (Gốc: {format_currency(orig_val)})"

            lbl_p = ctk.CTkLabel(
                var_card,
                text=price_str,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#4ade80"
            )
            lbl_p.pack(side="right", padx=12, pady=10)

        # Bottom buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text="✅ Xác Nhận Chọn Phân Loại Này",
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=40,
            command=self._on_confirm
        )
        confirm_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="Hủy",
            fg_color="#475569",
            hover_color="#334155",
            width=100,
            height=40,
            command=self.destroy
        )
        cancel_btn.pack(side="right")

    def _on_confirm(self):
        chosen_idx = self.selected_var_idx.get()
        if 0 <= chosen_idx < len(self.variations):
            chosen = self.variations[chosen_idx]
            self.destroy()
            self.on_select_callback(chosen)


class LazadaTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🛒 Lazada Price Tracker - Quản Lý Săn Sale 24/7")
        self.geometry("960x760")
        self.minsize(850, 650)

        self.provider = LazadaPriceProvider()
        self.products = []
        self.expanded_cards = set()  # Set of product IDs currently expanded
        self.load_products()

        self._create_layout()
        self.refresh_product_list()

    def load_products(self):
        if os.path.exists(PRODUCTS_FILE):
            try:
                with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                    self.products = json.load(f)
            except Exception:
                self.products = []
        else:
            self.products = []

    def save_products(self):
        with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.products, f, ensure_ascii=False, indent=2)

    def _create_layout(self):
        # Header Frame
        header = ctk.CTkFrame(self, corner_radius=10, fg_color="#1e293b")
        header.pack(fill="x", padx=15, pady=10)

        title = ctk.CTkLabel(
            header,
            text="🛒 LAZADA PRICE TRACKER",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#38bdf8"
        )
        title.pack(side="left", padx=15, pady=12)

        self.status_label = ctk.CTkLabel(
            header,
            text="🟢 Sẵn sàng",
            font=ctk.CTkFont(size=13),
            text_color="#4ade80"
        )
        self.status_label.pack(side="right", padx=15, pady=12)

        # Add Product Section
        add_frame = ctk.CTkFrame(self, corner_radius=10)
        add_frame.pack(fill="x", padx=15, pady=(0, 10))

        add_title = ctk.CTkLabel(
            add_frame,
            text="➕ Thêm Sản Phẩm Lazada Cần Theo Dõi",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        add_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(10, 6))

        # Row 1: URL input
        self.url_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="Dán link sản phẩm Lazada (https://www.lazada.vn/products/... hoặc https://s.lazada.vn/s...)...",
            height=38
        )
        self.url_entry.grid(row=1, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 8))

        # Row 2: Target Price + Note + Add Button
        row2_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        row2_frame.grid(row=2, column=0, columnspan=3, sticky="ew", padx=15, pady=(0, 12))

        self.target_entry = ctk.CTkEntry(
            row2_frame,
            placeholder_text="🎯 Giá mục tiêu (VD: 500000)...",
            width=180,
            height=38
        )
        self.target_entry.pack(side="left", padx=(0, 10))

        self.note_entry = ctk.CTkEntry(
            row2_frame,
            placeholder_text="📝 Ghi chú (VD: Bản Switch Reaper xanh, Quà sinh nhật...)...",
            height=38
        )
        self.note_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.add_btn = ctk.CTkButton(
            row2_frame,
            text="🔍 Thêm Sản Phẩm",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=38,
            width=150,
            command=self.on_add_product
        )
        self.add_btn.pack(side="right")

        add_frame.grid_columnconfigure(0, weight=1)

        # Scrollable Product List Frame
        list_container = ctk.CTkFrame(self, corner_radius=10)
        list_container.pack(fill="both", expand=True, padx=15, pady=(0, 10))

        list_header = ctk.CTkFrame(list_container, fg_color="transparent")
        list_header.pack(fill="x", padx=15, pady=(10, 5))

        self.count_label = ctk.CTkLabel(
            list_header,
            text="📋 Danh Sách Đang Theo Dõi (0 sản phẩm)",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.count_label.pack(side="left")

        self.scroll_list = ctk.CTkScrollableFrame(list_container, corner_radius=8)
        self.scroll_list.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Bottom Action Bar
        bottom_bar = ctk.CTkFrame(self, corner_radius=10, fg_color="transparent")
        bottom_bar.pack(fill="x", padx=15, pady=(0, 15))

        self.sync_btn = ctk.CTkButton(
            bottom_bar,
            text="🚀 ĐỒNG BỘ LÊN GITHUB 24/7",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#16a34a",
            hover_color="#15803d",
            height=42,
            command=self.on_sync_github
        )
        self.sync_btn.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.check_all_btn = ctk.CTkButton(
            bottom_bar,
            text="🔄 Quét Giá Tất Cả",
            font=ctk.CTkFont(size=13),
            fg_color="#475569",
            hover_color="#334155",
            height=42,
            width=160,
            command=self.on_check_all_prices
        )
        self.check_all_btn.pack(side="right")

    def refresh_product_list(self):
        for widget in self.scroll_list.winfo_children():
            widget.destroy()

        self.count_label.configure(text=f"📋 Danh Sách Đang Theo Dõi ({len(self.products)} sản phẩm)")

        if not self.products:
            empty_lbl = ctk.CTkLabel(
                self.scroll_list,
                text="Chưa có sản phẩm nào. Hãy dán link Lazada ở trên để thêm!",
                font=ctk.CTkFont(size=13),
                text_color="#94a3b8"
            )
            empty_lbl.pack(pady=40)
            return

        for idx, item in enumerate(self.products):
            p_id = item.get("id", idx + 1)
            is_expanded = (p_id in self.expanded_cards)

            card = ctk.CTkFrame(self.scroll_list, corner_radius=8, fg_color="#1e293b")
            card.pack(fill="x", padx=5, pady=5)

            # Top Main Row
            main_row = ctk.CTkFrame(card, fg_color="transparent")
            main_row.pack(fill="x", padx=12, pady=(10, 5))

            # Left Info
            info_frame = ctk.CTkFrame(main_row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True)

            # Title + SKU
            title_text = f"{idx + 1}. {item.get('name', 'Sản phẩm Lazada')[:60]}"
            name_lbl = ctk.CTkLabel(
                info_frame,
                text=title_text,
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
                text_color="#f8fafc"
            )
            name_lbl.pack(fill="x")

            # SKU badge if any
            sku_name = item.get("sku_name")
            if sku_name:
                sku_lbl = ctk.CTkLabel(
                    info_frame,
                    text=f"🏷️ Phân loại: {sku_name}",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    anchor="w",
                    text_color="#f59e0b"
                )
                sku_lbl.pack(fill="x", pady=(2, 0))

            # Prices row
            cur_price = item.get("last_price", 0)
            tgt_price = item.get("target_price", 0)
            prices_text = f"💵 Giá hiện tại: {format_currency(cur_price)}   |   🎯 Giá mục tiêu: {format_currency(tgt_price)}"
            price_lbl = ctk.CTkLabel(
                info_frame,
                text=prices_text,
                font=ctk.CTkFont(size=12),
                anchor="w",
                text_color="#38bdf8"
            )
            price_lbl.pack(fill="x", pady=(2, 0))

            # Note if any
            note_val = item.get("note")
            if note_val:
                note_lbl = ctk.CTkLabel(
                    info_frame,
                    text=f"📝 Ghi chú: {note_val}",
                    font=ctk.CTkFont(size=12, slant="italic"),
                    anchor="w",
                    text_color="#cbd5e1"
                )
                note_lbl.pack(fill="x", pady=(2, 0))

            # Right action buttons
            btn_frame = ctk.CTkFrame(main_row, fg_color="transparent")
            btn_frame.pack(side="right", padx=(10, 0))

            del_btn = ctk.CTkButton(
                btn_frame,
                text="🗑️ Xóa",
                fg_color="#dc2626",
                hover_color="#b91c1c",
                width=65,
                height=30,
                command=lambda p=item: self.on_delete_product(p)
            )
            del_btn.pack(side="right", padx=(5, 0))

            check_btn = ctk.CTkButton(
                btn_frame,
                text="🔄 Quét",
                fg_color="#334155",
                hover_color="#1e293b",
                width=65,
                height=30,
                command=lambda p=item: self.on_check_single_product(p)
            )
            check_btn.pack(side="right")

            # Expand / Collapse Link Toggle Button
            arrow_icon = "▲ Thu gọn link" if is_expanded else "▼ Link chi tiết"
            toggle_btn = ctk.CTkButton(
                card,
                text=arrow_icon,
                font=ctk.CTkFont(size=11),
                fg_color="#0f172a",
                hover_color="#334155",
                text_color="#94a3b8",
                height=24,
                command=lambda pid=p_id: self.toggle_card_expansion(pid)
            )
            toggle_btn.pack(anchor="w", padx=12, pady=(2, 8))

            # Expandable Sub-frame
            if is_expanded:
                link_subframe = ctk.CTkFrame(card, corner_radius=6, fg_color="#0f172a")
                link_subframe.pack(fill="x", padx=12, pady=(0, 10))

                url_val = item.get("url", "")
                
                # URL display box
                url_display = ctk.CTkEntry(
                    link_subframe,
                    font=ctk.CTkFont(size=11),
                    height=28,
                    fg_color="#1e293b"
                )
                url_display.insert(0, url_val)
                url_display.configure(state="readonly")
                url_display.pack(side="left", fill="x", expand=True, padx=(8, 6), pady=6)

                # Copy button
                copy_btn = ctk.CTkButton(
                    link_subframe,
                    text="📋 Copy Link",
                    font=ctk.CTkFont(size=11),
                    width=85,
                    height=28,
                    fg_color="#0284c7",
                    hover_color="#0369a1",
                    command=lambda u=url_val: self.copy_to_clipboard(u)
                )
                copy_btn.pack(side="left", padx=(0, 6), pady=6)

                # Open Web button
                web_btn = ctk.CTkButton(
                    link_subframe,
                    text="🌐 Mở Web",
                    font=ctk.CTkFont(size=11),
                    width=75,
                    height=28,
                    fg_color="#059669",
                    hover_color="#047857",
                    command=lambda u=url_val: webbrowser.open(u)
                )
                web_btn.pack(side="left", padx=(0, 8), pady=6)

    def toggle_card_expansion(self, product_id):
        if product_id in self.expanded_cards:
            self.expanded_cards.remove(product_id)
        else:
            self.expanded_cards.add(product_id)
        self.refresh_product_list()

    def copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        messagebox.showinfo("Đã sao chép", "Đã sao chép link sản phẩm vào bộ nhớ tạm!")

    def on_add_product(self):
        url = self.url_entry.get().strip()
        target_str = self.target_entry.get().strip()
        note = self.note_entry.get().strip()

        if not url:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng dán đường link Lazada!")
            return

        target_price = parse_currency(target_str) if target_str else 0

        self.set_loading(True, "🔍 Đang lấy thông tin sản phẩm và phân loại từ Lazada...")

        def fetch_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(self.provider.get_product_info(url))
                if res.success and res.price > 0:
                    # Check if there are multiple variations and user hasn't locked into a specific one
                    if res.variations and len(res.variations) > 1 and ("-s" not in url):
                        # Prompt variation selector on GUI thread
                        self.after(0, lambda: self._show_variation_selector(res, target_price, note, url))
                    else:
                        self.after(0, lambda: self._save_new_product(
                            name=res.name,
                            url=res.url or url,
                            price=res.price,
                            target_price=target_price,
                            sku_id=res.sku_id,
                            sku_name=res.sku_name,
                            note=note
                        ))
                else:
                    err_msg = res.error_message or "Không thể đọc giá từ trang này."
                    self.after(0, lambda: self._add_failed(err_msg))
            except Exception as e:
                self.after(0, lambda: self._add_failed(str(e)))
            finally:
                loop.close()

        threading.Thread(target=fetch_task, daemon=True).start()

    def _show_variation_selector(self, res, target_price: int, note: str, original_url: str):
        self.set_loading(False, "🟢 Vui lòng chọn phân loại sản phẩm")

        def on_selected(variation):
            var_price = variation.get("price", res.price)
            var_url = variation.get("url") or original_url
            var_sku = variation.get("sku_id")
            var_name = variation.get("name")
            self._save_new_product(
                name=res.name,
                url=var_url,
                price=var_price,
                target_price=target_price,
                sku_id=var_sku,
                sku_name=var_name,
                note=note
            )

        VariationSelectDialog(self, res.name, res.variations, on_selected)

    def _save_new_product(self, name: str, url: str, price: int, target_price: int, sku_id: str = None, sku_name: str = None, note: str = None):
        final_target = target_price if target_price > 0 else int(price * 0.9)
        new_id = (max([p.get("id", 0) for p in self.products], default=0)) + 1

        new_item = {
            "id": new_id,
            "name": name,
            "sku_id": sku_id,
            "sku_name": sku_name,
            "note": note if note else None,
            "url": url,
            "target_price": final_target,
            "last_price": price,
            "last_checked": None,
            "history": [{"price": price, "timestamp": ""}]
        }
        self.products.append(new_item)
        self.save_products()

        self._add_success(name, price, final_target, sku_name)

    def _add_success(self, name: str, price: int, target: int, sku_name: str = None):
        self.set_loading(False, "🟢 Đã thêm sản phẩm thành công!")
        self.url_entry.delete(0, "end")
        self.target_entry.delete(0, "end")
        self.note_entry.delete(0, "end")
        self.refresh_product_list()

        msg = f"Đã thêm sản phẩm:\n\n📦 {name[:50]}"
        if sku_name:
            msg += f"\n🏷️ Phân loại: {sku_name}"
        msg += f"\n💵 Giá hiện tại: {format_currency(price)}\n🎯 Mục tiêu: {format_currency(target)}"

        messagebox.showinfo("Thành công", msg)

    def _add_failed(self, msg: str):
        self.set_loading(False, "🔴 Thất bại")
        messagebox.showerror("Lỗi", f"Không thể lấy thông tin sản phẩm:\n{msg}")

    def on_delete_product(self, product):
        p_name = product.get("name", "")[:40]
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa sản phẩm:\n'{p_name}' ?"):
            p_id = product.get("id")
            if p_id:
                self.products = [p for p in self.products if p.get("id") != p_id]
            else:
                self.products = [p for p in self.products if p.get("url") != product.get("url")]
            self.save_products()
            self.refresh_product_list()

    def on_check_single_product(self, product):
        url = product.get("url")
        self.set_loading(True, f"🔄 Đang quét giá: {product.get('name', '')[:25]}...")

        def check_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(self.provider.get_product_info(url))
                if res.success and res.price > 0:
                    product["last_price"] = res.price
                    product["name"] = res.name or product.get("name")
                    if res.sku_name and not product.get("sku_name"):
                        product["sku_name"] = res.sku_name
                    self.save_products()
                    self.after(0, lambda: messagebox.showinfo("Cập nhật giá", f"📦 {res.name[:45]}\n💵 Giá hiện tại: {format_currency(res.price)}"))
                else:
                    self.after(0, lambda: messagebox.showerror("Lỗi", f"Không lấy được giá: {res.error_message}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Lỗi", str(e)))
            finally:
                self.after(0, lambda: self.set_loading(False, "🟢 Hoàn thành"))
                self.after(0, self.refresh_product_list)
                loop.close()

        threading.Thread(target=check_task, daemon=True).start()

    def on_check_all_prices(self):
        if not self.products:
            messagebox.showinfo("Thông báo", "Chưa có sản phẩm nào trong danh sách!")
            return

        self.set_loading(True, f"🔄 Đang quét giá {len(self.products)} sản phẩm...")

        def check_all_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            for p in self.products:
                url = p.get("url")
                if not url:
                    continue
                try:
                    res = loop.run_until_complete(self.provider.get_product_info(url))
                    if res.success and res.price > 0:
                        p["last_price"] = res.price
                        p["name"] = res.name or p.get("name")
                        if res.sku_name and not p.get("sku_name"):
                            p["sku_name"] = res.sku_name
                except Exception:
                    pass
                loop.run_until_complete(asyncio.sleep(2.0))
            self.save_products()
            loop.close()
            self.after(0, lambda: self.set_loading(False, "🟢 Đã quét xong tất cả!"))
            self.after(0, self.refresh_product_list)
            self.after(0, lambda: messagebox.showinfo("Hoàn tất", f"Đã quét và cập nhật giá mới cho {len(self.products)} sản phẩm!"))

        threading.Thread(target=check_all_task, daemon=True).start()

    def on_sync_github(self):
        if not self.products:
            messagebox.showinfo("Thông báo", "Chưa có sản phẩm nào để đồng bộ!")
            return

        self.set_loading(True, "🚀 Đang đẩy dữ liệu lên GitHub Actions 24/7...")

        def git_sync_task():
            try:
                subprocess.run(["git", "add", "products.json"], check=True, cwd=root_dir)
                subprocess.run(["git", "commit", "-m", f"Sync {len(self.products)} products from Desktop App"], cwd=root_dir)
                subprocess.run(["git", "push", "origin", "main"], check=True, cwd=root_dir)
                self.after(0, lambda: messagebox.showinfo("Đồng bộ thành công! 🎉", "Toàn bộ danh sách sản phẩm đã được đẩy lên GitHub Actions.\n\nGitHub sẽ tự động quét các sản phẩm này 24/7 và gửi báo giá về Telegram cho bạn!"))
            except Exception as e:
                self.after(0, lambda: messagebox.showwarning("Lưu ý", f"Dữ liệu đã lưu trên máy nhưng chưa đẩy được git:\n{e}"))
            finally:
                self.after(0, lambda: self.set_loading(False, "🟢 Đã đồng bộ"))

        threading.Thread(target=git_sync_task, daemon=True).start()

    def set_loading(self, is_loading: bool, status_text: str):
        self.status_label.configure(text=status_text)
        state = "disabled" if is_loading else "normal"
        self.add_btn.configure(state=state)
        self.sync_btn.configure(state=state)
        self.check_all_btn.configure(state=state)


if __name__ == "__main__":
    app = LazadaTrackerApp()
    app.mainloop()
