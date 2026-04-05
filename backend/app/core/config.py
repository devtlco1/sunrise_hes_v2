from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://hes:hes@localhost:5432/hes"
    api_prefix: str = "/api/v1"
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    tcp_ingress_host: str = "0.0.0.0"
    tcp_ingress_port: int = 8766
    tcp_ingress_enabled: bool = True

    online_window_seconds: int = 900

    # Outbound DLMS (Gurux) — اتصال من السيرفر إلى المقياس على peer_ip:dlms_tcp_port
    # الافتراضي 8766 ليتوافق مع مقاييس مبرمجة على نفس منفذ الـ ingress
    dlms_tcp_port: int = 8766
    dlms_client_address: int = 16
    dlms_server_address: int = 1
    dlms_interface: str = "WRAPPER"
    dlms_authentication: str = "NONE"
    dlms_password: str | None = None
    dlms_extra_read_obis: str = "1.0.1.8.0.255,1.0.2.8.0.255"

    @property
    def dlms_password_effective(self) -> bytes | None:
        if not self.dlms_password or not str(self.dlms_password).strip():
            return None
        p = str(self.dlms_password).strip()
        if p.lower().startswith("0x"):
            return bytes.fromhex(p[2:])
        return p.encode("latin-1", errors="replace")

    def dlms_extra_read_obis_list(self) -> list[str]:
        raw = (self.dlms_extra_read_obis or "").strip()
        if not raw:
            return []
        return [x.strip() for x in raw.split(",") if x.strip()]


settings = Settings()
