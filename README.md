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
