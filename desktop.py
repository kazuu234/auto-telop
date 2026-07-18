"""Native desktop app: PyWebView window wrapping the Flask editor.

Double-clicking the built app runs this. It starts the Flask server on a
free localhost port in a background thread, then opens a native window
pointing at it. The user never touches a terminal or a browser.
"""

import os
import socket
import subprocess
import sys
import threading
import time
import urllib.request

import webview  # pywebview

from app import app


def _free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _start_server(port):
    # Disable the reloader/debug so it runs cleanly inside a thread.
    app.run(host="127.0.0.1", port=port, debug=False,
            use_reloader=False, threaded=True)


def _wait_until_up(port, timeout=15):
    url = f"http://127.0.0.1:{port}/api/version"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except Exception:
            time.sleep(0.2)
    return False


class Api:
    """JavaScript-callable bridge for native dialogs."""

    def __init__(self):
        self._window = None

    def set_window(self, window):
        self._window = window

    def pick_videos(self):
        """Open a native multi-select file dialog. Returns list of paths."""
        file_types = ("動画ファイル (*.mp4;*.mov;*.m4v;*.avi;*.mkv)", "すべて (*.*)")
        result = self._window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=True, file_types=file_types
        )
        if not result:
            return []
        return list(result)

    def pick_save_path(self, default_name="output.fcpxml", directory=None):
        """Open a native save dialog. Returns chosen path, or '' if cancelled.

        The file-type filter is inferred from the default_name extension so the
        dialog matches the chosen export format (fcpxml / srt / vtt).
        directory: optional initial directory (e.g. the last-used save dir).
        """
        from embed_te import FORMATS
        ext = os.path.splitext(default_name)[1].lower().lstrip(".")
        # ext(拡張子)フィールドで照合する。FORMATSのキー(フォーマットID)とext
        # がたまたま一致しているだけなので、キー直引きにしない。
        label = next((v["dialog_label"] for v in FORMATS.values()
                     if v["ext"] == f".{ext}"), "すべて (*.*)")
        file_types = (label, "すべて (*.*)")
        result = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            directory=directory or "",
            save_filename=default_name,
            file_types=file_types,
        )
        if not result:
            return ""
        return result if isinstance(result, str) else result[0]

    def reveal_path(self, path):
        """Reveal a file in Finder / Explorer."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", "-R", path], check=False)
            elif sys.platform.startswith("win"):
                subprocess.run(["explorer", "/select,", os.path.normpath(path)], check=False)
            else:
                subprocess.run(["xdg-open", os.path.dirname(path)], check=False)
        except Exception:
            pass
        return True


def main():
    port = _free_port()
    server = threading.Thread(target=_start_server, args=(port,), daemon=True)
    server.start()

    if not _wait_until_up(port):
        print("Server failed to start", file=sys.stderr)
        sys.exit(1)

    api = Api()
    window = webview.create_window(
        "Auto Telop",
        f"http://127.0.0.1:{port}/",
        js_api=api,
        width=980,
        height=760,
        min_size=(720, 560),
    )
    api.set_window(window)
    webview.start()


if __name__ == "__main__":
    # PyInstaller化したアプリでは必須。Whisper(torch)が処理中に生成する
    # ワーカープロセスがアプリ本体を再実行してしまい、文字起こし中に
    # 2つ目のGUIウインドウが立ち上がる。freeze_support()がそれを横取りする。
    import multiprocessing
    multiprocessing.freeze_support()
    main()
