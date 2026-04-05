# مرجع تخاطب المقاييس — مشروع sunrise-hes-platform

> **الغرض:** مرجع تقني مركز على **التخاطب مع المقاييس** (DLMS/COSEM، TCP، OBIS، الأوامر، القراءات، الأسرار) مستخرج من **الكود الحالي** في هذا المستودع.  
> **ليس** دليلاً لكل المنصة (مستخدمين، واجهة، GIS، إلخ).  
> **للاستخدام مع Cursor:** انسخ هذا الملف إلى محادثة جديدة واطلب تنفيذاً يعتمد عليه حصراً لتقليل الخلط.

---

## 1. ملخص المعمارية

| الطبقة | الدور |
|--------|--------|
| **قاعدة البيانات** | `meters`, `communication_endpoints`, `meter_endpoint_assignments`, `protocol_association_profiles`, `commands`, `meter_readings`, … |
| **واجهة API** | FastAPI تحت البادئة ` /api/v1 ` + مسارات داخلية للاستيراد |
| **زمن التشغيل (Runtime)** | محول DLMS عبر **Gurux** على **TCP** (`gurux_tcp_ingress.py`, `dlms_cosem.py`) عند تفعيل مسارات التشغيل |
| **الويب** | عرض القراءات والأوامر؛ **لا** ينفّذ بروتوكول المقياس مباشرة — كل شيء يمر عبر الـ API والـ runtime |

**عائلة البروتوكول المعرّفة في المنصة:** `dlms_cosem` فقط (`ProtocolFamily.DLMS_COSEM`).

---

## 2. كيانات الاتصال (Connectivity)

### 2.1 نقطة الاتصال `CommunicationEndpoint`

- تمثل **وسيلة الوصول** للمقياس: TCP، serial، modem، gateway، virtual.
- حقول مهمة للـ TCP: `host`, `port`, `ip_address` (إن وُجدت)، وأنواع النقل `transport_type` / `endpoint_type`.

### 2.2 ربط المقياس بالنقطة `MeterEndpointAssignment`

- يربط `meter_id` ↔ `endpoint_id`.
- حالة التعيين: `active` / `inactive` / `suspended`.
- يمكن تمييز **أساسي** بـ `is_primary`.

### 2.3 ملف ارتباط البروتوكول `ProtocolAssociationProfile`

هذا الجدول يحمل **إعدادات جلسة DLMS/COSEM** التي يستهلكها الـ runtime:

| حقل | معنى تشغيلي |
|-----|---------------|
| `protocol_family` | حالياً `dlms_cosem` |
| `iec62056_21_enabled` | تفعيل مسار IEC 62056-21 قبل DLMS (غالباً عبر TCP) |
| `client_address`, `server_address` | عناوين الارتباط في COSEM |
| `authentication_mode` | `none`, `low`, `high`, `high_gmac` |
| `password_secret_ref` | **مرجع سر** (ليس كلمة المرور نصاً في DB عادة) — يُحل لاحقاً من البيئة |
| `security_suite`, `system_title`, `auth_key_ref`, … | أعمدة جاهزة لتوسعة أمنية أعلى |
| `invocation_counter_obis`, `meter_time_obis` | OBIS اختيارية لسياقات متقدمة |
| `profile_settings` | JSONB لإعدادات إضافية |

**القاعدة:** أي أمر أو قراءة حيّة تحتاج **تعيين نقطة فعّال** + **ملف بروتوكول** مرتبط بمسار التنفيذ.

---

## 3. إعدادات البروتوكول على TCP (`protocol_settings`)

تُمرَّر كجزء من سياق التنفيذ وتُبنى منها `LiveTcpDlmsSessionConfig` في  
`apps/api/app/runtime/adapters/dlms_cosem.py` → `_build_live_tcp_dlms_session_config`.

### 3.1 اختيار بداية الجلسة

| المفتاح | القيم | النتيجة |
|---------|--------|---------|
| `tcp_start_protocol` | `iec`, `iec62056_21`, `iec62056-21` | يبدأ بـ IEC ثم ينتقل لـ DLMS |
| | `dlms`, `hdlc`, `snrm` | جلسة DLMS مباشرة |
| (بدون مفتاح) | — | إن `iec62056_21_enabled` على الملف = true → IEC، وإلا DLMS |

### 3.2 مفاتيح شائعة (مع قيم افتراضية من الكود)

- `use_broadcast_snrm_first` (افتراضي `true`) — إرسال SNRM بثّي قبل الارتباط.
- `broadcast_snrm_hex` — افتراضي `7EA00AFEFEFEFF0393C9837E`.
- `iec_ack_hex_candidates` — قائمة hex لردود IEC المعترف بها؛ افتراضي `["063235320D0A", "06B235B28D0A"]`.
- `after_iec_sleep_ms` — افتراضي `1200`.
- `dlms_read_timeout_seconds` — افتراضي `2.5`.
- `iec_serial_timeout_seconds` — افتراضي `5.0`.
- `iec_wake_zero_bytes`, `iec_wake_post_delay_ms`, `iec_ident_retries`, `iec_ident_retry_delay_ms`.
- `ua_swap_addresses` — افتراضي `false`.
- `send_hdlc_disc_before_close` — افتراضي `true`.
- `disc_drain_timeout_seconds` — افتراضي `0.4`.

**تأخير إضافي:** `before_first_iec_send_delay_ms` يأتي من إعداد التطبيق `runtime_tcp_meter_ingress_before_first_iec_send_delay_ms` (ليس من JSON الملف بالضرورة).

---

## 4. كلمات المرور والأسرار

### 4.1 `password_secret_ref` على `ProtocolAssociationProfile`

- يخزّن **مرجعاً** (مثل اسم متغير بيئة أو مفتاح تكوين)، وليس بالضرورة القيمة الصريحة.

### 4.2 الدالة `resolve_runtime_secret_ref`

**الملف:** `apps/api/app/runtime/services/runtime_secret_refs.py`

1. إذا كان `secret_ref` يطابق **اسم متغير بيئة** وكان معرّفاً → تُرجع قيمته.
2. وإلا تُجرّب اسمًا مشتقاً: `RUNTIME_SECRET_` + تحويل المرجع إلى أحرف كبيرة واستبدال غير الأبجدية الرقمية بـ `_`.

**مثال من الاختبارات:** `password_secret_ref="secret://meters/runtime-low"` مع توفير قيمة عبر env مناسب.

**مهم:** وضع **LOW authentication** مع DLMS الحي يتطلب كلمة مرور قابلة للحل؛ وإلا يرمي التشغيل خطأ صريحاً.

---

## 5. رموز OBIS والاستخدام في المشروع

> OBIS بتنسيق DLMS: `A.B.C.D.E.F` (غالباً 6 مقاطع).

### 5.1 اكتشاف الهوية (Identity discovery)

**الثابت في الكود:** `IDENTITY_DISCOVERY_OBIS_CODES` في `gurux_tcp_ingress.py`:

- `0.0.96.1.0.255`
- `0.0.96.1.1.255`
- `0.0.96.1.2.255`

### 5.2 قراءة فوترة / لقطة سجلات (On-demand / billing snapshot)

**الدالة:** `_resolve_on_demand_read_obis_codes` في `dlms_cosem.py`:

- إذا وُجد في الـ payload قائمة `obis` غير فارغة → تُستخدم كما هي.
- **الافتراضي** إن لم تُحدد:  
  - `1.0.1.8.0.255` (طاقة فعالة مستوردة شائعة)  
  - `1.0.2.8.0.255` (طاقة فعالة مصدّرة شائعة)

**اختبارات أخرى في المستودع** تستخدم مثلاً `1.0.1.8.0.255` كسجل فوترة.

### 5.3 التحكم بالفصل والوصل (Relay / disconnect control)

**الربط في `dlms_cosem.py` → `_map_relay_control_operation_to_gurux_definition`:**

| العملية المنصّة | COSEM class | OBIS | method (منطقي) |
|-----------------|------------|------|----------------|
| `disconnect` | `disconnect_control`, class_id **70** | **`0.0.96.3.10.255`** | `remote_disconnect` (method_index 1) |
| `reconnect` | نفس الكائن | **`0.0.96.3.10.255`** | `remote_reconnect` (method_index 2) |

**تنبيه تشغيلي:** يتطلب `enable_runtime_relay_control_gurux_mapper = true` في الإعدادات (افتراضياً مفعّل في `config.py`).

### 5.4 التقاط بروفايل حمل (Profile capture)

- في الاختبارات يظهر مثال لـ `profile_obis_code` مثل **`1.0.99.1.0.255`** مع قنوات محددة — القراءة الفعلية تمر عبر مسار profile read في `gurux_tcp_ingress` (`execute_profile_read_over_tcp_ingress`).

### 5.5 قنوات البروفايل في المنصة (تعريف منطقي)

**API:** إنشاء قناة عبر  
`POST /api/v1/meters/{meter_id}/load-profile-channels`  
الحقول: `channel_code`, **`obis_code`**, `unit`, `interval_seconds`, `is_active`.

---

## 6. تدفق «نجاح القراءة» حتى تظهر في الواجهة

### 6.1 مسار التخزين (بدون تفاصيل عامل الشبكة الخارجي)

1. يُنشأ **دفعة قراءات** `MeterReadingBatch` مرتبطة بـ `meter_id` وربما `related_command_id` / `related_attempt_id` / `session_history_id`.
2. كل سطر قراءة: `MeterReading` يحتوي **`obis_code`**, `reading_type`, `value_numeric`/`value_text`, `quality`, `captured_at`, …
3. **الاستيراد الداخلي (من عامل/بوابة):**  
   `POST /api/v1/internal/meters/{meter_id}/ingest-reading-batch`  
   يتطلب ترويسة **`INTERNAL_API_TOKEN`** (قيمة من البيئة `internal_api_token`).

**نموذج الطلب (مبسّط):** `IngestReadingBatchRequest` — حقول رئيسية:

- `source_type`: من `ReadingSourceType` مثل `command_result`, `runtime_poll`, `scheduled_read`, …
- `captured_at`, `readings[]` كل عنصر فيه `obis_code`, `reading_type`, `captured_at`, قيم وجودة اختيارية.

### 6.2 مسار العرض في الويب

- قائمة قراءات المقياس: `GET /api/v1/meters/{meter_id}/readings?limit=…`
- صفحة `/readings` تجمع قراءات عدّة مقاييس ضمن نافذة عمل (حسب تنفيذ الواجهة).

---

## 7. تدفق «فصل / وصل المقياس» (Relay)

### 7.1 نموذج الأعمال في المنصة

- **عائلة الأمر:** `relay_control`
- **فئات القوالب:** `remote_disconnect`, `remote_reconnect`
- **عمليات الـ API للأمر:** `disconnect` / `reconnect` (`RelayControlCommandOperation`)

### 7.2 التنفيذ عند تشغيل الـ runtime الحي

- يُستدعى `execute_relay_control_over_tcp_ingress` مع:
  - نفس `LiveTcpDlmsSessionConfig` (IEC/DLMS/مهلات/بث SNRM…)
  - **OBIS ثابت للريلاي:** `0.0.96.3.10.255`
  - اسم العملية: `remote_disconnect` أو `remote_reconnect`

### 7.3 الموافقات (Approval)

- أوامر قد تُنشأ بحالة `submitted_for_approval` ثم تُعتمد/تُرفض عبر مسارات `/api/v1/commands/{id}/approvals/…` (حسب صلاحيات المستخدم).

---

## 8. أوامر أخرى مرتبطة بالمقياس (من الكود)

| العائلة | الغرض المختصر |
|---------|----------------|
| `on_demand_read` | لقطة سجلات / OBIS قابلة للتمرير |
| `profile_capture` | قراءة بروفايل حمل عبر مسار Gurux |
| `clock_sync`, `connectivity_test`, `config_push` | مذكورة كنماذج أعمال؛ التفاصيل التنفيذية في خدمات/محولات أخرى |

**Bulk للموافقات:** في الخدمة الحالية يُسمح في حزمة واحدة بـ **`relay_control`** و **`on_demand_read`** فقط (رفض صريح لـ `profile_capture` في مسار الـ bulk وفق كود الخدمة).

---

## 9. حالات التنفيذ والجودة

### 9.1 حالة الأمر `CommandStatus`

`pending` → `scheduled` → `queued` → `in_progress` → `succeeded` | `failed` | `timed_out` | `cancelled` + `retry_wait` عند الحاجة.

### 9.2 جودة القراءة `ReadingQuality`

`good`, `estimated`, `suspect`, `missing`.

### 9.3 نوع القراءة `ReadingType`

`scalar`, `register`, `instantaneous`, `demand`.

---

## 10. متغيرات بيئة ذات صلة مباشرة بالمقياس / الـ runtime

من `apps/api/.env.example` و `app/core/config.py` (أسماء الإعدادات كما في التطبيق):

| متغير | معنى |
|--------|------|
| `RUNTIME_TCP_METER_INGRESS_ENABLED` | تفعيل منفذ/مسار TCP ingress للمقياس |
| `RUNTIME_TCP_METER_INGRESS_HOST` / `PORT` | استماع العامل |
| `RUNTIME_TCP_METER_INGRESS_SOCKET_TIMEOUT_SECONDS` | مهلة المقبس |
| `RUNTIME_TCP_METER_INGRESS_BEFORE_FIRST_IEC_SEND_DELAY_MS` | تأخير قبل أول إرسال IEC |
| `INTERNAL_API_TOKEN` | توكن استدعاءات **internal** مثل استيراد القراءات |
| أسرار مطابقة لـ `password_secret_ref` أو `RUNTIME_SECRET_*` | كلمات مرور/مفاتيح DLMS |

**لا تُخزَّن في هذا الملف قيم إنتاج حقيقية** — عرّفها في `.env` أو مدير أسرار.

---

## 11. مسارات REST سريعة (مرجع)

| الغرض | المسار |
|--------|--------|
| قراءات مقياس | `GET /api/v1/meters/{meter_id}/readings` |
| دفعات القراءة | `GET /api/v1/meters/{meter_id}/reading-batches` |
| استيراد دفعة (داخلي) | `POST /api/v1/internal/meters/{meter_id}/ingest-reading-batch` |
| قنوات بروفايل | `GET/POST /api/v1/meters/{meter_id}/load-profile-channels` |
| أوامر حديثة | `GET /api/v1/commands/recent` |
| موافقات معلّقة | `GET /api/v1/commands/approvals/pending` |
| طلب أوامر مجمّع | `POST /api/v1/commands/bulk-requests` |
| قوالب الأوامر | `GET /api/v1/command-templates` |

الصلاحيات تُفرض عبر `require_permission` — ليست مفصّلة هنا.

---

## 12. ملفات كود “مصدر الحقيقة” للمطور

| الموضوع | الملف |
|---------|--------|
| جلسة TCP + IEC + DLMS + قراءة OBIS | `apps/api/app/runtime/adapters/gurux_tcp_ingress.py` |
| بناء الإعدادات + OBIS الافتراضية + ريلاي Gurux | `apps/api/app/runtime/adapters/dlms_cosem.py` |
| حل الأسرار | `apps/api/app/runtime/services/runtime_secret_refs.py` |
| نماذج القراءات | `apps/api/app/modules/readings/models.py`, `schemas.py`, `api.py` |
| نقاط الاتصال والبروتوكول | `apps/api/app/modules/connectivity/models.py`, `enums.py` |
| تعدادات الأوامر | `apps/api/app/modules/commands/enums.py` |
| إعدادات التطبيق | `apps/api/app/core/config.py` |

---

## 13. قيود واضحة لإعادة بناء نظام جديد

1. **المقياس الحقيقي** يحتاج **نموذج COSEM صحيح** لكل مصنع — OBIS أعلاه “شائعة” وليست ضماناً لكل جهاز.
2. **LOW auth** يحتاج كلمة مرور قابلة للحل من البيئة.
3. **Relay** يعتمد على وجود كائن **Disconnect control** على `0.0.96.3.10.255` ودعم الجهاز للـ methods.
4. المنصة تفصل بين **تنفيذ البروتوكول** و**تخزين القراءة**: يمكن بناء عامل خارجي يملأ `ingest-reading-batch` دون Gurux داخل API.
5. ما ورد هنا مبني على **نسخة المستودع الحالية**؛ أي فرع آخر قد يختلف.

---

*آخر تحديث للمحتوى: استخراج من شجرة `sunrise-hes-platform` (طبقة API + runtime).*
