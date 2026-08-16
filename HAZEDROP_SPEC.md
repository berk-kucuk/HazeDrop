# HazeDrop — Project Specification
> Anonymous · Encrypted · No Trace
> File transfer over Tor — Haze Protocol v2
> Version: 1.0.0 | Stack: Python 3.11+ | Platform: Linux

---

## 1. Proje Özeti

HazeDrop, dosyaları Tor ağı üzerinden anonim ve uçtan uca şifreli olarak paylaşmayı sağlayan bir uygulamadır.
Haze uygulamasıyla aynı güvenlik modelini ve Haze Protocol'ü kullanır; chat yerine dosya transferine odaklanır.

Gönderici taraf kendi Tor process'ini başlatır (sistem Tor'undan bağımsız), ephemeral hidden service açar,
dosyayı Haze Protocol ile şifreler ve .onion adresi üzerinden alıcıya ulaştırır.
Alıcı aynı şekilde kendi Tor process'i üzerinden SOCKS5 ile bağlanarak dosyayı indirir ve çözer.

Oturum biter, hiçbir şey kalmaz. Log yok, key yok, metadata yok.

Uygulama hem PyQt6 tabanlı frameless GUI hem de tam özellikli CLI sunar.
Default olarak GUI açılır. CLI'dan dosya/klasör verilebilir veya interactive mod başlatılabilir.

---

## 2. Güvenlik Modeli

Haze ile birebir aynı güvenlik modeli uygulanır:

| Özellik | Uygulama |
|---|---|
| Transport anonimliği | Tor onion routing — gönderici IP hiçbir zaman alıcıya açılmaz |
| Mesaj gizliliği | ChaCha20-Poly1305, her chunk için random nonce |
| Forward secrecy | Ephemeral session key — her oturumda yeniden üretilir, diske yazılmaz |
| Key exchange | Argon2id (şifre varsa) veya random key (URL fragmentına gömülür) |
| Oturum erişim kontrolü | Argon2id hash ile şifre doğrulaması, handshake öncesi |
| Persistent storage | Yok — veritabanı yok, log yok, geçici dosya yok |
| Panic | `os._exit(0)` — Python cleanup bypass, key'ler sıfırlanır |
| Hidden service key | Hiçbir zaman diske yazılmaz, Tor process memory'sinde tutulur |
| Tor process | Sistem Tor'undan izole, SocksPort ve ControlPort random seçilir |

### Panic Mekanizması
- Başlık çubuğunda **PANIC** butonu bulunur
- Tıklanınca: session key bellekte sıfırlanır (`ctypes.memset`) → tüm bağlantılar kesilir → `os._exit(0)`
- Python `atexit`, garbage collector veya herhangi bir cleanup handler çalışmaz
- CLI modunda: `Ctrl+\` (SIGQUIT) aynı etkiyi yapar

### Tor Process İzolasyonu (Haze ile aynı)
- Sistem genelindeki Tor kurulumundan bağımsız, uygulama kendi `tor` process'ini başlatır
- SocksPort: 19050–19150 arası rastgele
- ControlPort: 19200–19350 arası rastgele
- Local HTTP port: 50000–59999 arası rastgele
- Geçici data directory (`tempfile.mkdtemp()`) — çıkışta silinir
- Hidden service private key: Tor tarafından üretilir, memory'de tutulur, diske yazılmaz

---

## 3. Haze Protocol (v2)

### 3.1 Şifreleme Katmanı

```
Şifre varsa:
  password → Argon2id(time=3, mem=65536, par=2, hash_len=32) → 32-byte key
  salt = random 32 bytes → dosya header'ına gömülür

Şifre yoksa:
  key = os.urandom(32)
  Paylaşım URL'i: http://abc123.onion#<base64url(key)>
  (URL fragment Tor'a iletilmez — sadece client görür)

Şifreleme: ChaCha20-Poly1305 (AEAD)
  Nonce: random 12 bytes — her chunk için ayrı üretilir
  Tag: 16 bytes (Poly1305 authentication tag)
  Chunk boyutu: 64 KB plaintext
```

### 3.2 Dosya Format (Binary Wire Format)

```
┌───────────────────────────────────────────────────────┐
│  MAGIC        │ 8 bytes  │ ASCII: "HAZEDROP"          │
│  VERSION      │ 1 byte   │ 0x02                       │
│  FLAGS        │ 1 byte   │ bit0=has_password          │
│               │          │ bit1–7=reserved (0)        │
│  SALT         │ 32 bytes │ FLAGS bit0=1 ise vardır    │
│  FILENAME_LEN │ 2 bytes  │ big-endian uint16          │
│  FILENAME     │ N bytes  │ UTF-8                      │
│  ORIG_SIZE    │ 8 bytes  │ big-endian uint64          │
├───────────────────────────────────────────────────────┤
│  CHUNK (tekrarlı):                                    │
│    ENC_LEN    │ 4 bytes  │ big-endian uint32          │
│    NONCE      │ 12 bytes │ random per-chunk           │
│    CIPHERTEXT │ N bytes  │ plaintext + 16-byte tag    │
└───────────────────────────────────────────────────────┘
```

### 3.3 HTTP Transfer Protokolü

```
GET  /health     → 200 "ok"
GET  /info       → 200 JSON | 410 Gone
POST /download   → body: {"password": "..."} → 200 Stream | 401 | 410

/info response:
{
  "filename": "secret.zip",
  "size": 4194304,
  "password_required": true,
  "once": true,
  "downloads": 0,
  "expires_at": 1234567890,
  "haze_version": "2"
}

Response headers (200):
  Content-Type: application/octet-stream
  Content-Disposition: attachment; filename="<name>.hazedrop"
  X-HazeDrop-Filename: <original filename>
  X-HazeDrop-Size: <original size in bytes>
  X-HazeDrop-Version: 2
```

---

## 4. Proje Dizin Yapısı

```
hazedrop/
├── hazedrop/
│   ├── __init__.py                  # version = "1.0.0"
│   ├── main.py                      # entry point — GUI vs CLI kararı
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── crypto.py                # Haze Protocol v2 — ChaCha20 + Argon2id
│   │   ├── tor_manager.py           # Bağımsız Tor process yönetimi (Haze modeli)
│   │   ├── server.py                # aiohttp HTTP server — dosya sunucu
│   │   ├── receiver.py              # SOCKS5 üzerinden indirme + decrypt
│   │   └── session.py               # DropSession dataclass
│   │
│   ├── secure/
│   │   └── memory.py                # Key sıfırlama, panic handler
│   │
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── app.py                   # click komut tanımları
│   │   └── interactive.py           # rich interactive TUI
│   │
│   └── gui/
│       ├── __init__.py
│       ├── main_window.py           # Frameless ana pencere + custom title bar
│       ├── title_bar.py             # Custom app bar (drag, minimize, close, PANIC)
│       ├── send_panel.py            # Gönderme paneli
│       ├── receive_panel.py         # Alma paneli
│       ├── tor_status_widget.py     # Tor bağlantı durumu indikatörü
│       └── theme.py                 # QSS — OLED siyah + beyaz, Haze ile aynı stil
│
├── assets/
│   ├── icon.png                     # 256x256
│   └── icon.svg
│
├── installer/
│   └── install.sh                   # venv + desktop entry (Haze installer modeli)
│
├── pyproject.toml
├── PKGBUILD
└── README.md
```

---

## 5. Modül Detayları

### 5.1 `core/crypto.py` — Haze Protocol Crypto

**Sorumluluk:** Tüm şifreleme/çözme işlemleri. Dışarıya hiçbir key sızdırmaz.

```python
def derive_key(password: str, salt: bytes) -> bytes:
    """Argon2id: password → 32-byte key
    time_cost=3, memory_cost=65536, parallelism=2, hash_len=32"""

def hash_password_for_auth(password: str) -> str:
    """
    Şifre doğrulama için SHA-256 hash (Haze modeli):
    SHA-256("hazedrop-v2:" + password) → hex string
    Plaintext şifre hiçbir zaman wire'a çıkmaz.
    """

def generate_key() -> bytes:
    """os.urandom(32) — şifresiz mod"""

def generate_salt() -> bytes:
    """os.urandom(32)"""

def encrypt_file_chunked(
    filepath: str,
    key: bytes,
    salt: bytes | None = None,
    on_progress: Callable[[int, int], None] | None = None,
) -> Generator[bytes, None, None]:
    """
    Dosyayı 64KB chunk'lar halinde stream şifreler.
    İlk yield: header bytes
    Sonraki yield'lar: her şifreli chunk
    on_progress(bytes_processed, total_bytes) her chunk sonrası çağrılır.
    """

def decrypt_file_chunked(
    data: bytes,
    key: bytes,
) -> tuple[str, bytes]:
    """
    Tam şifreli blob'u çözer.
    Returns: (original_filename, plaintext_bytes)
    Hatalı key → cryptography.exceptions.InvalidTag
    Bozuk format → ValueError("Invalid HazeDrop file")
    """

def build_share_url(onion_address: str, key: bytes | None, password_protected: bool) -> str:
    """
    password_protected=True  → "http://abc.onion"  (şifreyi ayrı ilet)
    password_protected=False → "http://abc.onion#<base64url(key)>"
    """

def extract_key_from_url(url: str) -> bytes | None:
    """URL fragment'ından key çıkar. Fragment yoksa None."""
```

**Kütüphaneler:** `cryptography>=42` (ChaCha20Poly1305), `argon2-cffi>=23`

---

### 5.2 `secure/memory.py` — Güvenli Bellek ve Panic

**Sorumluluk:** Key'leri bellekte sıfırlamak, panic handler.

```python
def zero_bytes(data: bytearray) -> None:
    """ctypes.memset ile bytearray'i sıfırla"""

def secure_delete_key(key_ref: list) -> None:
    """
    key_ref[0] = key bytes objesi
    ctypes ile memory'deki içeriği sıfırla, referansı temizle.
    Python GC'nin key'i henüz toplamadığını varsay.
    """

def panic(session_keys: list[bytes]) -> None:
    """
    1. Her key'i zero_bytes ile sıfırla
    2. gc.collect() — objeler bellekten düşsün
    3. os._exit(0) — Python cleanup çalışmaz
    """

def register_sigquit_panic(keys_getter: Callable[[], list[bytes]]) -> None:
    """CLI için SIGQUIT (Ctrl+\) → panic() bağla"""
```

---

### 5.3 `core/session.py` — DropSession

```python
@dataclass
class DropSession:
    filepath: str
    filename: str
    filesize: int
    password: str | None        # None = şifresiz mod
    once: bool
    expire_seconds: int | None

    # runtime
    salt: bytes | None          # password varsa random 32 bytes
    key: bytes                  # derive_key veya generate_key
    created_at: float
    download_count: int = 0
    onion_address: str | None = None

    @property
    def is_password_protected(self) -> bool: ...

    @property
    def is_expired(self) -> bool:
        """once=True ve download_count>=1 → True
           expire_at geçtiyse → True"""

    @property
    def share_url(self) -> str:
        """build_share_url(onion_address, key, is_password_protected)"""

    def zero_key(self) -> None:
        """secure/memory.py — key'i sıfırla"""
```

---

### 5.4 `core/tor_manager.py` — Tor Process Yöneticisi

**Sorumluluk:** Haze ile aynı model — sistem Tor'undan bağımsız process.

```python
class TorManager:
    """
    Kendi tor process'ini başlatır.
    SocksPort: random 19050–19150
    ControlPort: random 19200–19350
    DataDirectory: tempfile.mkdtemp() → çıkışta silinir
    """

    def __init__(self): ...

    async def start(self, on_progress: Callable[[str], None] | None = None) -> None:
        """
        tor process başlat, bootstrap %100 olana kadar bekle.
        on_progress("Bootstrapping 50%...") gibi status callback'i çağırır.
        GUI'da Tor başlatma log'u göstermek için kullanılır.
        """

    def create_hidden_service(self, local_port: int) -> str:
        """
        Ephemeral hidden service — await_publication=True.
        Returns: "abc123def456.onion"
        Private key: Tor memory'sinde, diske yazılmaz.
        """

    async def renew_circuit(self) -> None:
        """NEWNYM sinyali gönder — mevcut bağlantılar korunur"""

    async def stop(self) -> None:
        """Process öldür, temp directory sil"""

    @property
    def socks_port(self) -> int: ...

    @property
    def control_port(self) -> int: ...
```

---

### 5.5 `core/server.py` — HTTP Server

```python
class TorDropServer:
    def __init__(
        self,
        session: DropSession,
        local_port: int,
        on_download_start: Callable | None = None,
        on_download_complete: Callable | None = None,
        on_wrong_password: Callable | None = None,
        on_expired: Callable | None = None,
    ): ...

    async def start(self) -> None:
        """aiohttp AppRunner — sadece 127.0.0.1 bind eder"""

    async def stop(self) -> None: ...
```

**Güvenlik notları:**
- Server `0.0.0.0`'a asla bind etmez, sadece `127.0.0.1`
- Yanlış şifrede HTTP 401, detay içermeyen generic mesaj
- Expired session'da HTTP 410
- `--once` race condition: `asyncio.Lock()` ile korunur, ilk indirme tamamlanana kadar ikinci istek bloklanır
- Key hiçbir response header'ına veya log'a yazılmaz

---

### 5.6 `core/receiver.py` — Downloader

```python
async def fetch_info(onion_url: str, socks_port: int) -> dict:
    """GET /info — SOCKS5 üzerinden"""

async def download_and_decrypt(
    onion_address: str,
    output_dir: str,
    socks_port: int,
    password: str | None = None,
    key_from_url: bytes | None = None,
    on_progress: Callable[[int, int], None] | None = None,
    on_info: Callable[[dict], None] | None = None,
) -> str:
    """
    1. GET /info → şifre gerekli mi?
    2. POST /download → stream al (SOCKS5 üzerinden)
    3. Key belirle: password → derive_key | key_from_url | hata
    4. decrypt_file_chunked() → plaintext
    5. output_dir'e kaydet (isim çakışmasında _1, _2 suffix)
    Returns: kaydedilen dosyanın tam yolu
    """
```

**Proxy:** `python-socks[asyncio]` (Haze ile aynı paket)
```python
from python_socks.async_.asyncio import Proxy
proxy = Proxy.from_url(f"socks5://127.0.0.1:{socks_port}")
```

---

### 5.7 `cli/app.py` — Click CLI

```python
@click.group(invoke_without_command=True)
@click.option("--cli", is_flag=True)
@click.pass_context
def main(ctx, cli):
    """Komut yok + --cli yok → GUI aç. --cli → interactive TUI."""

@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("-p", "--password", default=None)
@click.option("--once", is_flag=True)
@click.option("--expire", default=None, help="10m / 1h / 30s")
def send(filepath, password, once, expire): ...

@main.command()
@click.argument("onion_url")
@click.option("-p", "--password", default=None)
@click.option("-o", "--output", default=".", type=click.Path())
def receive(onion_url, password, output): ...
```

**Örnekler:**
```bash
hazedrop                              # GUI
hazedrop --cli                        # interactive TUI
hazedrop send dosya.zip               # şifresiz
hazedrop send dosya.zip -p sifre      # şifreli
hazedrop send dosya.zip --once        # tek indirme
hazedrop send dosya.zip --expire 10m  # 10 dakika expire
hazedrop receive abc123.onion -p sifre
hazedrop receive "abc123.onion#<key>" # şifresiz (URL'den key)
hazedrop receive abc123.onion -o ~/Downloads
```

---

### 5.8 `cli/interactive.py` — Rich TUI

```
╭─────────────────────────╮
│  ◈ HAZEDROP  v1.0.0     │
│  Anonymous · Encrypted  │
╰─────────────────────────╯

  [1]  Dosya Gönder
  [2]  Dosya Al
  [3]  Çıkış

▸ Seçim: _
```

**Gönderme akışı:**
```
📁  Dosya: /home/user/secret.zip
🔑  Şifre (boş = şifresiz): ****
⚡  Tek indirme? [e/H]: e
⏱   Süre limiti [boş=∞]: 10m

◈  Tor başlatılıyor...
   Bootstrapping 10%... 50%... 100% ✓
◈  Hidden service oluşturuluyor...

╭──────────────────────────────────────────╮
│  ◈  HAZEDROP LINK                        │
│                                          │
│  http://abc123def456ghij.onion           │
│  Şifre: **** (alıcıya güvenli iletin)    │
│                                          │
│  📦 secret.zip · 4.2 MB                 │
│  ⚡ Tek indirme · 10 dakika              │
╰──────────────────────────────────────────╯

  ◌  İndirme bekleniyor...  [Ctrl+C iptal · Ctrl+\ PANIC]

  ↓  İndirme başladı... ████████░░ 82%
  ✓  Tamamlandı. Bağlantı kapatılıyor.
```

---

### 5.9 `gui/theme.py` — OLED Dark Theme

Haze ile aynı görsel dil. Siyah-beyaz, minimal, modern.

```python
COLORS = {
    "bg":           "#000000",   # OLED siyah — pencere arkaplanı
    "bg_panel":     "#0a0a0a",   # panel arkaplanı
    "bg_elevated":  "#111111",   # input, card arkaplanı
    "border":       "#1e1e1e",   # ince border
    "border_focus": "#333333",   # focus durumunda border
    "accent":       "#ffffff",   # birincil aksan — beyaz
    "accent_dim":   "#888888",   # ikincil metin, placeholder
    "text":         "#ffffff",   # ana metin
    "text_dim":     "#666666",   # ikincil metin
    "text_muted":   "#333333",   # çok soluk metin
    "success":      "#22c55e",   # yeşil
    "warning":      "#f59e0b",   # sarı
    "error":        "#ef4444",   # kırmızı
    "panic":        "#ef4444",   # PANIC buton rengi
}

# STYLESHEET: tüm QWidget, QPushButton, QLineEdit, QLabel,
# QProgressBar, QCheckBox stillerini kapsar.
# app.setStyleSheet(STYLESHEET) ile uygulanır.
```

---

### 5.10 `gui/title_bar.py` — Custom App Bar

Haze ile birebir aynı frameless title bar konsepti.

**Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  ◈ HAZEDROP    ● TOR AKTIF    [PANIC]    [─]  [×]      │
│   (ikon+isim)  (durum dot)   (kırmızı)  (min)(kapat)   │
└─────────────────────────────────────────────────────────┘
```

**Bileşenler:**
- **Sol:** `◈ HAZEDROP` — ikon + uygulama adı (tıklanmaz)
- **Orta:** Tor durum indikatörü
  - `● Başlatılıyor...` gri
  - `● Tor Aktif` yeşil (tıklanınca onion adresi veya debug bilgisi)
  - `● Tor Bağlanamadı` kırmızı
- **PANIC butonu:** Sağda, kırmızı, `os._exit(0)` tetikler — her zaman görünür
- **Minimize / Kapat:** En sağ, standart pencere kontrolleri
- **Drag:** Title bar'a basılı sürükleyerek pencere taşınır
  (`mousePressEvent` + `mouseMoveEvent`)

**Implementasyon:**
```python
class TitleBar(QWidget):
    panic_triggered = pyqtSignal()

    def __init__(self, parent): ...

    def set_tor_status(self, status: Literal["starting", "active", "error"]) -> None: ...

    def mousePressEvent(self, event): ...   # drag başlat
    def mouseMoveEvent(self, event): ...    # pencere taşı

    def _on_panic_clicked(self):
        """session.zero_key() → os._exit(0)"""
```

---

### 5.11 `gui/main_window.py` — Ana Pencere

**Özellikler:**
- `Qt.WindowType.FramelessWindowHint` — sistem pencere dekorasyonu yok
- `setAttribute(Qt.WA_TranslucentBackground)` — şeffaf arka plan desteği
- Minimum boyut: 820×560
- Sol sidebar + sağda içerik paneli layout'u

**Pencere Layout:**
```
┌─────────────────────────────────────────────────────────┐
│  ◈ HAZEDROP     ● TOR AKTIF     [PANIC]    [─]  [×]    │  ← TitleBar
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  [📤]    │                                              │
│  Gönder  │          (aktif panel — Send veya Receive)   │
│          │                                              │
│  [📥]    │                                              │
│  Al      │                                              │
│          │                                              │
│  ──────  │                                              │
│          │                                              │
│  v1.0.0  │                                              │
└──────────┴──────────────────────────────────────────────┘
```

**Sidebar:**
- `📤 Gönder` ve `📥 Al` butonları — aktif olanın arka planı hafif aydınlık
- Alt kısımda versiyon numarası (küçük, soluk)
- Sidebar genişliği: 72px sabit

**Qt + asyncio:**
- `qasync.QEventLoop` kullanılır (`QEventLoop` yerine)
- Tor başlatma, hidden service oluşturma → `asyncio.ensure_future()`
- UI callback'leri → `qasync.asyncSlot()` decorator
- Tor `create_hidden_service` bloklayan çağrı → `loop.run_in_executor(None, ...)`

---

### 5.12 `gui/send_panel.py` — Gönderme Paneli

```
┌──────────────────────────────────────────┐
│                                          │
│  DOSYA GÖNDER                            │
│                                          │
│  ┌──────────────────────────────────┐    │
│  │  Dosyayı buraya sürükle          │    │
│  │  veya tıkla seç                  │    │
│  └──────────────────────────────────┘    │
│  secret.zip · 4.2 MB (seçilince)         │
│                                          │
│  Şifre                                   │
│  [  ••••••••••••       ] [👁]            │
│  ○ Şifresiz gönder (URL'e gömülür)       │
│                                          │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄    │
│                                          │
│  [✓] Tek indirme sonrası kapat           │
│  [ ] Süre limiti  [____] dakika          │
│                                          │
│  ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄    │
│                                          │
│         [  ◈  PAYLAŞ  ]                 │
│                                          │
│  ════════════════════════════════════    │
│  (paylaşım aktifken görünür)             │
│                                          │
│  LINK                                    │
│  ┌──────────────────────────────────┐   │
│  │ http://abc123def456ghij.onion    │   │
│  └──────────────────────────────────┘   │
│  [📋 Kopyala]  [□ QR Kod]              │
│                                          │
│  ● İndirme bekleniyor...                 │
│  [██████████░░░░░░░░░░] (progress)       │
│                                          │
│         [  ✕  DURDUR  ]                 │
│                                          │
└──────────────────────────────────────────┘
```

**Akış:**
1. Drag-drop veya dosya seç diyaloğu
2. Şifre gir veya "şifresiz" seç
3. Seçenekleri belirle (once, expire)
4. `PAYLAŞ` → TorManager başlat → server başlat → hidden service → .onion göster
5. İndirme progress bar ile göster
6. `once=True` tamamlanınca otomatik durdur
7. `DURDUR` → session.zero_key() → server stop → hidden service kaldır

---

### 5.13 `gui/receive_panel.py` — Alma Paneli

```
┌──────────────────────────────────────────┐
│                                          │
│  DOSYA AL                                │
│                                          │
│  Onion Adresi                            │
│  [ http://abc123def456.onion      ]      │
│                                          │
│  Şifre (gerekiyorsa)                     │
│  [  ••••••••           ] [👁]            │
│                                          │
│  Kayıt Klasörü                           │
│  [  ~/Downloads               ] [📂]    │
│                                          │
│         [  📥  İNDİR  ]                 │
│                                          │
│  ════════════════════════════════════    │
│  (indirme başlayınca görünür)            │
│                                          │
│  Dosya: secret.zip · 4.2 MB             │
│  [████████████░░░░░░░░] 60%  2.5/4.2 MB │
│                                          │
│  ● İndiriliyor...                        │
│  ✓ Tamamlandı → ~/Downloads/secret.zip  │
│    [📂 Klasörü Aç]                      │
│                                          │
└──────────────────────────────────────────┘
```

**URL parsing:**
- `http://abc.onion#<key>` → key fragment'tan otomatik çıkarılır, şifre alanı gizlenir
- `http://abc.onion` → şifre alanı gösterilir

---

## 6. main.py — Entry Point

```python
def main():
    import sys
    args = sys.argv[1:]

    cli_triggers = {"send", "receive", "--cli", "-h", "--help", "--version"}

    if any(a in cli_triggers for a in args) or (args and not args[0].startswith("-")):
        from hazedrop.cli.app import main as cli_main
        cli_main(standalone_mode=True)
    else:
        from hazedrop.gui.main_window import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()
```

---

## 7. pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "hazedrop"
version = "1.0.0"
description = "Anonymous encrypted file transfer over Tor — Haze Protocol"
license = { text = "GPL-3.0" }
requires-python = ">=3.11"
dependencies = [
    "aiohttp>=3.9",
    "python-socks[asyncio]>=2.4",
    "cryptography>=42",
    "argon2-cffi>=23",
    "stem>=1.8",
    "click>=8.1",
    "rich>=13",
    "PyQt6>=6.6",
    "qasync>=0.27",
    "qrcode[pil]>=7.4",
]

[project.scripts]
hazedrop = "hazedrop.main:main"

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "black", "mypy"]
```

---

## 8. PKGBUILD (AUR)

```bash
pkgname=hazedrop
pkgver=1.0.0
pkgrel=1
pkgdesc="Anonymous encrypted file transfer over Tor — Haze Protocol"
arch=('x86_64')
url="https://github.com/berkkucukk/hazedrop"
license=('GPL3')
depends=(
    'python>=3.11'
    'tor'
    'python-pyqt6'
    'python-cryptography'
    'python-click'
    'python-rich'
    'python-stem'
    'python-argon2-cffi'
)
makedepends=('python-build' 'python-installer' 'python-wheel' 'python-setuptools')
source=("$pkgname-$pkgver.tar.gz::$url/archive/v$pkgver.tar.gz")
sha256sums=('SKIP')

build() {
    cd "$pkgname-$pkgver"
    python -m build --wheel --no-isolation
}

package() {
    cd "$pkgname-$pkgver"
    python -m installer --destdir="$pkgdir" dist/*.whl
    install -Dm644 assets/icon.png "$pkgdir/usr/share/pixmaps/hazedrop.png"
    install -Dm644 hazedrop.desktop "$pkgdir/usr/share/applications/hazedrop.desktop"
}
```

---

## 9. Bağımlılıklar

| Paket | Rol |
|---|---|
| `stem>=1.8` | Tor process başlatma, control, hidden service |
| `aiohttp>=3.9` | Async HTTP server (gönderici) |
| `python-socks[asyncio]>=2.4` | SOCKS5 proxy (alıcı — Haze ile aynı paket) |
| `cryptography>=42` | ChaCha20-Poly1305 (Haze Protocol) |
| `argon2-cffi>=23` | Argon2id key derivation |
| `PyQt6>=6.6` | GUI |
| `qasync>=0.27` | Qt + asyncio event loop entegrasyonu |
| `click>=8.1` | CLI komutları |
| `rich>=13` | Interactive TUI, progress bar |
| `qrcode[pil]>=7.4` | .onion → QR kod |

**Sistem bağımlılığı:** `tor` binary PATH'te olmalı (sistem paketi yeterli).

---

## 10. Önemli Teknik Notlar

### Frameless Pencere + Drag
```python
# main_window.py
self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

# title_bar.py
def mousePressEvent(self, event):
    if event.button() == Qt.MouseButton.LeftButton:
        self._drag_pos = event.globalPosition().toPoint() - self.window().pos()

def mouseMoveEvent(self, event):
    if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
        self.window().move(event.globalPosition().toPoint() - self._drag_pos)
```

### Qt + asyncio (qasync)
```python
# main_window.py → launch_gui()
import qasync

app = QApplication(sys.argv)
loop = qasync.QEventLoop(app)
asyncio.set_event_loop(loop)
with loop:
    window = MainWindow()
    window.show()
    loop.run_forever()
```

### Tor Process (Haze Modeli)
```python
# tor_manager.py
import stem.process
from stem.control import Controller

self._process = stem.process.launch_tor_with_config(
    config={
        "SocksPort": str(self.socks_port),
        "ControlPort": str(self.control_port),
        "DataDirectory": self._data_dir,
        "Log": "notice stdout",
    },
    init_msg_handler=on_progress,
    take_ownership=True,
)
```

### PANIC — Key Sıfırlama
```python
# secure/memory.py
import ctypes, os, gc

def panic(keys: list[bytes]) -> None:
    for key in keys:
        if key:
            ctypes.memset(id(key) + ...offset..., 0, len(key))
    gc.collect()
    os._exit(0)
```

### Güvenlik Zorunlulukları
- HTTP server sadece `127.0.0.1` bind eder — asla `0.0.0.0`
- Key, onion URL dışında hiçbir yere (log, UI label, clipboard) yazılmaz
- Şifre hash'i: `SHA-256("hazedrop-v2:" + password)` — plaintext wire'a çıkmaz
- `--once` lock: `asyncio.Lock()` — concurrent download race condition engeli
- Tor data directory: `tempfile.mkdtemp()` → `atexit` ve `TorManager.stop()` ile silinir
- Session sonunda `session.zero_key()` her zaman çağrılır (normal çıkış + panic)

---

## 11. Geliştirme Sırası

```
1.  secure/memory.py        → panic, key sıfırlama — en temel güvenlik katmanı
2.  core/crypto.py          → Haze Protocol, test edilebilir
3.  core/session.py         → DropSession dataclass
4.  core/tor_manager.py     → Tor process izolasyonu
5.  core/server.py          → HTTP server (curl ile test)
6.  core/receiver.py        → İndirme + decrypt
7.  cli/app.py              → click CLI
8.  cli/interactive.py      → rich TUI
9.  gui/theme.py            → OLED QSS
10. gui/title_bar.py        → Custom app bar + PANIC + drag
11. gui/tor_status_widget.py→ Durum indikatörü
12. gui/send_panel.py       → Gönderme paneli
13. gui/receive_panel.py    → Alma paneli
14. gui/main_window.py      → Ana pencere + entegrasyon
15. main.py                 → Entry point
16. installer/install.sh    → Haze installer modeli
17. PKGBUILD                → AUR
```
