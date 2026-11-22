import os
import shutil
import sys
import threading
from collections.abc import Callable
from pathlib import Path
from typing import cast

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)
from openai.types.chat import ChatCompletionMessageParam

SYSTEM_PROMPT = """Kamu adalah AI assistant pribadi yang cerdas, informatif, kritis, dan komunikatif.

Jawablah pertanyaan pengguna dengan jelas dan terstruktur. Gunakan bahasa yang sesuai dengan bahasa pengguna. Jangan mengarang informasi apabila tidak mengetahuinya. Hindari Markdown untuk pemformatan: jangan gunakan tanda bintang, termasuk **teks tebal** atau *teks miring*. Gunakan teks biasa dan susunan baris sederhana."""
DEFAULT_BASE_URL = "http://localhost:20128/v1"
DEFAULT_MODEL = "9router-gptcontext1m"
MAX_HISTORY_MESSAGES = 40
COLORS = {"cyan": "36", "green": "32", "yellow": "33", "red": "31", "dim": "2", "bold": "1", "magenta": "35"}

def _paint(text: str, color: str) -> str:
    if not sys.stdout.isatty() or os.getenv("NO_COLOR") is not None:
        return text
    return f"\033[{COLORS[color]}m{text}\033[0m"

def _clear_line(width: int) -> str:
    if sys.stdout.isatty() and os.getenv("NO_COLOR") is None:
        return "\r\033[2K"
    return "\r" + " " * width + "\r"


def _ai_label(model: str) -> str:
    return f"AI {model}"


def _init_terminal() -> None:
    # ponytail: aktifkan VT100 escape codes di Windows console; upgrade ke curses jika butuh TUI penuh
    if os.name == "nt":
        os.system("")


def _print_logo() -> None:
    _init_terminal()
    width = shutil.get_terminal_size((80, 20)).columns
    pad = " " * max((width - 56) // 2, 0)

    rows = [
        pad + _paint("╭── ", "cyan") + _paint("PERSONAL AI", "bold") + _paint(" ───────────────────────────────────────╮", "cyan"),
        pad + _paint("│", "cyan") + " " * 54 + _paint("│", "cyan"),
        pad + _paint("│", "cyan") + "      " + _paint("___    ____", "cyan") + "                                     " + _paint("│", "cyan"),
        pad + _paint("│", "cyan") + "     " + _paint("/   |  /  _/", "cyan") + "    " + _paint("Intelligence Terminal Console", "bold") + "    " + _paint("│", "cyan"),
        pad + _paint("│", "cyan") + "    " + _paint("/ /| |  / /  ", "cyan") + "    " + _paint("Engine  :", "dim") + " 9Router Multi-Model    " + _paint("│", "cyan"),
        pad + _paint("│", "cyan") + "   " + _paint("/ ___ |_/ /   ", "cyan") + "    " + _paint("Status  :", "dim") + " " + _paint("Online & Ready", "green") + "         " + _paint("│", "cyan"),
        pad + _paint("│", "cyan") + "  " + _paint("/_/  |_/___/   ", "cyan") + "    " + _paint("Panduan :", "dim") + " Ketik " + _paint("/help", "cyan") + "            " + _paint("│", "cyan"),
        pad + _paint("│", "cyan") + " " * 54 + _paint("│", "cyan"),
        pad + _paint("╰──────────────────────────────────────────────────────╯", "cyan"),
    ]
    print()
    for row in rows:
        print(row)
    print()


def create_client() -> tuple[OpenAI, str, str]:
    if getattr(sys, "frozen", False):
        load_dotenv(Path(sys.executable).resolve().parent / ".env")
    else:
        load_dotenv()
    api_key = os.getenv("ROUTER_API_KEY", "").strip()
    base_url = os.getenv("ROUTER_BASE_URL", DEFAULT_BASE_URL).strip()
    model = os.getenv("ROUTER_MODEL", DEFAULT_MODEL).strip()

    if not api_key:
        raise ValueError("ROUTER_API_KEY belum diisi di file .env")
    if not base_url or not model:
        raise ValueError("ROUTER_BASE_URL dan ROUTER_MODEL tidak boleh kosong.")

    return OpenAI(api_key=api_key, base_url=base_url, timeout=180, max_retries=2), model, api_key

def get_combos(client: OpenAI) -> list[str]:
    response = client.models.list()
    return sorted({item.id for item in response.data if item.id.startswith("9router-")})

def _interactive_select(options: list[str], default_idx: int) -> int:
    import msvcrt
    idx = default_idx
    total = len(options)
    width = shutil.get_terminal_size((80, 20)).columns
    pad = " " * max((width - 56) // 2, 0)

    def draw(first: bool = False) -> None:
        if not first:
            print(f"\033[{total}A", end="")
        for i, opt in enumerate(options):
            marker = " ★" if i == default_idx else ""
            if i == idx:
                line = f"{pad} ❯ [{i+1}] {opt}{marker}"
                print("\033[2K" + _paint(line, "cyan"))
            else:
                line = f"{pad}   [{i+1}] {opt}{marker}"
                print("\033[2K" + _paint(line, "dim" if i != default_idx else "green"))
        sys.stdout.flush()

    print(pad + _paint("PILIH COMBO", "cyan") + _paint(" (Gunakan ↑/↓ lalu Enter, atau ketik nomor):", "dim"))
    draw(first=True)

    buf = ""
    while True:
        key = msvcrt.getwch()
        if key in ("\r", "\n"):
            if buf.isdigit() and 1 <= int(buf) <= total:
                return int(buf) - 1
            return idx
        elif key in ("\x00", "\xe0"):
            arrow = msvcrt.getwch()
            buf = ""
            if arrow == "H":
                idx = (idx - 1) % total
                draw()
            elif arrow == "P":
                idx = (idx + 1) % total
                draw()
        elif key.isdigit():
            buf += key
            val = int(buf)
            if 1 <= val <= total:
                idx = val - 1
                draw()
        elif key in ("\x08",):
            buf = buf[:-1]
        elif key in ("\x03", "\x1b"):
            print()
            raise KeyboardInterrupt


def choose_combo(
    combos: list[str],
    default_model: str,
    input_fn: Callable[[str], str] = input,
) -> str:
    options = list(combos)
    if not options:
        choice = input_fn(_paint(f"Combo [Enter={default_model}] > ", "cyan")).strip()
        return choice or default_model
    if default_model not in options:
        options.insert(0, default_model)

    default_idx = options.index(default_model)

    # ponytail: arrow navigation via msvcrt jika terminal interaktif; fallback ke input biasa di testing/piping
    if input_fn is input and sys.stdin.isatty() and os.name == "nt":
        try:
            chosen = _interactive_select(options, default_idx)
            print()
            return options[chosen]
        except (ImportError, OSError):
            pass

    print("\n" + _paint("PILIH COMBO", "cyan"))
    for index, combo in enumerate(options, 1):
        marker = _paint(" *", "green") if combo == default_model else ""
        print(f"  {_paint(f'[{index:>2}]', 'dim')}  {combo}{marker}")

    while True:
        try:
            choice = input_fn(_paint("Pilihan [Enter=default] > ", "cyan")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            raise
        if not choice:
            return default_model
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice) - 1]
        print(_paint("Pilihan tidak valid. Masukkan nomor combo atau tekan Enter.", "yellow"))

def trim_history(messages: list[dict[str, str]], max_messages: int = MAX_HISTORY_MESSAGES) -> None:
    """Keep system prompt and newest complete user/assistant turns."""
    if max_messages < 2:
        raise ValueError("max_messages harus minimal 2")

    system_message = messages[0]
    history = messages[1:]
    if len(history) <= max_messages:
        return

    history = history[-max_messages:]
    if history and history[0]["role"] == "assistant":
        history.pop(0)
    messages[:] = [system_message, *history]

def chat(question: str, client: OpenAI, model: str, messages: list[dict[str, str]]) -> None:
    messages.append({"role": "user", "content": question})
    answer: list[str] = []
    stop_spinner = threading.Event()
    label = _ai_label(model)
    spinner = threading.Thread(target=_animate_loading, args=(stop_spinner, model), daemon=True)
    spinner.start()
    spinner_running = True

    def finish_loading() -> None:
        nonlocal spinner_running
        if spinner_running:
            stop_spinner.set()
            spinner.join()
            print(_clear_line(len(label) + 3) + _paint(label, "green") + ": ", end="", flush=True)
            spinner_running = False

    try:
        stream = client.chat.completions.create(
                    model=model,
                    messages=cast(list[ChatCompletionMessageParam], messages),
                    stream=True,
                )
        for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            if isinstance(content, str):
                finish_loading()
                print(content, end="", flush=True)
                answer.append(content)

        if not answer:
            finish_loading()
            messages.pop()
            print("\nModel tidak mengirim jawaban. Coba lagi.")
            return

        print("\n")
        messages.append({"role": "assistant", "content": "".join(answer)})
        trim_history(messages)
    except AuthenticationError:
        finish_loading()
        messages.pop()
        print("\n" + _paint("API key tidak valid. Periksa ROUTER_API_KEY di .env.", "red"))
    except APIConnectionError:
        finish_loading()
        messages.pop()
        print("\n" + _paint(f"Tidak dapat terhubung ke {client.base_url}.", "red"))
        print(_paint("Periksa alamat layanan dan pastikan provider sedang berjalan.", "dim"))
    except RateLimitError:
        finish_loading()
        messages.pop()
        print("\n" + _paint("Rate limit tercapai. Periksa kuota atau limit API.", "yellow"))
    except APIStatusError as error:
        finish_loading()
        messages.pop()
        print("\n" + _paint(f"API Error: HTTP {error.status_code}", "red"))
        print(error.message)
    except OpenAIError as error:
        finish_loading()
        messages.pop()
        print("\n" + _paint(f"OpenAI SDK Error: {error}", "red"))
    except (OSError, ValueError, TypeError) as error:
        finish_loading()
        messages.pop()
        print("\n" + _paint(f"Unexpected Error: {error}", "red"))
    finally:
        finish_loading()

def _animate_loading(stop: threading.Event, model: str) -> None:
    frames = "|/-\\"
    index = 0
    while not stop.is_set():
        frame = _paint(frames[index % len(frames)], "cyan")
        print(f"\r{_paint(_ai_label(model), 'green')}: {frame}", end="", flush=True)
        index += 1
        stop.wait(0.12)


COMMANDS_HELP = [
    ("/help", "Panduan daftar perintah ini"),
    ("/model", "Ganti model AI via menu interaktif"),
    ("/status", "Status model aktif & statistik chat"),
    ("/clear", "Bersihkan tampilan layar terminal"),
    ("/save [file]", "Simpan riwayat chat ke file teks"),
    ("/reset", "Reset percakapan saat ini"),
    ("/exit", "Keluar dari aplikasi"),
]


def print_help() -> None:
    width = shutil.get_terminal_size((80, 20)).columns
    pad = " " * max((width - 56) // 2, 0)
    target_inner = 54
    print()
    print(pad + _paint("╭─ PANDUAN PERINTAH ───────────────────────────────────╮", "cyan"))
    for cmd, desc in COMMANDS_HELP:
        visible_len = len(f"  {cmd:<13} {desc}")
        trailing = " " * max(target_inner - visible_len, 0)
        row = (
            pad
            + _paint("│", "cyan")
            + "  "
            + _paint(f"{cmd:<13}", "green")
            + " "
            + desc
            + trailing
            + _paint("│", "cyan")
        )
        print(row)
    print(pad + _paint("╰──────────────────────────────────────────────────────╯", "cyan"))


def save_history(messages: list[dict[str, str]], filename: str = "chat_export.txt") -> None:
    try:
        with open(filename, "w", encoding="utf-8") as file:
            for msg in messages:
                role = msg["role"].upper()
                if role == "SYSTEM":
                    continue
                file.write(f"[{role}]\n{msg['content']}\n\n")
        print(_paint(f"✔ Riwayat percakapan disimpan ke '{filename}'.", "green"))
    except (OSError, ValueError, TypeError) as error:
        print(_paint(f"✘ Gagal menyimpan file: {error}", "red"))


def print_status(model: str, base_url: str, message_count: int) -> None:
    turns = (message_count - 1) // 2
    width = shutil.get_terminal_size((80, 20)).columns
    pad = " " * max((width - 56) // 2, 0)
    target_inner = 54
    status_data = [
        ("Model Aktif", model),
        ("Endpoint", base_url),
        ("Percakapan", f"{turns} turn ({message_count - 1} pesan)"),
    ]
    print()
    print(pad + _paint("╭─ STATUS PERSONAL AI ─────────────────────────────────╮", "cyan"))
    for label, val in status_data:
        visible_len = len(f"  {label:<15}: {val}")
        trailing = " " * max(target_inner - visible_len, 0)
        row = (
            pad
            + _paint("│", "cyan")
            + "  "
            + _paint(f"{label:<15}", "green")
            + ": "
            + val
            + trailing
            + _paint("│", "cyan")
        )
        print(row)
    print(pad + _paint("╰──────────────────────────────────────────────────────╯", "cyan"))


def run_chat(
    input_fn: Callable[[str], str] = input,
    client: OpenAI | None = None,
    model: str | None = None,
) -> None:
    if client is None:
        client, model, _ = create_client()

    _print_logo()

    try:
        combos = get_combos(client)
    except OpenAIError as error:
        print(_paint(f"Daftar combo tidak tersedia: {error}", "yellow"))
        combos = []
    except (OSError, ValueError, TypeError) as error:
        print(_paint(f"Daftar combo tidak tersedia: {error}", "yellow"))
        combos = []

    try:
        model = choose_combo(combos, model or DEFAULT_MODEL, input_fn)
    except (EOFError, KeyboardInterrupt):
        return
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    width = shutil.get_terminal_size((80, 20)).columns
    pad = " " * max((width - 56) // 2, 0)
    print()
    print(pad + " Model aktif: " + _paint(model, "cyan"))
    print(pad + _paint("─" * 56, "dim"))

    while True:
        try:
            prompt = f"\n{_paint(f'[{model}]', 'cyan')} {_paint('❯', 'green')} "
            question = input_fn(prompt).strip()
            if not question:
                continue
            cmd_parts = question.split(maxsplit=1)
            command = cmd_parts[0].lower()

            if command in ("/exit", "/quit"):
                print(_paint("Sampai jumpa!", "dim"))
                break
            if command == "/help":
                print_help()
                continue
            if command == "/reset":
                messages[:] = [{"role": "system", "content": SYSTEM_PROMPT}]
                print(_paint("✔ Riwayat percakapan direset.", "dim"))
                continue
            if command in ("/clear", "/cls"):
                os.system("cls" if os.name == "nt" else "clear")
                _print_logo()
                print(pad + _paint("✔", "green") + " Model aktif: " + _paint(model, "cyan"))
                print(pad + _paint("─" * 56, "dim"))
                continue
            if command in ("/model", "/combo"):
                try:
                    model = choose_combo(combos, model or DEFAULT_MODEL, input_fn)
                    print()
                    print(pad + _paint("✔", "green") + " Model aktif: " + _paint(model, "cyan"))
                    print(pad + _paint("─" * 56, "dim"))
                except (EOFError, KeyboardInterrupt):
                    pass
                continue
            if command in ("/status", "/info"):
                print_status(model or DEFAULT_MODEL, str(client.base_url), len(messages))
                continue
            if command == "/save":
                filename = cmd_parts[1].strip() if len(cmd_parts) > 1 else "chat_export.txt"
                save_history(messages, filename)
                continue

            chat(question, client, model or DEFAULT_MODEL, messages)
        except KeyboardInterrupt:
            print()
            break
        except EOFError:
            print()
            break


def main() -> int:
    try:
        run_chat()
    except ValueError as error:
        print(_paint(f"Error: {error}", "red"))
        print("Salin .env.example menjadi .env, lalu isi konfigurasi.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
