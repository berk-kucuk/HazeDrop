import asyncio
import os
import random

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm


console = Console()


def _parse_expire(value: str) -> int | None:
    if not value:
        return None
    value = value.strip().lower()
    if value.endswith("s"):
        return int(value[:-1])
    if value.endswith("m"):
        return int(value[:-1]) * 60
    if value.endswith("h"):
        return int(value[:-1]) * 3600
    try:
        return int(value)
    except ValueError:
        return None


def _header():
    console.print(
        Panel(
            "[bold white]◈ HAZEDROP[/bold white]  v1.3.0\n[dim]Anonymous · Encrypted[/dim]",
            border_style="white",
        )
    )


async def _send_flow():
    filepath = Prompt.ask("📁  Dosya")
    if not os.path.exists(filepath):
        console.print("[red]  Dosya bulunamadı.[/red]")
        return

    import getpass
    password = getpass.getpass("🔑  Şifre (boş = şifresiz): ") or None
    once = Confirm.ask("⚡  Tek indirme?", default=True)
    expire_str = Prompt.ask("⏱   Süre limiti [boş=∞]", default="")
    expire_seconds = _parse_expire(expire_str)

    from hazedrop.core.crypto import compute_file_hash, derive_key, generate_key, generate_salt
    from hazedrop.core.session import DropSession
    from hazedrop.core.tor_manager import TorManager
    from hazedrop.core.server import TorDropServer
    from hazedrop.secure.memory import register_sigquit_panic

    if password:
        salt = generate_salt()
        key = derive_key(password, salt)
    else:
        salt = None
        key = generate_key()

    file_hash = compute_file_hash(filepath)

    session = DropSession(
        filepath=filepath,
        filename=os.path.basename(filepath),
        filesize=os.path.getsize(filepath),
        password=password,
        once=once,
        expire_seconds=expire_seconds,
        salt=salt,
        key=key,
        file_hash=file_hash,
    )

    register_sigquit_panic(lambda: [session.key])

    tor = TorManager()
    local_port = random.randint(50000, 59999)

    console.print("\n[bold white]◈[/bold white]  Tor başlatılıyor...")

    def _progress(msg: str):
        if "Bootstrapped" in msg:
            pct = ""
            for part in msg.split():
                if part.endswith("%"):
                    pct = part
            console.print(f"   [dim]Bootstrapping {pct}[/dim]", end="\r")

    await tor.start(on_progress=_progress)
    console.print("[bold green]◈[/bold green]  Tor aktif ✓            ")
    console.print("[bold white]◈[/bold white]  Hidden service oluşturuluyor...")

    server = TorDropServer(session, local_port)
    await server.start()

    loop = asyncio.get_running_loop()
    onion = await loop.run_in_executor(None, tor.create_hidden_service, local_port)
    session.onion_address = onion

    size_mb = session.filesize / 1024 / 1024
    url = session.share_url
    expire_label = f"{expire_str}" if expire_str else "∞"
    once_label = "Tek indirme" if once else "Çoklu indirme"

    console.print(
        Panel(
            f"[bold white]{url}[/bold white]\n"
            + (f"Şifre: [bold]{password}[/bold] (alıcıya güvenli iletin)\n" if password else "")
            + f"\n📦 {session.filename} · {size_mb:.1f} MB\n"
            + f"⚡ {once_label} · {expire_label}",
            title="◈  HAZEDROP LINK",
            border_style="white",
        )
    )

    from rich.progress import Progress, BarColumn, DownloadColumn

    console.print("  [dim]◌  İndirme bekleniyor...  [Ctrl+C iptal · Ctrl+\\ PANIC][/dim]\n")

    download_started = asyncio.Event()
    download_done = asyncio.Event()

    def _on_start():
        console.print("  [bold white]↓[/bold white]  İndirme başladı...")
        download_started.set()

    def _on_complete():
        download_done.set()

    server._on_download_start = _on_start
    server._on_download_complete = _on_complete

    try:
        while not session.is_expired:
            await asyncio.sleep(0.5)
        if download_done.is_set():
            console.print("  [green]✓[/green]  Tamamlandı. Bağlantı kapatılıyor.")
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n  [dim]İptal edildi.[/dim]")
    finally:
        session.zero_key()
        await server.stop()
        await tor.stop()


async def _receive_flow():
    from hazedrop.core.receiver import download_and_decrypt
    from hazedrop.core.tor_manager import TorManager
    from rich.progress import Progress, BarColumn, DownloadColumn, TransferSpeedColumn

    import getpass
    onion_url = Prompt.ask("🔗  Onion adresi")
    password = getpass.getpass("🔑  Şifre (gerekiyorsa, yoksa boş bırak): ") or None
    output = Prompt.ask("📂  Kayıt klasörü", default=os.path.expanduser("~/Downloads"))

    tor = TorManager()
    console.print("\n[bold white]◈[/bold white]  Tor başlatılıyor...")

    def _progress(msg: str):
        if "Bootstrapped" in msg:
            for part in msg.split():
                if part.endswith("%"):
                    console.print(f"   [dim]Bootstrapping {part}[/dim]", end="\r")

    await tor.start(on_progress=_progress)
    console.print("[bold green]◈[/bold green]  Tor aktif ✓            ")

    try:
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
        ) as prog:
            task = prog.add_task("İndiriliyor...", total=None)

            def _on_progress(received, total):
                prog.update(task, completed=received, total=total or received)

            def _on_info(info):
                prog.update(task, description=f"[white]{info.get('filename', '?')}[/white]")

            out = await download_and_decrypt(
                onion_address=onion_url,
                output_dir=output,
                socks_port=tor.socks_port,
                password=password,
                on_progress=_on_progress,
                on_info=_on_info,
            )

        console.print(f"  [green]✓[/green]  Kaydedildi: [bold]{out}[/bold]")
    except Exception as e:
        console.print(f"  [red]✕[/red]  Hata: {e}")
    finally:
        await tor.stop()


def run_interactive():
    _header()

    while True:
        console.print("\n  [bold white][1][/bold white]  Dosya Gönder")
        console.print("  [bold white][2][/bold white]  Dosya Al")
        console.print("  [bold white][3][/bold white]  Çıkış\n")

        choice = Prompt.ask("▸ Seçim", choices=["1", "2", "3"], default="3")

        if choice == "3":
            break
        elif choice == "1":
            asyncio.run(_send_flow())
        elif choice == "2":
            asyncio.run(_receive_flow())
