import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from webp_to_webm import convert, find_ffmpeg


def folder_jobs(source):
    return [(path, path.relative_to(source)) for path in sorted(source.rglob("*"))
            if path.suffix.lower() == ".webp" and path.is_file()]


def run_batch(jobs, destination, ffmpeg, events):
    errors = 0
    for number, (source, relative) in enumerate(jobs, 1):
        target = (destination / relative).with_suffix(".webm")
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            size = convert(source, target, ffmpeg)
            line = f"✓ {relative} → {size:,} байт"
        except (OSError, ValueError, subprocess.CalledProcessError) as error:
            errors += 1
            line = f"✗ {relative} — {error}"
        events.put((number, line))
    events.put((None, f"Готово: {len(jobs) - errors} из {len(jobs)}. Ошибок: {errors}."))


def main():
    root = tk.Tk()
    root.title("LoopForge · Видеостикеры Telegram")
    logo_path = Path(__file__).with_name("loopforge.png")
    if logo_path.is_file():
        icon = tk.PhotoImage(file=logo_path)
        root.iconphoto(True, icon)
    root.geometry("690x420")
    root.minsize(470, 300)
    panel = ttk.Frame(root, padding=16)
    panel.pack(fill="both", expand=True)

    toolbar = ttk.Frame(panel)
    toolbar.pack(fill="x")
    ttk.Label(panel, text="VP9 · 30 FPS · до 3 секунд · до 256 КБ").pack(
        anchor="w", pady=(12, 6)
    )
    status = tk.StringVar(value="Выберите файлы или папку с WebP.")
    ttk.Label(panel, textvariable=status).pack(anchor="w", pady=(0, 6))
    progress = ttk.Progressbar(panel, mode="determinate")
    progress.pack(fill="x", pady=(0, 10))
    log_frame = ttk.Frame(panel)
    log_frame.pack(fill="both", expand=True)
    log = tk.Text(log_frame, height=10, wrap="word", state="disabled")
    scroll = ttk.Scrollbar(log_frame, command=log.yview)
    log.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")
    log.pack(side="left", expand=True, fill="both")
    events = queue.Queue()

    def poll():
        while True:
            try:
                number, line = events.get_nowait()
            except queue.Empty:
                root.after(100, poll)
                return
            if number is None:
                status.set(line)
                for button in buttons:
                    button.state(["!disabled"])
                return
            progress["value"] = number
            status.set(f"Обработано {number} из {int(progress['maximum'])}")
            log.configure(state="normal")
            log.insert("end", line + "\n")
            log.see("end")
            log.configure(state="disabled")

    def start(jobs):
        if not jobs:
            messagebox.showinfo("WebP → WebM", "В выбранной папке нет файлов WebP.")
            return
        try:
            ffmpeg = find_ffmpeg()
        except RuntimeError as error:
            messagebox.showerror("FFmpeg", str(error), parent=root)
            return
        output = filedialog.askdirectory(title="Куда сохранить файлы WebM?")
        if not output:
            return
        for button in buttons:
            button.state(["disabled"])
        log.configure(state="normal")
        log.delete("1.0", "end")
        log.configure(state="disabled")
        progress.configure(maximum=len(jobs), value=0)
        status.set(f"Обработано 0 из {len(jobs)}")
        threading.Thread(
            target=run_batch, args=(jobs, Path(output), ffmpeg, events), daemon=True
        ).start()
        root.after(100, poll)

    def select_files():
        paths = filedialog.askopenfilenames(
            title="Выберите файлы WebP", filetypes=[("WebP", "*.webp *.WEBP")]
        )
        if paths:
            start([(Path(path), Path(path).name) for path in paths])

    def select_folder():
        path = filedialog.askdirectory(title="Выберите папку с WebP")
        if path:
            start(folder_jobs(Path(path)))

    buttons = [
        ttk.Button(toolbar, text="Выбрать файлы…", command=select_files),
        ttk.Button(toolbar, text="Выбрать папку…", command=select_folder),
    ]
    for button in buttons:
        button.pack(side="left", padx=(0, 8))
    root.mainloop()


if __name__ == "__main__":
    main()
