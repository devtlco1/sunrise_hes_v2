# SUNRISE HES v2

منصة رأس خط (Head End) أولية: **FastAPI + PostgreSQL + React** مع **استقبال TCP على المنفذ 8766** لتسجيل الاتصالات وربطها بعناوين IP المخزّنة للمقاييس.

## التشغيل السريع (Docker)

```bash
docker compose up -d --build
```

- **لوحة التحكم:** `http://<عنوان-السيرفر>/`
- **وثائق API:** `http://<عنوان-السيرفر>/docs`
- **منفذ المقاييس (TCP):** `8766` (يُوجَّه لحاوية `api`)

غيّر كلمة مرور PostgreSQL في `docker-compose.yml` قبل الإنتاج، وافتح في الجدار الناري: **22** (SSH)، **80** (واجهة)، **8766** (مقاييس).

## نشر على السيرفر (أوبنتو)

**الرفع إلى GitHub لا يشغّل السيرفر تلقائياً.** على الـ VPS بعد تثبيت Docker و Docker Compose Plugin:

```bash
apt update && apt install -y git docker.io docker-compose-plugin
git clone https://github.com/devtlco1/sunrise_hes_v2.git && cd sunrise_hes_v2
docker compose up -d --build
docker compose ps
curl -s http://127.0.0.1/health
```

**جدار ناري (مثال `ufw`):**

```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 8766/tcp
ufw enable
ufw status
```

## إذا الصفحة «ما تفتح» من المتصفح

1. **افتح الرابط من Chrome أو Safari مباشرة** (`http://IP/`) وليس من معاينة مضمّنة داخل Cursor أو إطار؛ رسالة مثل `chrome-error://chromewebdata` و`Unsafe attempt to load URL` غالباً بسبب **الإطار المضمّن** وليس بسبب المشروع.
2. **تأكد أن الحاويات شغالة** (`docker compose ps`) وأن **80 و8766 مسموحين** في الـ VPS ومزوّد الاستضافة (بعضهم يحتاج فتح المنافذ من لوحة التحكم).

## التطوير المحلي

**قاعدة البيانات:** شغّل Postgres أو `docker compose up -d db`.

**Backend:**

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

الوكيل في Vite يمرّر `/api` و`/docs` إلى `localhost:8000`.

## الخطوة التالية

ربط **DLMS/COSEM (Gurux)** لقراءة الهوية والسيريال حسب `meter-communication-reference-ar.md`؛ المسار `POST /api/v1/meters/{id}/read-identity` جاهز كـ placeholder (501).
