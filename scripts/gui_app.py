import os
import sys
import json
import asyncio
import threading
import subprocess
import tkinter as tk
from tkinter import messagebox, simpledialog
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


class LazadaTrackerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("🛒 Lazada Price Tracker - Quản Lý Săn Sale 24/7")
        self.geometry("900x700")
        self.minsize(800, 600)

        self.provider = LazadaPriceProvider()
        self.products = []
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
        add_title.grid(row=0, column=0, columnspan=3, sticky="w", padx=15, pady=(10, 5))

        self.url_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="Dán đường link sản phẩm Lazada vào đây (https://www.lazada.vn/products/...)...",
            height=38
        )
        self.url_entry.grid(row=1, column=0, sticky="ew", padx=(15, 10), pady=(0, 12))

        self.target_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text="Giá mục tiêu (VD: 300000)...",
            width=180,
            height=38
        )
        self.target_entry.grid(row=1, column=1, padx=(0, 10), pady=(0, 12))

        self.add_btn = ctk.CTkButton(
            add_frame,
            text="🔍 Thêm Sản Phẩm",
            font=ctk.CTkFont(weight="bold"),
            fg_color="#0284c7",
            hover_color="#0369a1",
            height=38,
            width=140,
            command=self.on_add_product
        )
        self.add_btn.grid(row=1, column=2, padx=(0, 15), pady=(0, 12))

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
            card = ctk.CTkFrame(self.scroll_list, corner_radius=8, fg_color="#1e293b")
            card.pack(fill="x", padx=5, pady=5)

            # Left Info
            info_frame = ctk.CTkFrame(card, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True, padx=12, pady=10)

            name_lbl = ctk.CTkLabel(
                info_frame,
                text=f"{idx + 1}. {item.get('name', 'Sản phẩm Lazada')[:60]}",
                font=ctk.CTkFont(size=14, weight="bold"),
                anchor="w",
                text_color="#f8fafc"
            )
            name_lbl.pack(fill="x")

            prices_text = f"💵 Giá hiện tại: {format_currency(item.get('last_price', 0))}  |  🎯 Giá mục tiêu: {format_currency(item.get('target_price', 0))}"
            price_lbl = ctk.CTkLabel(
                info_frame,
                text=prices_text,
                font=ctk.CTkFont(size=12),
                anchor="w",
                text_color="#38bdf8"
            )
            price_lbl.pack(fill="x", pady=(2, 0))

            # Right Buttons
            btn_frame = ctk.CTkFrame(card, fg_color="transparent")
            btn_frame.pack(side="right", padx=12, pady=10)

            del_btn = ctk.CTkButton(
                btn_frame,
                text="🗑️ Xóa",
                fg_color="#dc2626",
                hover_color="#b91c1c",
                width=70,
                height=30,
                command=lambda p=item: self.on_delete_product(p)
            )
            del_btn.pack(side="right", padx=(5, 0))

            check_btn = ctk.CTkButton(
                btn_frame,
                text="🔄 Quét",
                fg_color="#334155",
                hover_color="#1e293b",
                width=70,
                height=30,
                command=lambda p=item: self.on_check_single_product(p)
            )
            check_btn.pack(side="right")

    def on_add_product(self):
        url = self.url_entry.get().strip()
        target_str = self.target_entry.get().strip()

        if not url:
            messagebox.showwarning("Thiếu thông tin", "Vui lòng dán đường link Lazada!")
            return

        target_price = parse_currency(target_str) if target_str else 0

        self.set_loading(True, "🔍 Đang lấy thông tin sản phẩm từ Lazada...")

        def fetch_task():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                res = loop.run_until_complete(self.provider.get_product_info(url))
                if res.success and res.price > 0:
                    current_price = res.price
                    name = res.name or "Sản phẩm Lazada"
                    final_target = target_price if target_price > 0 else int(current_price * 0.9)

                    # Add to list
                    new_item = {
                        "id": len(self.products) + 1,
                        "name": name,
                        "url": res.url or url,
                        "target_price": final_target,
                        "last_price": current_price,
                        "last_checked": None,
                        "history": [{"price": current_price, "timestamp": ""}]
                    }
                    self.products.append(new_item)
                    self.save_products()

                    self.after(0, lambda: self._add_success(name, current_price, final_target))
                else:
                    err_msg = res.error_message or "Không thể đọc giá từ trang này."
                    self.after(0, lambda: self._add_failed(err_msg))
            except Exception as e:
                self.after(0, lambda: self._add_failed(str(e)))
            finally:
                loop.close()

        threading.Thread(target=fetch_task, daemon=True).start()

    def _add_success(self, name, price, target):
        self.set_loading(False, "🟢 Đã thêm sản phẩm thành công!")
        self.url_entry.delete(0, "end")
        self.target_entry.delete(0, "end")
        self.refresh_product_list()
        messagebox.showinfo("Thành công", f"Đã thêm sản phẩm:\n\n📦 {name[:50]}\n💵 Giá hiện tại: {format_currency(price)}\n🎯 Mục tiêu: {format_currency(target)}")

    def _add_failed(self, msg):
        self.set_loading(False, "🔴 Thất bại")
        messagebox.showerror("Lỗi", f"Không thể lấy thông tin sản phẩm:\n{msg}")

    def on_delete_product(self, product):
        if messagebox.askyesno("Xác nhận", f"Bạn có chắc muốn xóa sản phẩm:\n'{product.get('name', '')[:40]}' ?"):
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
                    self.save_products()
                    self.after(0, lambda: self._check_success(res.name, res.price))
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
                except Exception:
                    pass
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
