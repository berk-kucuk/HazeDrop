# HazeDrop

**Anonymous encrypted file transfer over Tor — Haze Protocol v2**

HazeDrop, dosyaları Tor ağı üzerinden kimlik tespiti olmaksızın aktarmanızı sağlayan, uçtan uca şifreli bir dosya transfer uygulamasıdır. Gönderen ve alıcı arasında hiçbir merkezi sunucu bulunmaz; bağlantı doğrudan `.onion` adresi üzerinden kurulur.

---

## Özellikler

| Özellik | Açıklama |
|---|---|
| **Uçtan uca şifreleme** | ChaCha20-Poly1305 AEAD, 64 KB chunk'lar halinde |
| **Tor hidden service** | Her paylaşım için otomatik `.onion` adresi oluşturulur |
| **Şifresiz mod** | Şifreleme anahtarı URL fragment'ına gömülür (`#key`) |
| **Şifreli mod** | Argon2id ile anahtar türetme, tuz header'a eklenir |
| **SHA-256 doğrulama** | Dosya bütünlüğü hash ile doğrulanır (`#key:hash`) |
| **Web arayüzü** | Alıcı tarayıcıdan da indirebilir, masaüstü tasarımına uyumlu HTML sayfası |
| **Maksimum indirme limiti** | Kaç kez indirilebileceği ayarlanabilir (0 = sınırsız) |
| **3 yanlış şifre kilidi** | 3 başarısız denemede link otomatik iptal edilir |
| **Süre sınırı** | `30s`, `10m`, `1h`, `2d`, `1h30m` (max `30d`) |
| **PANIC butonu** | Tek tıkla hafızadaki anahtarlar silinir ve uygulama kapanır |
| **Metin modu** | Dosya yerine metin/snippet paylaşımı |
| **Klasör zip** | Klasörler otomatik olarak ZIP arşivine dönüştürülür |
| **QR kod** | Paylaşım linki QR kod olarak gösterilir |
| **Transfer geçmişi** | SQLite veritabanı, yapılandırılabilir TTL |
| **Sistem tepsisi** | Uygulama arka planda çalışmaya devam eder |
| **Tor köprüleri** | Tor engellenmiş ağlarda obfs4/meek bridge desteği |
| **Devre yenileme** | Tek tıkla yeni Tor devresi (NEWNYM) |
| **GUI + CLI** | PyQt6 arayüzü ve tam özellikli komut satırı |
| **PANIC desteği** | `Ctrl+\` ile kriptografik bellek temizleme |

---

## Interface

Frameless window that can be resized from any edge, maximized by
double-clicking the title bar, and which restores its last position and size on
launch. The primary action button (`SHARE` / `DOWNLOAD` / `SAVE`) is pinned to
the bottom of every panel, so it is always reachable without scrolling.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+1` / `Ctrl+2` / `Ctrl+3` | Switch to the Send / Receive / Settings panel |
| `Ctrl+\` | PANIC — wipe keys from memory and quit |
| `Ctrl+W` | Close the window (goes to the tray if minimize-to-tray is on) |

---

## Haze Protocol v2

```
Gönderen                                    Alıcı
────────                                    ─────
aiohttp sunucu başlatılır
Tor hidden service oluşturulur
  ┌─ URL: http://xxxxx.onion#base64key:hash16
  │
  └──────────────── Tor ağı ────────────────►  /info   → dosya adı, boyut, şifre?
                                               /download → ChaCha20-Poly1305 stream
                                               /web-download → plaintext (tarayıcı)
```

### URL Formatları

| Durum | URL |
|---|---|
| Şifresiz | `http://xxxxx.onion#base64key:sha256hex16` |
| Şifreli | `http://xxxxx.onion` (şifre ayrıca iletilir) |

### Şifreleme Akışı

```
header  = MAGIC(8) + VERSION(1) + FLAGS(1) + [SALT(32)] + FILENAME_LEN(2) + FILENAME + FILESIZE(8)
chunks  = enc_len(4) + nonce(12) + ChaCha20Poly1305(chunk)   × N
```

---

## Gereksinimler

| Paket | Versiyon |
|---|---|
| Python | ≥ 3.11 |
| Tor | herhangi |
| PyQt6 | ≥ 6.6 |
| aiohttp | ≥ 3.9 |
| cryptography | ≥ 42 |
| argon2-cffi | ≥ 23 |
| stem | ≥ 1.8 |
| qasync | ≥ 0.27 |
| qrcode[pil] | ≥ 7.4 |

---

## Kurulum

### Maze deposundan

**Maze Linux'ta** depo zaten tanımlı:

```bash
sudo pacman -S hazedrop
```

**Arch Linux ve Arch tabanlı dağıtımlarda** depoyu bir kez ekleyin:

1. Maze imzalama anahtarını içe aktarın ve güvenin:

   ```bash
   curl -O https://mazerepo.berkkucukk.com.tr/packages/mazelinux.gpg
   gpg --show-keys --with-fingerprint mazelinux.gpg
   sudo pacman-key --add mazelinux.gpg
   sudo pacman-key --lsign-key 7C4D515A6B930CB04794CEF6147C8159B3E2EE5F
   ```

   `gpg`'nin yazdığı parmak izi `7C4D 515A 6B93 0CB0 4794  CEF6 147C 8159 B3E2 EE5F` olmalı.

2. Depoyu `/etc/pacman.conf` dosyasının sonuna ekleyin:

   ```ini
   [mazelinux]
   SigLevel = Required DatabaseOptional
   Server = https://mazerepo.berkkucukk.com.tr/packages
   ```

3. Senkronize edin ve kurun:

   ```bash
   sudo pacman -Syu hazedrop
   ```

İsterseniz `mazelinux-keyring` paketini de kurun; imzalama anahtarını pacman üzerinden güncel tutar.

Kaldırmak için: `sudo pacman -Rns hazedrop`.

### Kaynaktan derleme

Paket, bu çalışma ağacından `build-pkg.sh` ile derlenir ve yayındaki paket gibi pacman ile kurulur:

```bash
sudo pacman -S --needed base-devel git
git clone https://github.com/berk-kucuk/HazeDrop.git
cd HazeDrop
sudo pacman -S --needed $(bash -c 'source packaging/PKGBUILD; echo "${depends[@]}" "${makedepends[@]}"')
./build-pkg.sh --install
```

`--install` verilmezse paket yalnızca `dist-pkg/` altına derlenir.

`maze-python` (ortak Python çalışma ortamı) Maze deposundan gelir; bu yüzden önce depoyu ekleyin (yukarıdaki 1–2. adımlar).

### Geliştirme

Bir çalışma kopyasından sanal ortamda doğrudan çalıştırmak için:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -e .
hazedrop
```

---

## Kullanım

### GUI (Grafik Arayüz)

```bash
hazedrop
```

#### Dosya Gönderme

1. **SEND** sekmesine geç
2. Dosyayı sürükle-bırak ya da tıklayarak seç
3. İsteğe bağlı: şifre belirle, indirme limiti ve süre sınırı ayarla
4. **SHARE** butonuna bas
5. Tor ağı hazır olunca paylaşım linki belirir
6. Linki veya QR kodu alıcıya ilet

#### Dosya Alma

1. **RECV** sekmesine geç
2. `.onion` adresini gir
3. Gerekiyorsa şifreyi gir
4. Kayıt klasörünü seç
5. **DOWNLOAD** butonuna bas

#### Ayarlar

**CONF** sekmesinden:
- İndirme klasörü
- Varsayılan indirme limiti
- Geçmiş kaydı (TTL süresi)
- Sistem tepsisine küçültme
- Tor köprüleri (obfs4, meek vb.)

### CLI

```bash
# Dosya gönder
hazedrop send dosya.pdf

# Şifreli gönder, 1 kez indirilebilir, 30 dakika geçerli
hazedrop send gizli.pdf --password s3cr3t --once --expire 30m

# Dosya al
hazedrop receive "http://xxxxx.onion#base64key:hash"

# Şifreli al
hazedrop receive "http://xxxxx.onion" --password s3cr3t --output ~/Downloads

# İnteraktif TUI
hazedrop --cli
```

### CLI — Tüm Seçenekler

```
hazedrop send FILE [OPTIONS]
  -p, --password TEXT    Şifreleme şifresi
  --once                 Tek indirmede link silinir
  --expire TEXT          Expiry: 30s / 10m / 1h / 2d / 1h30m
                         (bare number = seconds, max 30d)

hazedrop receive URL [OPTIONS]
  -p, --password TEXT    Çözme şifresi
  -o, --output PATH      Kayıt klasörü (varsayılan: .)
```

---

## Web Arayüzü

Paylaşım linki tarayıcıda açılabilir. Gönderen aktif olduğu sürece herhangi bir Tor-destekli tarayıcıdan (Tor Browser, Brave vb.) doğrudan indirme yapılabilir.

```
Tor Browser → http://xxxxx.onion
```

Web arayüzü masaüstü uygulamasıyla aynı tasarıma sahip koyu tema HTML sayfasıdır. JavaScript ile dosya bilgisi alınır, şifre gerekiyorsa girilir ve dosya akış olarak tarayıcıya indirilir.

---

## Güvenlik Notları

- **Tor zorunludur.** Tüm trafik Tor ağı üzerinden akar; IP adresi gizlenir.
- **Keyless modda** şifreleme anahtarı URL fragment'ında taşınır ve sunucuya ulaşmaz.
- **Şifreli modda** anahtar Argon2id ile türetilir; salt dosya başlığına gömülür.
- **3 yanlış şifre** girişinden sonra link kalıcı olarak iptal edilir.
- **PANIC butonu** ctypes ile hafızadaki ham anahtar byte'larını sıfırlar ve `os._exit(0)` ile kapanır.
- **Geçici dosyalar** paylaşım durdurulduğunda silinir.
- **Gönderen** dosyayı doğrudan diskten sunar; şifrelenmiş stream yalnızca indirme sırasında oluşturulur.
- Uygulama kapandığında atexit hook ile Tor süreci sonlandırılır ve geçici dizin silinir.

> ⚠️ Bu uygulama yalnızca yasal amaçlarla kullanılmalıdır. Kullanıcı sorumluluğu kullanıcıya aittir.

---

## Yapılandırma

Ayarlar `~/.config/hazedrop/settings.json` dosyasında saklanır:

```json
{
  "download_dir": "~/Downloads",
  "default_once": true,
  "default_expire": "",
  "tor_bridges": [],
  "use_bridges": false,
  "history_enabled": true,
  "history_ttl_days": 7,
  "minimize_to_tray": true,
  "max_downloads": 1,
  "language": "tr",
  "window_geometry": ""
}
```

`window_geometry` stores the window's last position and size. Delete it and the
app opens centred on screen at its default size.

Transfer geçmişi `~/.local/share/hazedrop/history.db` SQLite veritabanında tutulur.

---

## Kaldırma

```bash
sudo pacman -Rns hazedrop
```

Kullanıcı verilerini de temizlemek için:
```bash
rm -rf ~/.config/hazedrop ~/.local/share/hazedrop
```

---

## Proje Yapısı

```
hazedrop/
├── assets/
│   └── logo.png
├── cli/
│   ├── app.py          # Click komutları (send, receive)
│   └── interactive.py  # Rich TUI
├── core/
│   ├── crypto.py       # ChaCha20, Argon2, SHA-256, URL
│   ├── history.py      # SQLite transfer geçmişi
│   ├── receiver.py     # aiohttp client, şifre çözme
│   ├── server.py       # aiohttp sunucu, /download /web-download
│   ├── session.py      # DropSession veri modeli
│   ├── settings.py     # JSON yapılandırma
│   ├── tor_manager.py  # stem ile Tor yönetimi
│   └── web_template.py # Tarayıcı arayüzü HTML
├── gui/
│   ├── main_window.py  # Ana pencere, navigasyon
│   ├── receive_panel.py
│   ├── send_panel.py
│   ├── settings_panel.py
│   ├── theme.py        # QSS stylesheet
│   ├── title_bar.py
│   ├── tray.py         # Sistem tepsisi
│   └── widgets.py      # SpinnerButton
└── secure/
    └── memory.py       # PANIC, ctypes key zeroing
```

---

## Lisans

GPL-3.0 — Berk Küçük
