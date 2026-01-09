Here is the complete English translation of your documentation, optimized for a GitHub README or a technical user guide.

---

# Ry Pro Downloader

## Overview

A Windows-based graphical downloader built with `tkinter`. It integrates the following powerful command-line tools:

* **`yt-dlp`**: Supports downloading from YouTube, Bilibili, TikTok, and general web videos (includes video/audio merging and optional subtitles).
* **`N_m3u8DL-RE`**: Specialized for M3U8 stream downloading.
* **`aria2c`**: Supports HTTP/FTP, Magnet links, and BitTorrent (with file selection support).

> **Main Entry Point**: `ry_download.pyw` (The GUI script designed to be run by double-clicking).

---

## Features

* **Unified Save Directory**: A single setting in the bottom bar applies to all three download tabs.
* **Task Queue & Concurrency Control**: Independent concurrency settings for Video and M3U8 downloads; global concurrency for Aria2.
* **Speed Limiting**: Adjustable speed limits in MB/s.
* **Retry Mechanism**: Custom retry attempts for failed tasks.
* **Auto-Muxing**: Automatically merges video and audio streams using `ffmpeg`.
* **YouTube Cookies Support**: Automatically attempts to use cookies when encountering 403 Forbidden, login requirements, or CAPTCHAs.
* **Aria2 File Selection**: Pop-up window for selecting specific files within Magnet links or Torrents.

---

## Environment Requirements

* **OS**: Windows 10/11
* **Python**: (If running from source) Python 3.9+ is recommended (includes `tkinter`).
* **Required Binaries** (Must be placed in the same directory as `ry_download.pyw`):
* `yt-dlp.exe`
* **JavaScript Runtime** (Required for `yt-dlp-ejs` capabilities in `yt-dlp`):
* Recommended: `deno.exe`
* Alternatives: `node.exe`, `bun.exe`, or `qjs.exe` (QuickJS).


* `ffmpeg.exe` (and `ffprobe.exe`)
* `aria2c.exe`
* `N_M3U8DL-RE.exe` (Used for the M3U8 tab; can also be updated via the in-app "Update" button).



*Note: These `.exe` files are NOT included in the repository/package. Please download them from their respective official websites and place them in the root directory.*

---

## Quick Start

### Method A: Direct Run (Recommended)

1. Ensure `ry_download.pyw` and all required `.exe` binaries are in the same folder.
2. Double-click `ry_download.pyw` to launch.

### Method B: Command Line

Open PowerShell in the project directory and run:

```powershell
py -3 ry_download.pyw

```

---

## Directory Structure (Recommended)

Keep the following files in the same root folder for optimal performance:

* `ry_download.pyw` (Main GUI)
* `yt-dlp.exe`
* `deno.exe` (or other JS runtime)
* `ffmpeg.exe`
* `aria2c.exe`
* `N_M3U8DL-RE.exe`

---

## Interface Guide (By Tab)

The application consists of three main tabs and a global footer:

1. **Video Download (yt-dlp)**
2. **M3U8 Download**
3. **Aria2 Download**

**Global Footer:**

* **Save Directory**: Sets the default download path for all tasks.
* **Browse/Open Buttons**: For quick directory selection and access to downloaded files.

---

## 1) Video Download (yt-dlp)

**Supported Platforms**: YouTube, Bilibili, TikTok, and most generic video sites.

**Standard Workflow**:

1. Paste the link into the **Video URL** field.
2. (Optional) Click **Get Resolution/Formats** to view available quality and codec options.
3. (Optional) Enter a **Rename** value (leave blank to use the webpage title).
4. Configure settings: **Retries**, **Concurrency**, and **Speed Limit** (0 for unlimited).
5. **Subtitles (YouTube)**: Choose None / English / Chinese (will attempt to embed subtitles into the file).
6. Click **Add to Queue**, then click **Start All**.

**Quick Shortcuts**:

* **Direct Download**: Downloads using the default strategy (usually "best") if no format is selected.

### YouTube Cookies (Optional but Recommended)

If you encounter 403 Forbidden errors, "Not a bot" verification, or need to download private/members-only content:

1. Use a browser extension to export cookies (Recommended: `Get cookies.txt LOCALLY`).
2. Save the file as: `www.youtube.com_cookies.txt`.
3. Place this file in the **same directory** as `ry_download.pyw`.

> **Security Warning**: Cookies files are essentially "login credentials." Do NOT upload them to GitHub or share them with others.

---

## 2) M3U8 Download (N_m3u8DL-RE)

**Field Descriptions**:

* **M3U8 URL**: The source link (Required).
* **Filename**: The output name (Required; automatically validates against illegal Windows characters like `\ / : * ? " < > |`).
* **Threads**: Number of threads for segment downloading.
* **Retry/Concurrency/Speed Limit**: Similar to the video tab.
* **Headers**: Used for authentication/referer requirements (passed directly to the tool).
* **Extra Args**: Additional command-line arguments for advanced users.

**Example Headers**:

```text
User-Agent: Mozilla/5.0\r\nReferer: https://example.com/

```

---

## 3) Aria2 Download (HTTP/FTP/BT/Magnet)

**Supported Types**:

* Direct links (HTTP/HTTPS/FTP).
* Magnet links (`magnet:`).
* BitTorrent files (`.torrent`).

**Operations**:

* Paste a link and click **Add** to join the Aria2 queue.
* Click **Add BT Torrent** to select a `.torrent` file from your computer.
* **Right-click tasks**: Open file location, Open save directory, or Stop and Delete.

**File Selection**:
For Magnets or Torrents with multiple files, a selection window will pop up. You can Select All, Deselect All, or Invert Selection. Unchecked files will not be downloaded.

---

## Updating Tools (Internet Required)

The top toolbar includes:

* **Update yt-dlp**: Downloads the latest `yt-dlp.exe`.
* **Update N_M3U8DL-RE**: Fetches the latest Windows x64 version from GitHub Releases.

If you are in a restricted network environment, please manually replace the `.exe` files in the root directory.

---

## Files & Data Reference

The program generates or uses the following files:

* `window_pos.json`: Saves window position and size.
* `download_history_*.json`: Stores task history by category.
* `Logs/` or `download.log`: System logs for troubleshooting.
* `www.youtube.com_cookies.txt`: Optional YouTube credentials.

**Recommended `.gitignore**`:

```text
www.youtube.com_cookies.txt
download_history_*.json
window_pos.json
Logs/
download*.log

```


## Troubleshooting

1. **"N_M3U8DL-RE.exe not found"**: Click "Update N_M3U8DL-RE" in the toolbar or manually place the file in the root directory.
2. **YouTube Cookies Invalid**: Re-export the cookies file and ensure it is named correctly.
3. **No Audio / Merging Failed**: Ensure `ffmpeg.exe` exists in the root directory. `yt-dlp` requires it to mux video and audio.
4. **Aria2 RPC Not Ready**: The program launches an Aria2 RPC daemon on startup. If it fails, check if antivirus software is blocking the process or port.

---

## Disclaimer

Please comply with local laws and the terms of service of the platforms you use. Only download content you have the right to access. The author/maintainer assumes no responsibility for any misuse or legal consequences.

---

