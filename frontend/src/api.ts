const API = "/api/v1";

/** طلبات DLMS قد تطول؛ Nginx عادة ~٧٥ث، نحدّ العميل قريباً من ذلك */
const DLMS_FETCH_TIMEOUT_MS = 90_000;

export type DashboardStats = {
  total_meters: number;
  online_meters: number;
  offline_meters: number;
  online_window_seconds: number;
};

export type Meter = {
  id: string;
  name: string;
  serial_number: string | null;
  peer_ip: string | null;
  notes: string | null;
  created_at: string;
  last_seen_at: string | null;
  is_online: boolean;
};

export type ConnectionEvent = {
  id: string;
  peer_ip: string;
  peer_port: number | null;
  bytes_preview_hex: string | null;
  created_at: string;
};

async function parseError(res: Response): Promise<string> {
  try {
    const j = await res.json();
    if (typeof j.detail === "string") return j.detail;
    if (Array.isArray(j.detail)) {
      return j.detail
        .map((d: { msg?: string; type?: string }) => d.msg || d.type || JSON.stringify(d))
        .join(" · ");
    }
    if (j.detail != null && typeof j.detail === "object") {
      return JSON.stringify(j.detail);
    }
    return res.statusText;
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

function abortMessage(): Error {
  return new Error(
    "انتهت مهلة الطلب (~٩٠ ثانية). غالباً المقياس لا يستجيب على العنوان/المنفذ (أو جدار ناري).",
  );
}

async function postWithDlmsTimeout(path: string): Promise<Response> {
  const ctrl = new AbortController();
  const t = window.setTimeout(() => ctrl.abort(), DLMS_FETCH_TIMEOUT_MS);
  try {
    return await fetch(`${API}${path}`, { method: "POST", signal: ctrl.signal });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") throw abortMessage();
    throw e;
  } finally {
    window.clearTimeout(t);
  }
}

export async function fetchStats(): Promise<DashboardStats> {
  const res = await fetch(`${API}/stats`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchMeters(): Promise<Meter[]> {
  const res = await fetch(`${API}/meters`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function createMeter(body: {
  name: string;
  serial_number?: string | null;
  peer_ip?: string | null;
  notes?: string | null;
}): Promise<Meter> {
  const res = await fetch(`${API}/meters`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function updateMeter(
  id: string,
  body: Partial<{
    name: string;
    serial_number: string | null;
    peer_ip: string | null;
    notes: string | null;
  }>,
): Promise<Meter> {
  const res = await fetch(`${API}/meters/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function fetchIngressEvents(limit = 20): Promise<ConnectionEvent[]> {
  const res = await fetch(`${API}/ingress/events?limit=${limit}`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export type DlmsReadResult = {
  ok: boolean;
  serial_number: string | null;
  serial_source_obis: string | null;
  registers: Record<string, string>;
  message: string | null;
};

export async function readMeterIdentity(meterId: string): Promise<DlmsReadResult> {
  const res = await postWithDlmsTimeout(`/meters/${meterId}/read-identity`);
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function relayDisconnect(meterId: string): Promise<void> {
  const res = await postWithDlmsTimeout(`/meters/${meterId}/relay/disconnect`);
  if (!res.ok) throw new Error(await parseError(res));
}

export async function relayReconnect(meterId: string): Promise<void> {
  const res = await postWithDlmsTimeout(`/meters/${meterId}/relay/reconnect`);
  if (!res.ok) throw new Error(await parseError(res));
}
