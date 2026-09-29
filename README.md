# 🚀 Lazada Price Tracker & Telegram Notification Web App

Ứng dụng web toàn diện theo dõi biến động giá sản phẩm Lazada theo thời gian thực, lưu lịch sử giá, vẽ biểu đồ trực quan và tự động gửi thông báo qua **Telegram Bot** khi giá giảm hoặc đạt mức mục tiêu của người dùng, tích hợp **thuật toán chống spam thông minh**.

---

## 🌟 Tính Năng Nổi Bật

- 🔍 **Thêm sản phẩm dễ dàng bằng URL**: Chỉ cần dán link Lazada, hệ thống tự động trích xuất tên, ảnh, giá hiện tại và giá gốc.
- 📈 **Lịch sử & Biểu đồ giá trực quan**: Biểu đồ Recharts mượt mà với các mốc thời gian lọc: **24 Giờ**, **7 Ngày**, **30 Ngày**, **Tất cả**.
- 🔔 **Hệ thống cảnh báo đa điều kiện (Multi-rule Alerts)**:
  - `TARGET_PRICE`: Khi giá giảm bằng hoặc thấp hơn mức giá bạn mong muốn (VD: `<= 1.000.000đ`).
  - `PRICE_DROP`: Bất kỳ khi nào giá giảm so với lần kiểm tra trước.
  - `PERCENT_DROP`: Khi giá giảm sâu ít nhất X% (VD: `>= 10%`).
  - `NEW_LOWEST_PRICE`: Khi giá lập kỷ lục thấp nhất từ trước đến nay.
  - `PRICE_INCREASE`: Bất kỳ khi nào giá tăng.
- 🛡️ **Thuật toán chống spam Telegram thông minh**:
  - Không gửi lặp lại thông báo mỗi chu kỳ 5 phút nếu giá không thay đổi.
  - Tự động reset trạng thái kích hoạt khi giá hồi phục lên trên target để sẵn sàng gửi lại trong tương lai khi giá giảm tiếp.
- 🤖 **Tích hợp Telegram Bot API**: Tin nhắn HTML định dạng đẹp mắt, đầy đủ chi tiết % giảm, giá cũ, giá mới, timestamp và nút bấm **🔗 Mở sản phẩm trên Lazada**.
- 🔄 **Lập lịch tự động (APScheduler)**: Tự động quét giá nền theo chu kỳ tùy chỉnh (`PRICE_CHECK_INTERVAL_MINUTES=5`), kiểm soát concurrency lock tránh race condition.
- 🌓 **Giao diện hiện đại**: Hỗ trợ **Dark Mode**, tìm kiếm nhanh, sắp xếp theo giá/% giảm, lọc sản phẩm đạt target.
- 🐳 **Docker & Docker Compose**: Đóng gói sẵn sàng chạy chỉ với 1 câu lệnh.

---

## 🏗️ Kiến Trúc Hệ Thống (Clean Architecture)

```
tracking_LazaDA/
├── backend/
│   ├── app/
│   │   ├── api/                  # FastAPI routers (products, alerts, telegram, stats)
│   │   ├── core/                 # Config, Database engine, Logging
│   │   ├── jobs/                 # APScheduler background tasks & workers
│   │   ├── models/               # SQLAlchemy async models
│   │   ├── repositories/         # Database access layer (CRUD)
│   │   ├── schemas/              # Pydantic v2 validation schemas
│   │   ├── services/             # Business logic (Product, AlertEngine, Telegram)
│   │   │   └── providers/        # PriceProvider interface & Lazada scraper
│   │   └── utils/                # Currency formatters & URL validators
│   ├── tests/                    # Pytest unit tests (Alerts, Anti-spam, Regex, Formatter)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/           # UI Components (Cards, Modals, Charts, Alerts)
│   │   ├── hooks/                # Custom React hooks (Dark mode)
│   │   ├── pages/                # Dashboard view
│   │   ├── services/             # Axios API client
│   │   └── utils/                # Date & Currency formatting
│   ├── Dockerfile
│   ├── nginx.conf
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🛠️ Hướng Dẫn Cài Đặt & Khởi Chạy

### 1. Chuẩn bị Telegram Bot & Chat ID

#### Bước 1: Tạo Telegram Bot để lấy Token
1. Mở ứng dụng **Telegram**, tìm kiếm bot **`@BotFather`**.
2. Gửi lệnh `/newbot` và làm theo hướng dẫn (đặt tên hiển thị và username kết thúc bằng `bot`, ví dụ: `my_lazada_tracker_bot`).
3. `@BotFather` sẽ cấp cho bạn **HTTP API Token**, có dạng:
   `7123456789:AAFlM0XyZwABCD12345efgh-ijklmnop`

#### Bước 2: Lấy Chat ID của bạn
1. Nhắn tin bất kỳ (ví dụ: `/start` hoặc `Hello`) cho con bot bạn vừa tạo.
2. Tìm kiếm bot **`@userinfobot`** trên Telegram và bấm Start.
3. Bot sẽ trả về thông tin của bạn, trong đó dòng `Id:` chính là **Chat ID** (ví dụ: `123456789`).

---

### 2. Cấu hình biến môi trường (`.env`)

Tạo file `backend/.env` hoặc `.env` ở thư mục gốc từ `.env.example`:

```env
# Database (mặc định sử dụng SQLite không cần cài đặt thêm)
DATABASE_URL=sqlite+aiosqlite:///./lazada_tracker.db

# Telegram credentials
TELEGRAM_BOT_TOKEN=7123456789:AAFlM0XyZwABCD12345efgh-ijklmnop
TELEGRAM_CHAT_ID=123456789

# Chu kỳ tự động kiểm tra giá (phút)
PRICE_CHECK_INTERVAL_MINUTES=5

# Debug mode
DEBUG=True
```

---

### 3. Chạy ứng dụng bằng Docker Compose (Khuyên dùng)

Chỉ cần một câu lệnh để khởi động toàn bộ Frontend, Backend, Database và Scheduler:

```bash
docker compose up -d --build
```

- **Frontend Web UI**: [http://localhost:5173](http://localhost:5173)
- **Backend API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

### 4. Chạy trực tiếp trên máy (Local Development)

#### Backend (FastAPI):
```bash
# Di chuyển vào thư mục backend
cd backend

# Cài đặt thư viện
pip install -r requirements.txt

# Khởi chạy server FastAPI
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Frontend (React + Vite):
```bash
# Mở terminal mới, di chuyển vào thư mục frontend
cd frontend

# Cài đặt packages
npm install

# Khởi chạy server phát triển
npm run dev
```

---

## 🧪 Chạy Kiểm Thử (Unit Tests)

Backend đi kèm bộ test hoàn chỉnh kiểm thử logic so sánh giá, 5 loại cảnh báo, cơ chế chống spam, định dạng tiền tệ và trích xuất HTML:

```bash
python -m pytest backend/tests
```

Kết quả: **16/16 unit tests Passed** ✅

---

## 📱 Ví Dụ Thông Báo Telegram Khi Đạt Target

Khi giá sản phẩm giảm bằng hoặc thấp hơn `target_price`, Telegram Bot sẽ gửi tin nhắn:

```
🔥 GIÁ SẢN PHẨM VỪA GIẢM!

📦 Chuột Gaming Logitech G Pro X Superlight Wireless

💰 Giá cũ: 1.590.000đ
🔥 Giá mới: 1.290.000đ
📉 Giảm: 300.000đ (-18.87%)
🎯 Giá mục tiêu: 1.300.000đ
✅ ĐÃ ĐẠT / THẤP HƠN GIÁ MỤC TIÊU!
✨ 🎯 Đạt giá mục tiêu: 1.290.000đ <= 1.300.000đ
✨ 📉 Giá giảm: -300.000đ (-18.9%)

⏰ 23/09/2026 19:30
[ Nút bấm: 🔗 MỞ SẢN PHẨM TRÊN LAZADA ]
```

---

## ⚠️ Giới Hạn Khi Lấy Giá Lazada & Giải Pháp Mở Rộng Provider

### 1. Thách thức với hệ thống chống bot của sàn TMĐT
Lazada và các sàn thương mại điện tử lớn thường xuyên cập nhật cơ chế bảo vệ (Cloudflare, Akamai bot detection, JavaScript challenge, captcha). Khi truy cập với tần suất cao từ cùng một IP, yêu cầu có thể bị chặn.

### 2. Thiết kế linh hoạt với `BasePriceProvider`
Dự án được thiết kế theo nguyên tắc **Open-Closed** trong Clean Architecture với abstract class `BasePriceProvider` tại `backend/app/services/providers/base.py`.

Nếu phương thức crawl HTML hiện tại bị hạn chế, bạn có thể dễ dàng thay đổi hoặc thêm phương thức mới:

1. **Playwright / Puppeteer Adapter (Headless Browser)**:
   Mô phỏng trình duyệt thật để vượt qua JavaScript rendering và cookie challenge.
   ```python
   class PlaywrightLazadaProvider(BasePriceProvider):
       async def get_product_info(self, url: str) -> ProductScrapedData:
           # Khởi động trình duyệt Chromium và lấy DOM sau khi render
           pass
   ```
2. **Lazada Open Platform API (Official API)**:
   Nếu có tài khoản đối tác Lazada Affiliate / Developer, bạn có thể đăng ký API key và triển khai `LazadaOfficialApiProvider` mà không cần sửa bất kỳ dòng code database hay alert nào.
3. **Mở rộng sang các sàn khác**:
   Dễ dàng bổ sung `ShopeePriceProvider`, `TikTokShopPriceProvider` thông qua `backend/app/services/providers/factory.py`.
