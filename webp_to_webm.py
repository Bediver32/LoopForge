import argparse
from pathlib import Path
import shutil
import subprocess
import tempfile

from PIL import Image

FPS = 30
MAX_FRAMES = 90
MAX_BYTES = 256_000


def find_ffmpeg():
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    try:
        from imageio_ffmpeg import get_ffmpeg_exe
    except ImportError as error:
        raise RuntimeError("Установите зависимости из requirements.txt или добавьте FFmpeg в PATH.") from error
    return get_ffmpeg_exe()


def convert(source, target, ffmpeg):
    if target.exists():
        raise ValueError(f"Файл уже существует: {target}")

    with Image.open(source) as animation, tempfile.TemporaryDirectory(
        dir=target.parent
    ) as temp:
        if animation.format != "WEBP" or not animation.is_animated:
            raise ValueError("Выберите анимированный файл WebP.")

        width, height = animation.size
        scale = 512 / max(width, height)
        size = tuple(max(2, round(side * scale / 2) * 2) for side in (width, height))
        raw = Path(temp) / "frames.rgba"
        encoded = Path(temp) / "sticker.webm"
        elapsed_ms = 0
        written = 0

        with raw.open("wb") as frames:
            for index in range(animation.n_frames):
                animation.seek(index)
                frame = animation.convert("RGBA")
                elapsed_ms += max(1, animation.info.get("duration", 0))
                end = min(MAX_FRAMES, (elapsed_ms * FPS + 999) // 1000)
                if end > written:
                    pixels = frame.resize(size, Image.Resampling.LANCZOS).tobytes()
                    frames.write(pixels * (end - written))
                    written = end
                if written == MAX_FRAMES:
                    break

        for crf in (28, 36, 44, 52, 60, 63):
            subprocess.run(
                [
                    ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                    "-f", "rawvideo", "-pixel_format", "rgba",
                    "-video_size", f"{size[0]}x{size[1]}",
                    "-framerate", str(FPS), "-i", str(raw),
                    "-an", "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p",
                    "-b:v", "0", "-crf", str(crf), "-deadline", "good",
                    "-cpu-used", "4", "-threads", "2", str(encoded),
                ],
                check=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            byte_count = encoded.stat().st_size
            if byte_count <= MAX_BYTES:
                encoded.rename(target)
                return byte_count
        raise ValueError("Не удалось уложиться в 256 КБ. Попробуйте укоротить исходник.")


def main():
    parser = argparse.ArgumentParser(description="Анимированный WebP → видеостикер Telegram")
    parser.add_argument("source", type=Path, help="Исходный файл .webp")
    parser.add_argument("target", type=Path, nargs="?", help="Выходной файл .webm")
    args = parser.parse_args()
    target = args.target or args.source.with_suffix(".webm")
    if target.suffix.lower() != ".webm":
        parser.error("Укажите расширение .webm для выходного файла.")
    try:
        byte_count = convert(args.source, target, find_ffmpeg())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Ошибка: {error}\n")
    print(f"Готово: {target} ({byte_count:,} байт)")


if __name__ == "__main__":
    main()
