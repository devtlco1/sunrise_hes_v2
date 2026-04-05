const API = "/api/v1";

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
    return res.statusText;
  } catch {
    return res.statusText;
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
  const res = await fetch(`${API}/meters/${meterId}/read-identity`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
  return res.json();
}

export async function relayDisconnect(meterId: string): Promise<void> {
  const res = await fetch(`${API}/meters/${meterId}/relay/disconnect`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
}

export async function relayReconnect(meterId: string): Promise<void> {
  const res = await fetch(`${API}/meters/${meterId}/relay/reconnect`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(await parseError(res));
}
