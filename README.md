# LoopForge

<img src="loopforge.png" width="112" alt="LoopForge logo">

LoopForge converts animated WebP files to WebM video with VP9 for Telegram stickers. It supports individual files and folders. Folder conversion includes subfolders and preserves their structure.

## Run on Windows

Install Python 3 with Tkinter. Install the dependencies and launch the app from this repository folder:

```powershell
python -m pip install -r requirements.txt
python webp_gui.py
```

If Python is installed in `C:\Python314`, use `C:\Python314\python.exe` in place of `python`. LoopForge uses FFmpeg from PATH when available or from the installed `imageio-ffmpeg` package.

Choose your WebP files or a folder, then select where to save the converted files.

The converter uses 30 FPS, preserves transparency, removes audio, and sets the longest side to 512 px. It takes the first three seconds of longer animations. It retries with stronger compression to meet the 256 KB limit and reports a failure if the result still exceeds that limit.

[Telegram video sticker requirements](https://core.telegram.org/stickers/webm-vp9-encoding)
