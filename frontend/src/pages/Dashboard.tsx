import { useCallback, useEffect, useState } from "react";
import type { ConnectionEvent, DashboardStats } from "../api";
import { fetchIngressEvents, fetchStats } from "../api";

function formatWindow(sec: number): string {
  if (sec < 60) return `${sec} ثانية`;
  if (sec < 3600) return `${Math.round(sec / 60)} دقيقة`;
  return `${Math.round(sec / 3600)} ساعة`;
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [events, setEvents] = useState<ConnectionEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setError(null);
    try {
      const [s, e] = await Promise.all([fetchStats(), fetchIngressEvents(15)]);
      setStats(s);
      setEvents(e);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تعذر التحميل");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const id = setInterval(load, 15_000);
    return () => clearInterval(id);
  }, [load]);

  if (loading && !stats) {
    return <p className="hint">جاري التحميل…</p>;
  }

  return (
    <>
      <h1 className="section-title">لوحة التحكم</h1>
      {error ? <div className="error-banner">{error}</div> : null}
      {stats ? (
        <div className="grid-stats">
          <div className="card">
            <h3>إجمالي المقاييس</h3>
            <div className="value">{stats.total_meters}</div>
          </div>
          <div className="card">
            <h3>متصل (تقريباً)</h3>
            <div className="value" style={{ color: "var(--accent)" }}>
              {stats.online_meters}
            </div>
            <div className="hint">
              يُحسب المتصل بظهور نشاط خلال آخر {formatWindow(stats.online_window_seconds)}
            </div>
          </div>
          <div className="card">
            <h3>غير متصل</h3>
            <div className="value" style={{ color: "var(--danger)" }}>
              {stats.offline_meters}
            </div>
          </div>
        </div>
      ) : null}

      <section className="events">
        <h2 className="section-title">آخر اتصالات المنفذ {8766}</h2>
        <p className="hint" style={{ marginTop: "-0.5rem", marginBottom: "1rem" }}>
          أي جهاز يتصل بـ TCP على هذا المنفذ يُسجَّل هنا. لربط المقياس بصف «متصل» أدخل نفس عنوان IP في
          بطاقة المقياس.
        </p>
        {events.length === 0 ? (
          <div className="card">
            <p style={{ margin: 0, color: "var(--muted)" }}>لا توجد أحداث بعد.</p>
          </div>
        ) : (
          <div className="events-list">
            {events.map((ev) => (
              <div key={ev.id} className="event-row">
                <span className="mono">{ev.peer_ip}</span>
                {ev.peer_port != null ? (
                  <span className="mono" style={{ color: "var(--muted)" }}>
                    :{ev.peer_port}
                  </span>
                ) : null}
                <time>{new Date(ev.created_at).toLocaleString("ar-IQ")}</time>
                {ev.bytes_preview_hex ? (
                  <span className="mono" style={{ flex: "1 1 100%", color: "var(--muted)" }}>
                    {ev.bytes_preview_hex.slice(0, 120)}
                    {ev.bytes_preview_hex.length > 120 ? "…" : ""}
                  </span>
                ) : null}
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
