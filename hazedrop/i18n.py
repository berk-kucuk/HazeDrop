from __future__ import annotations

_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # ── Nav ──────────────────────────────────────────────────────
        "nav_send": "SEND",
        "nav_recv": "RECV",
        "nav_conf": "CONF",

        # ── Title bar ────────────────────────────────────────────────
        "protocol_badge": "HAZE PROTOCOL",
        "protocol_connecting": "CONNECTING…",
        "protocol_error": "TOR ERROR",
        "panic": "PANIC",
        "panic_tip": "Wipe keys from memory and quit immediately  (Ctrl+\\)",
        "renew_circuit_tip": "Request a new Tor circuit",
        "minimize_tip": "Minimize",
        "maximize_tip": "Maximize",
        "restore_tip": "Restore",
        "close_tip": "Close",
        "tor_status_idle": "Tor is not running",
        "tor_status_starting": "Tor is starting…",
        "tor_status_active": "Connected to the Tor network",
        "tor_status_error": "Tor could not be started",

        # ── Send panel ───────────────────────────────────────────────
        "send_title": "SEND",
        "mode_file": "File",
        "mode_text": "Text",
        "select_file_title": "Select file",
        "select_folder_btn": "Select folder",
        "clear_btn": "Clear",
        "drop_hint_line1": "Drop a file here",
        "drop_hint_line2": "or click to browse",
        "text_placeholder": "Paste text, an API key, a password…",
        "security_title": "SECURITY",
        "pw_label": "PASSWORD",
        "pw_placeholder": "Used to derive the encryption key",
        "pw_show": "show",
        "pw_hide": "hide",
        "keyless_check": "Keyless — embed the key in the share URL",
        "keyless_help": "Anyone with the link can download. Turn this off to "
                        "require a password instead.",
        "options_title": "OPTIONS",
        "limit_check": "Limit downloads",
        "expire_check": "Expire after",
        "expire_placeholder": "10m  /  1h  /  30s",
        "expire_invalid": "Use a value like 30s, 10m, 1h or 2d (max 30d).",
        "share_btn": "SHARE",
        "share_link_title": "SHARE LINK",
        "copy_link_btn": "Copy link",
        "copied_btn": "Copied",
        "qr_btn": "QR code",
        "stop_btn": "STOP SHARING",
        "status_waiting": "Waiting for download…",
        "status_downloading": "Downloading",
        "status_complete": "Transfer complete",
        "status_error_prefix": "Error: {}",
        "text_empty": "Enter some text to share.",
        "file_missing": "Select a file to share.",
        "zip_failed": "Could not archive the folder: {}",
        "spin_starting_tor": "STARTING TOR",
        "spin_bootstrapping": "BOOTSTRAPPING {}",
        "spin_publishing": "PUBLISHING",
        "spin_connecting": "CONNECTING",
        "spin_downloading": "DOWNLOADING",
        "notify_dl_started": "Download started: {}",
        "notify_dl_complete": "Transfer complete: {}",
        "footer_hint_pick": "Choose a file or folder to get started.",
        "footer_hint_text": "Type or paste the text you want to share.",
        "footer_hint_ready": "Ready to publish over Tor.",
        "footer_hint_starting": "Starting Tor…",
        "footer_hint_live": "Link is live — keep HazeDrop open until it is downloaded.",
        "footer_hint_failed": "Something went wrong. See the details above.",

        # ── Receive panel ─────────────────────────────────────────────
        "recv_title": "RECEIVE",
        "onion_label": "SHARE LINK",
        "onion_placeholder": "http://xxxxxxxx.onion#key",
        "onion_help": "Paste the full link you were given, including anything "
                      "after the # sign.",
        "onion_invalid": "That does not look like a .onion link.",
        "onion_required": "Paste a share link first.",
        "pw_required_hint": "Required if the sender set one",
        "save_to_label": "SAVE TO",
        "browse_btn": "Browse",
        "download_btn": "DOWNLOAD",
        "open_folder_btn": "Open folder",
        "open_folder_failed": "Could not open the folder: {}",
        "output_dir_failed": "Cannot write to that folder: {}",
        "status_starting_tor": "Starting Tor…",
        "status_bootstrapping": "Bootstrapping {}",
        "status_connecting_recv": "Connecting…",
        "tor_failed": "Tor failed: {}",
        "saved_as": "Saved  {}",
        "notify_dl_complete_recv": "Download complete: {}",
        "footer_hint_url": "Paste a share link to begin.",
        "footer_hint_ready_dl": "Ready to download over Tor.",
        "footer_hint_downloading": "Downloading — keep HazeDrop open.",
        "footer_hint_saved": "Done. The file is in your download folder.",

        # ── Settings panel ────────────────────────────────────────────
        "settings_title": "SETTINGS",
        "general_section": "GENERAL",
        "dl_dir_label": "Download folder",
        "minimize_tray_check": "Minimize to tray on close",
        "transfer_section": "TRANSFER DEFAULTS",
        "max_dl_label": "Max downloads per link",
        "max_dl_help": "0 means unlimited. The link stops working once the "
                       "limit is reached.",
        "unlimited": "∞",
        "default_expire_label": "Default expiry",
        "expire_hint": "10m / 1h / 30s",
        "history_section": "HISTORY",
        "history_check": "Keep a transfer history",
        "history_ttl_label": "Keep entries for (days)",
        "clear_history_btn": "Clear history",
        "history_cleared": "History cleared.",
        "bridges_section": "TOR BRIDGES",
        "use_bridges_check": "Use bridges",
        "bridges_help": "Only needed where access to the Tor network is blocked.",
        "bridge_lines_label": "Bridge lines (one per line)",
        "bridge_placeholder": "obfs4 1.2.3.4:1234 FINGERPRINT cert=… iat-mode=0",
        "language_section": "LANGUAGE",
        "language_label": "Interface language",
        "language_help": "Applied immediately — no restart needed.",
        "save_btn": "SAVE",
        "settings_saved": "Settings saved.",

        # ── Tray ──────────────────────────────────────────────────────
        "tray_show": "Show HazeDrop",
        "tray_hide": "Hide",
        "tray_quit": "Quit",
    },

    "tr": {
        # ── Nav ──────────────────────────────────────────────────────
        "nav_send": "GÖNDER",
        "nav_recv": "AL",
        "nav_conf": "AYAR",

        # ── Title bar ────────────────────────────────────────────────
        "protocol_badge": "HAZE PROTOKOL",
        "protocol_connecting": "BAĞLANIYOR…",
        "protocol_error": "TOR HATASI",
        "panic": "PANİK",
        "panic_tip": "Anahtarları bellekten sil ve hemen çık  (Ctrl+\\)",
        "renew_circuit_tip": "Yeni bir Tor devresi iste",
        "minimize_tip": "Küçült",
        "maximize_tip": "Büyült",
        "restore_tip": "Eski boyuta döndür",
        "close_tip": "Kapat",
        "tor_status_idle": "Tor çalışmıyor",
        "tor_status_starting": "Tor başlatılıyor…",
        "tor_status_active": "Tor ağına bağlanıldı",
        "tor_status_error": "Tor başlatılamadı",

        # ── Send panel ───────────────────────────────────────────────
        "send_title": "GÖNDER",
        "mode_file": "Dosya",
        "mode_text": "Metin",
        "select_file_title": "Dosya seç",
        "select_folder_btn": "Klasör seç",
        "clear_btn": "Temizle",
        "drop_hint_line1": "Dosyayı buraya sürükle",
        "drop_hint_line2": "veya seçmek için tıkla",
        "text_placeholder": "Metin, API anahtarı ya da parola yapıştır…",
        "security_title": "GÜVENLİK",
        "pw_label": "PAROLA",
        "pw_placeholder": "Şifreleme anahtarı bundan türetilir",
        "pw_show": "göster",
        "pw_hide": "gizle",
        "keyless_check": "Parolasız — anahtar bağlantıya gömülür",
        "keyless_help": "Bağlantıya sahip olan herkes indirebilir. Parola "
                        "zorunlu kılmak için bu seçeneği kapat.",
        "options_title": "SEÇENEKLER",
        "limit_check": "İndirme limiti",
        "expire_check": "Şu süre sonra dolsun",
        "expire_placeholder": "10m  /  1h  /  30s",
        "expire_invalid": "30s, 10m, 1h ya da 2d gibi bir değer gir (en fazla 30d).",
        "share_btn": "PAYLAŞ",
        "share_link_title": "PAYLAŞIM BAĞLANTISI",
        "copy_link_btn": "Bağlantıyı kopyala",
        "copied_btn": "Kopyalandı",
        "qr_btn": "QR kod",
        "stop_btn": "PAYLAŞIMI DURDUR",
        "status_waiting": "İndirme bekleniyor…",
        "status_downloading": "İndiriliyor",
        "status_complete": "Transfer tamamlandı",
        "status_error_prefix": "Hata: {}",
        "text_empty": "Paylaşmak için bir metin gir.",
        "file_missing": "Paylaşmak için bir dosya seç.",
        "zip_failed": "Klasör arşivlenemedi: {}",
        "spin_starting_tor": "TOR BAŞLATILIYOR",
        "spin_bootstrapping": "HAZIRLANIYOR {}",
        "spin_publishing": "YAYINLANIYOR",
        "spin_connecting": "BAĞLANIYOR",
        "spin_downloading": "İNDİRİLİYOR",
        "notify_dl_started": "İndirme başladı: {}",
        "notify_dl_complete": "Transfer tamamlandı: {}",
        "footer_hint_pick": "Başlamak için bir dosya ya da klasör seç.",
        "footer_hint_text": "Paylaşmak istediğin metni yaz ya da yapıştır.",
        "footer_hint_ready": "Tor üzerinden yayınlamaya hazır.",
        "footer_hint_starting": "Tor başlatılıyor…",
        "footer_hint_live": "Bağlantı yayında — indirilene kadar HazeDrop'u açık tut.",
        "footer_hint_failed": "Bir şeyler ters gitti. Ayrıntılar yukarıda.",

        # ── Receive panel ─────────────────────────────────────────────
        "recv_title": "AL",
        "onion_label": "PAYLAŞIM BAĞLANTISI",
        "onion_placeholder": "http://xxxxxxxx.onion#anahtar",
        "onion_help": "Sana verilen bağlantının tamamını, # işaretinden "
                      "sonrasıyla birlikte yapıştır.",
        "onion_invalid": "Bu bir .onion bağlantısına benzemiyor.",
        "onion_required": "Önce bir paylaşım bağlantısı yapıştır.",
        "pw_required_hint": "Gönderen parola belirlediyse gerekli",
        "save_to_label": "KAYIT YERİ",
        "browse_btn": "Gözat",
        "download_btn": "İNDİR",
        "open_folder_btn": "Klasörü aç",
        "open_folder_failed": "Klasör açılamadı: {}",
        "output_dir_failed": "Bu klasöre yazılamıyor: {}",
        "status_starting_tor": "Tor başlatılıyor…",
        "status_bootstrapping": "Hazırlanıyor {}",
        "status_connecting_recv": "Bağlanıyor…",
        "tor_failed": "Tor başlatılamadı: {}",
        "saved_as": "Kaydedildi  {}",
        "notify_dl_complete_recv": "İndirme tamamlandı: {}",
        "footer_hint_url": "Başlamak için bir paylaşım bağlantısı yapıştır.",
        "footer_hint_ready_dl": "Tor üzerinden indirmeye hazır.",
        "footer_hint_downloading": "İndiriliyor — HazeDrop'u açık tut.",
        "footer_hint_saved": "Bitti. Dosya indirme klasöründe.",

        # ── Settings panel ────────────────────────────────────────────
        "settings_title": "AYARLAR",
        "general_section": "GENEL",
        "dl_dir_label": "İndirme klasörü",
        "minimize_tray_check": "Kapatınca sistem tepsisine küçült",
        "transfer_section": "VARSAYILAN TRANSFER AYARLARI",
        "max_dl_label": "Bağlantı başına en fazla indirme",
        "max_dl_help": "0 sınırsız demektir. Limite ulaşınca bağlantı çalışmayı bırakır.",
        "unlimited": "∞",
        "default_expire_label": "Varsayılan süre sınırı",
        "expire_hint": "10m / 1h / 30s",
        "history_section": "GEÇMİŞ",
        "history_check": "Transfer geçmişini tut",
        "history_ttl_label": "Kayıtları saklama süresi (gün)",
        "clear_history_btn": "Geçmişi temizle",
        "history_cleared": "Geçmiş temizlendi.",
        "bridges_section": "TOR KÖPRÜLERİ",
        "use_bridges_check": "Köprü kullan",
        "bridges_help": "Yalnızca Tor ağına erişimin engellendiği yerlerde gerekir.",
        "bridge_lines_label": "Köprü satırları (her satıra bir tane)",
        "bridge_placeholder": "obfs4 1.2.3.4:1234 PARMAKİZİ cert=… iat-mode=0",
        "language_section": "DİL",
        "language_label": "Arayüz dili",
        "language_help": "Anında uygulanır — yeniden başlatmaya gerek yok.",
        "save_btn": "KAYDET",
        "settings_saved": "Ayarlar kaydedildi.",

        # ── Tray ──────────────────────────────────────────────────────
        "tray_show": "HazeDrop'u göster",
        "tray_hide": "Gizle",
        "tray_quit": "Çık",
    },
}

_LANGUAGE: str = "en"

LANGUAGE_OPTIONS: dict[str, str] = {
    "en": "English",
    "tr": "Türkçe",
}


def set_language(lang: str) -> None:
    global _LANGUAGE
    if lang in _STRINGS:
        _LANGUAGE = lang


def get_language() -> str:
    return _LANGUAGE


def t(key: str, *args) -> str:
    """Return the translated string for ``key``, with optional format args."""
    text = (
        _STRINGS.get(_LANGUAGE, _STRINGS["en"]).get(key)
        or _STRINGS["en"].get(key)
        or key
    )
    if not args:
        return text
    try:
        return text.format(*args)
    except (IndexError, KeyError):
        # A translator dropping the {} placeholder should not crash the UI.
        return text
