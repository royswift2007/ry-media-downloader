# Ry Pro Downloader

一个基于 `tkinter` 的 Windows 图形界面下载器，整合了：

- `yt-dlp`：YouTube / Bilibili / TikTok / 通用网页视频下载（含合并音视频、可选字幕）
- `N_m3u8DL-RE`：M3U8 下载
- `aria2c`：HTTP/FTP/磁力链接/BT 种子下载（支持选择文件）

> 项目核心入口：`ry_download.pyw`（双击运行的 GUI 脚本）。

---

## 功能一览

- 统一的保存目录（底部栏一处设置，三个标签页共用）
- 任务队列/并发控制（视频下载、M3U8 下载分别有并发设置；Aria2 也有全局并发）
- 限速（MB/s）
- 重试次数设置
- 自动合并音视频（通过 `ffmpeg`）
- YouTube Cookies 辅助（当遇到 403/需要登录/人机验证等情况时，自动尝试使用 cookies）
- Aria2：支持磁力链接/BT 种子并弹窗选择要下载的文件

---

## 环境要求

- Windows 10/11
- Python（运行源码时需要）：推荐 Python 3.9+（自带 `tkinter`）
- 工具文件（放在与 `ry_download.pyw` 同一目录）：
  - `yt-dlp.exe`
  - JavaScript 运行时（用于 `yt-dlp` 的 `yt-dlp-ejs` 相关能力）
    - 推荐：`deno.exe`
    - 也可使用：`node.exe` / `bun.exe` / `qjs.exe`（QuickJS）
  - `ffmpeg.exe`
  - `aria2c.exe`
  - `N_M3U8DL-RE.exe`（用于 M3U8 标签页；也可在界面内点击“更新 N_M3U8DL-RE”下载）

仓库（或发布包）内通常已包含上述 `.exe`，请不要随意改动文件名。

---

## 快速开始

### 方式 A：直接运行（推荐）

1. 确保目录中存在 `ry_download.pyw` 以及配套的 `.exe` 工具文件。
2. 双击运行 `ry_download.pyw`。

### 方式 B：命令行运行

在该目录打开 PowerShell：

```powershell
py -3 ry_download.pyw
```

## 目录结构（建议保持不变）

至少需要：

- `ry_download.pyw`：主程序（GUI）
- `yt-dlp.exe`：视频下载器
- JavaScript 运行时：`yt-dlp` 的 `yt-dlp-ejs` 相关能力需要（推荐 `deno.exe`，也可用 `node.exe` / `bun.exe` / `qjs.exe`）
- `ffmpeg.exe`：音视频合并/封装
- `aria2c.exe`：直链/BT/磁力下载器
- `N_M3U8DL-RE.exe`：M3U8 下载器（可在界面内更新）

---

## 界面说明（按标签页）

程序包含 3 个标签页：

1. `视频下载 (yt-dlp)`
2. `M3U8 下载`
3. `Aria2 下载`

底部栏为全局设置：

- `保存目录`：所有任务默认保存位置
- 通常包含“选择目录 / 打开目录”等按钮（便于快速定位下载结果）

---

## 1) 视频下载（yt-dlp）

支持平台提示：YouTube / Bilibili / TikTok / 通用网页。

常用流程：

1. 在 `视频 URL` 输入框粘贴链接
2. （可选）点击 `获取分辨率/格式` 获取可用清晰度/编码组合
3. （可选）填写 `重命名`（留空则自动使用网页标题）
4. 根据需要设置：
   - `重试次数`
   - `并发数`
   - `限速(MB/s)`（0 表示不限速）
   - （YouTube）字幕：无/英文/中文（会尝试写入并嵌入字幕）
5. 点击 `添加到队列`，再点击 `开始全部`

快捷下载：

- `1080p` / `720p` / `仅音频`：一键以预设格式加入队列
- `直接下载`：不选格式时按默认策略下载（通常相当于 best）

### YouTube Cookies（可选但很有用）

当遇到以下情况时，程序可能提示 cookies 失效/需要更新，或会自动改用 cookies 重试：

- 403 / Forbidden
- 需要登录（Private / Members-only / age gate）
- “not a bot”/人机验证导致无法获取信息

使用方式：

1. 用浏览器插件导出 cookies 文件（推荐插件：`Get cookies.txt LOCALLY`）
2. 生成文件名必须为：`www.youtube.com_cookies.txt`
3. 将该文件放到程序同目录（与 `ry_download.pyw` 同级）

注意：cookies 文件等同于“登录凭证”，请勿上传到 GitHub、不要发给他人。

---

## 2) M3U8 下载（N_m3u8DL-RE）

字段说明：

- `M3U8 URL`：必填
- `文件名[必填]`：必填（会校验 Windows 不允许的字符：`\\ / : * ? \" < > |`）
- `线程数`：下载分片的线程数
- `重试`：失败重试次数
- `并发`：M3U8 队列并发任务数
- `限速(M)`：MB/s（0 表示不限速）
- `Headers`：用于需要鉴权/Referer 的场景（按工具参数原样传入）
- `额外参数`：会按空格拆分并追加到命令行（高级用法）

基本流程：

1. 填入 `M3U8 URL` 与 `文件名`
2. 需要鉴权时在 `Headers` 填入请求头（例如 `Referer`、`User-Agent`、`Cookie` 等；多条请求头请按 `N_m3u8DL-RE` 的 `--headers` 规则填写）
3. 点击 `添加到队列`，再点击 `开始全部`

示例（仅示意，具体分隔符以 `N_m3u8DL-RE` 为准）：

```text
User-Agent: Mozilla/5.0\r\nReferer: https://example.com/
```

---

## 3) Aria2 下载（HTTP/FTP/BT/Magnet）

支持：

- HTTP/HTTPS/FTP 直链下载
- 磁力链接（`magnet:`）
- BT 种子（`.torrent` 文件）

常用操作：

- 粘贴链接到输入框后点击“添加”（加入 Aria2 队列）
- 点击“添加 BT 种子”选择 `.torrent` 文件
- 右键任务：打开文件/打开保存目录/停止并删除（具体以界面为准）

### 磁力/种子选择文件

当磁力链接/种子包含多个文件时，程序会弹出选择窗口：

- 支持“全选/全不选/反选”
- 未选中的文件不会下载（通过 Aria2 的 `select-file` 控制）

---

## 更新工具（需要联网）

顶部工具栏包含：

- `更新 yt-dlp`：下载最新 `yt-dlp.exe`
- `更新 N_M3U8DL-RE`：从 GitHub release 拉取 Windows x64 版本并替换

如果你在离线环境或网络受限环境中使用，请手动下载对应工具并放到同目录覆盖即可。

---

## 文件与数据说明

程序会在同目录生成/使用一些文件（名称以实际生成结果为准）：

- `window_pos.json`：窗口位置与大小
- `download_history_*.json`：下载历史（按下载器类别区分）
- `download_log_aria2.txt` / `download.log` 或 `Logs/`：运行日志
- `www.youtube.com_cookies.txt`：可选 cookies（不要分享/不要提交到仓库）

建议在 Git 仓库中添加 `.gitignore`，至少忽略：

- `www.youtube.com_cookies.txt`
- `download_history_*.json`
- `window_pos.json`
- `Logs/`、`download*.log`

---


## 常见问题（Troubleshooting）

### 1. 提示找不到 `N_M3U8DL-RE.exe`

- 点击顶部的“更新 N_M3U8DL-RE”自动下载；或手动放置 `N_M3U8DL-RE.exe` 到同目录。

### 2. YouTube 提示 cookies 失效

- 重新导出 `www.youtube.com_cookies.txt` 并覆盖旧文件。
- 确保导出的 cookies 对应 `www.youtube.com` 域名且仍在有效期。

### 3. 下载完成但没有声音/画面未合并

- 检查同目录是否存在 `ffmpeg.exe`。
- 这是合并音视频所必需的工具（`yt-dlp` 会调用它）。

### 4. Aria2 显示 RPC 未就绪

- 程序启动后会尝试拉起 `aria2c` 的 RPC 守护进程；如果被杀毒软件拦截/权限不足可能失败。
- 尝试以普通方式重启程序，或将目录加入安全软件白名单。

---

## 免责声明

请遵守当地法律法规与平台服务条款，仅下载你有权获取的内容。作者/维护者不对滥用行为及其后果承担责任。

