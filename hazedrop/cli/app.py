import asyncio
import random
import sys

import click

from hazedrop.core.crypto import compute_file_hash, derive_key, generate_key, generate_salt
from hazedrop.core.duration import parse_duration
from hazedrop.core.session import DropSession
from hazedrop.core.tor_manager import TorManager
from hazedrop.core.server import TorDropServer
from hazedrop.secure.memory import register_sigquit_panic


def _parse_expire(value: str | None) -> int | None:
    """Shared with the GUI so both accept exactly the same syntax."""
    try:
        return parse_duration(value)
    except ValueError:
        raise click.BadParameter(
            "Use a value like 30s, 10m, 1h or 2d (max 30d).", param_hint="--expire"
        ) from None


@click.group(invoke_without_command=True)
@click.option("--cli", "use_cli", is_flag=True, help="Launch interactive TUI")
@click.pass_context
def main(ctx, use_cli):
    if ctx.invoked_subcommand is not None:
        return
    if use_cli:
        from hazedrop.cli.interactive import run_interactive
        run_interactive()
    else:
        from hazedrop.gui.main_window import launch_gui
        launch_gui()


@main.command()
@click.argument("filepath", type=click.Path(exists=True))
@click.option("-p", "--password", default=None, help="Encryption password")
@click.option("--once", is_flag=True, help="Self-destruct after one download")
@click.option("--expire", default=None,
              help="Expiry: 30s / 10m / 1h / 2d / 1h30m (bare number = seconds, max 30d)")
def send(filepath, password, once, expire):
    """Share a file over Tor."""
    asyncio.run(_send(filepath, password, once, expire))


async def _send(filepath: str, password: str | None, once: bool, expire: str | None):
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    expire_seconds = _parse_expire(expire)

    if password:
        salt = generate_salt()
        key = derive_key(password, salt)
    else:
        salt = None
        key = generate_key()

    import os
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

    console.print("[bold white]◈[/bold white]  Tor başlatılıyor...")
    console.print(f"  [dim]SHA-256: {file_hash[:16]}…[/dim]")

    def _progress(msg: str):
        console.print(f"   [dim]{msg}[/dim]")

    await tor.start(on_progress=_progress)
    console.print("[bold green]◈[/bold green]  Tor aktif ✓")

    server = TorDropServer(session, local_port)
    await server.start()

    console.print("[bold white]◈[/bold white]  Hidden service oluşturuluyor...")
    loop = asyncio.get_running_loop()
    onion = await loop.run_in_executor(None, tor.create_hidden_service, local_port)
    session.onion_address = onion

    url = session.share_url
    console.print(
        Panel(
            f"[bold white]{url}[/bold white]\n"
            + (f"Şifre: [bold]{password}[/bold] (alıcıya güvenli iletin)" if password else ""),
            title="◈  HAZEDROP LINK",
            border_style="white",
        )
    )
    console.print("  [dim]◌  İndirme bekleniyor...  [Ctrl+C iptal · Ctrl+\\ PANIC][/dim]")

    try:
        while not session.is_expired:
            await asyncio.sleep(1)
        console.print("  [green]✓[/green]  Tamamlandı.")
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n  [dim]İptal edildi.[/dim]")
    finally:
        session.zero_key()
        await server.stop()
        await tor.stop()


@main.command()
@click.argument("onion_url")
@click.option("-p", "--password", default=None, help="Decryption password")
@click.option("-o", "--output", default=".", type=click.Path(), help="Output directory")
def receive(onion_url, password, output):
    """Download a file from a HazeDrop .onion address."""
    asyncio.run(_receive(onion_url, password, output))


async def _receive(onion_url: str, password: str | None, output: str):
    from rich.console import Console
    from rich.progress import Progress, DownloadColumn, TransferSpeedColumn, TimeRemainingColumn, BarColumn

    console = Console()
    tor = TorManager()

    console.print("[bold white]◈[/bold white]  Tor başlatılıyor...")

    def _progress(msg: str):
        console.print(f"   [dim]{msg}[/dim]")

    await tor.start(on_progress=_progress)
    console.print("[bold green]◈[/bold green]  Tor aktif ✓")

    from hazedrop.core.receiver import download_and_decrypt

    try:
        with Progress(
            "[progress.description]{task.description}",
            BarColumn(),
            DownloadColumn(),
            TransferSpeedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("İndiriliyor...", total=None)

            def _on_progress(received: int, total: int):
                progress.update(task, completed=received, total=total or received)

            def _on_info(info: dict):
                progress.update(task, description=f"[white]{info.get('filename', '?')}[/white]")

            out = await download_and_decrypt(
                onion_address=onion_url,
                output_dir=output,
                socks_port=tor.socks_port,
                password=password,
                on_progress=_on_progress,
                on_info=_on_info,
            )

        console.print(f"  [green]✓[/green]  Kaydedildi: [bold]{out}[/bold]")
    except ConnectionError as e:
        console.print(f"  [red]✕[/red]  Bağlantı hatası: {e}")
        sys.exit(1)
    except TimeoutError as e:
        console.print(f"  [red]✕[/red]  Zaman aşımı: {e}")
        sys.exit(1)
    except PermissionError as e:
        console.print(f"  [red]✕[/red]  {e}")
        sys.exit(1)
    except FileNotFoundError as e:
        console.print(f"  [red]✕[/red]  {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"  [red]✕[/red]  Hata: {e}")
        sys.exit(1)
    finally:
        await tor.stop()
