import os
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
DEFAULT_MODEL = "cx/gpt-6-luna[1m]"
MAX_HISTORY_MESSAGES = 40
COLORS = {"cyan": "36", "green": "32", "yellow": "33", "red": "31", "dim": "2"}


def _paint(text: str, color: str) -> str:
    if not sys.stdout.isatty() or os.getenv("NO_COLOR") is not None:
        return text
    return f"\033[{COLORS[color]}m{text}\033[0m"


def _clear_line() -> str:
    if sys.stdout.isatty() and os.getenv("NO_COLOR") is None:
        return "\r\033[2K"
    return "\r      \r"


def create_client() -> tuple[OpenAI, str]:
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

    return OpenAI(api_key=api_key, base_url=base_url, timeout=180, max_retries=2), model

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
    spinner = threading.Thread(target=_animate_loading, args=(stop_spinner,), daemon=True)
    spinner.start()
    spinner_running = True

    def finish_loading() -> None:
        nonlocal spinner_running
        if spinner_running:
            stop_spinner.set()
            spinner.join()
            print(_clear_line() + _paint("AI", "green") + ": ", end="", flush=True)
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


def _animate_loading(stop: threading.Event) -> None:
    frames = "|/-\\"
    index = 0
    while not stop.is_set():
        frame = _paint(frames[index % len(frames)], "cyan")
        print(f"\r{_paint('AI', 'green')}: {frame}", end="", flush=True)
        index += 1
        stop.wait(0.12)


def print_help() -> None:
    commands = ("/help (bantuan)", "/reset (reset percakapan)", "/exit (keluar)")
    print("Perintah: " + ", ".join(_paint(command, "cyan") for command in commands))


def run_chat(
    input_fn: Callable[[str], str] = input,
    client: OpenAI | None = None,
    model: str | None = None,
) -> None:
    if client is None:
        client, model = create_client()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            question = input_fn("\n" + _paint(">", "cyan") + " ").strip()
            if not question:
                continue
            command = question.lower()
            if command == "/exit":
                break
            if command == "/help":
                print_help()
                continue
            if command == "/reset":
                messages[:] = [{"role": "system", "content": SYSTEM_PROMPT}]
                print(_paint("Riwayat direset.", "dim"))
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
