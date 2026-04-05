import { FormEvent, useCallback, useEffect, useState } from "react";
import type { Meter } from "../api";
import {
  createMeter,
  fetchMeters,
  readMeterIdentity,
  relayDisconnect,
  relayReconnect,
  updateMeter,
} from "../api";

export default function Meters() {
  const [rows, setRows] = useState<Meter[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [info, setInfo] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dlmsMeterId, setDlmsMeterId] = useState<string | null>(null);
  const [scanValue, setScanValue] = useState("");

  const [name, setName] = useState("");
  const [serial, setSerial] = useState("");
  const [peerIp, setPeerIp] = useState("");
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    setError(null);
    setInfo(null);
    try {
      const list = await fetchMeters();
      setRows(list);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر التحميل");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!name.trim()) {
      setError("اسم المقياس مطلوب");
      return;
    }
    setSaving(true);
    setError(null);
    setInfo(null);
    try {
      await createMeter({
        name: name.trim(),
        serial_number: serial.trim() || null,
        peer_ip: peerIp.trim() || null,
        notes: notes.trim() || null,
      });
      setName("");
      setSerial("");
      setPeerIp("");
      setNotes("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشل الحفظ");
    } finally {
      setSaving(false);
    }
  }

  async function onScanSubmit(e: FormEvent) {
    e.preventDefault();
    const v = scanValue.trim();
    if (!v) return;
    setSaving(true);
    setError(null);
    setInfo(null);
    try {
      await createMeter({
        name: `مقياس ${v}`,
        serial_number: v,
      });
      setScanValue("");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشل الإضافة السريعة");
    } finally {
      setSaving(false);
    }
  }

  async function onReadIdentity(m: Meter) {
    setError(null);
    setInfo(null);
    if (!m.peer_ip?.trim()) {
      setError("أدخل peer_ip أولاً (عنوان يقبل DLMS من السيرفر، غالباً منفذ 4059).");
      return;
    }
    setDlmsMeterId(m.id);
    try {
      const r = await readMeterIdentity(m.id);
      const regs = Object.entries(r.registers || {})
        .map(([k, v]) => `${k}=${v}`)
        .join(" · ");
      setInfo(
        [
          r.serial_number ? `تسلسل: ${r.serial_number}` : null,
          r.serial_source_obis ? `(من ${r.serial_source_obis})` : null,
          r.message,
          regs ? `سجلات: ${regs}` : null,
        ]
          .filter(Boolean)
          .join(" "),
      );
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشلت قراءة DLMS");
    } finally {
      setDlmsMeterId(null);
    }
  }

  async function onRelay(m: Meter, mode: "disconnect" | "reconnect") {
    setError(null);
    setInfo(null);
    if (!m.peer_ip?.trim()) {
      setError("peer_ip مطلوب للتحكم بالفصل/الوصل.");
      return;
    }
    setDlmsMeterId(m.id);
    try {
      if (mode === "disconnect") await relayDisconnect(m.id);
      else await relayReconnect(m.id);
      setInfo(mode === "disconnect" ? "تم إرسال أمر الفصل (DLMS)." : "تم إرسال أمر الوصل (DLMS).");
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشل أمر الريلاي");
    } finally {
      setDlmsMeterId(null);
    }
  }

  async function saveSerial(m: Meter, value: string) {
    setError(null);
    setInfo(null);
    try {
      await updateMeter(m.id, { serial_number: value.trim() || null });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "فشل التحديث");
    }
  }

  if (loading) {
    return <p className="hint">جاري التحميل…</p>;
  }

  return (
    <>
      <h1 className="section-title">المقاييس</h1>
      {error ? <div className="error-banner">{error}</div> : null}
      {info ? <div className="info-banner">{info}</div> : null}

      <div className="card" style={{ marginBottom: "1.5rem" }}>
        <h3 style={{ marginTop: 0 }}>إضافة سريعة بالسكانر</h3>
        <form className="scan-row" onSubmit={onScanSubmit}>
          <input
            type="text"
            inputMode="text"
            autoComplete="off"
            placeholder="امسح الباركود أو أدخل الرقم التسلسلي ثم Enter"
            value={scanValue}
            onChange={(e) => setScanValue(e.target.value)}
          />
          <button type="submit" className="btn btn-primary" disabled={saving || !scanValue.trim()}>
            إضافة
          </button>
        </form>
      </div>

      <h2 className="section-title" style={{ fontSize: "1rem" }}>
        إضافة يدوية
      </h2>
      <form onSubmit={onSubmit} className="form-grid" style={{ maxWidth: 520 }}>
        <div className="form-row">
          <label htmlFor="name">الاسم</label>
          <input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="مثال: مقياس منطقة الكرادة"
            required
          />
        </div>
        <div className="form-row">
          <label htmlFor="serial">الرقم التسلسلي (اختياري)</label>
          <input
            id="serial"
            value={serial}
            onChange={(e) => setSerial(e.target.value)}
            placeholder="يُحدَّث لاحقاً من قراءة DLMS"
          />
        </div>
        <div className="form-row">
          <label htmlFor="peer_ip">عنوان IP للربط بالاتصال الوارد</label>
          <input
            id="peer_ip"
            value={peerIp}
            onChange={(e) => setPeerIp(e.target.value)}
            placeholder="مثال: 203.0.113.44"
          />
        </div>
        <div className="form-row">
          <label htmlFor="notes">ملاحظات</label>
          <textarea id="notes" value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        <button type="submit" className="btn btn-primary" disabled={saving} style={{ width: "fit-content" }}>
          حفظ المقياس
        </button>
      </form>

      <p className="hint" style={{ marginBottom: "1rem" }}>
        DLMS صادر: السيرفر يتصل بـ <span className="mono">peer_ip</span> على المنفذ الافتراضي{" "}
        <span className="mono">4059</span> (غيّره بـ <span className="mono">DLMS_TCP_PORT</span>).
        منفذ <span className="mono">8766</span> للاتصال الوارد من المقاييس منفصل.
      </p>

      <h2 className="section-title">القائمة</h2>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>الاسم</th>
              <th>التسلسل</th>
              <th>IP</th>
              <th>الحالة</th>
              <th>آخر ظهور</th>
              <th>DLMS</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ color: "var(--muted)" }}>
                  لا توجد مقاييس بعد.
                </td>
              </tr>
            ) : (
              rows.map((m) => (
                <tr key={m.id}>
                  <td>{m.name}</td>
                  <td>
                    <InlineSerial
                      meter={m}
                      onSave={(v) => saveSerial(m, v)}
                      disabled={saving}
                    />
                  </td>
                  <td className="mono">{m.peer_ip ?? "—"}</td>
                  <td>
                    <span className={`badge ${m.is_online ? "ok" : "off"}`}>
                      {m.is_online ? "متصل" : "غير متصل"}
                    </span>
                  </td>
                  <td style={{ fontSize: "0.8rem", color: "var(--muted)" }}>
                    {m.last_seen_at ? new Date(m.last_seen_at).toLocaleString("ar-IQ") : "—"}
                  </td>
                  <td>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem" }}>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        style={{ fontSize: "0.75rem", padding: "0.3rem 0.5rem" }}
                        disabled={saving || dlmsMeterId === m.id}
                        onClick={() => onReadIdentity(m)}
                      >
                        قراءة
                      </button>
                      <button
                        type="button"
                        className="btn btn-ghost"
                        style={{ fontSize: "0.75rem", padding: "0.3rem 0.5rem" }}
                        disabled={saving || dlmsMeterId === m.id}
                        onClick={() => onRelay(m, "disconnect")}
                      >
                        فصل
                      </button>
                      <button
                        type="button"
                        className="btn btn-primary"
                        style={{ fontSize: "0.75rem", padding: "0.3rem 0.5rem" }}
                        disabled={saving || dlmsMeterId === m.id}
                        onClick={() => onRelay(m, "reconnect")}
                      >
                        وصل
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}

function InlineSerial({
  meter,
  onSave,
  disabled,
}: {
  meter: Meter;
  onSave: (v: string) => void;
  disabled: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState(meter.serial_number ?? "");

  useEffect(() => {
    setVal(meter.serial_number ?? "");
  }, [meter.serial_number]);

  if (editing) {
    return (
      <span style={{ display: "flex", gap: "0.35rem", alignItems: "center" }}>
        <input
          className="mono"
          style={{ minWidth: 140 }}
          value={val}
          onChange={(e) => setVal(e.target.value)}
        />
        <button
          type="button"
          className="btn btn-primary"
          style={{ fontSize: "0.75rem", padding: "0.25rem 0.5rem" }}
          disabled={disabled}
          onClick={() => {
            onSave(val);
            setEditing(false);
          }}
        >
          حفظ
        </button>
      </span>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setEditing(true)}
      className="btn btn-ghost"
      style={{
        fontSize: "0.8rem",
        padding: "0.2rem 0.45rem",
        fontFamily: "var(--mono)",
      }}
    >
      {meter.serial_number ?? "تعيين"}
    </button>
  );
}
