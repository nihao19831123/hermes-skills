---
name: web-demo-video-narration
description: 给本地网页系统/数据大屏录制带中文配音解说的演示视频（比赛路演、项目汇报）。Playwright 按解说时间轴程序化驱动页面录屏 + edge-tts 中文配音 + ffmpeg 合成字幕/标题卡。触发词：展示视频、演示视频、路演视频、系统亮点视频、要配音/解说、视频控制在N分钟。
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, windows, macos]
metadata:
  hermes:
    tags: [video, playwright, tts, ffmpeg, demo, screen-recording, narration]
related_skills: [maplibre-gl-dashboards, strategy-simulation-engine]
---

# 网页系统演示视频（配音+字幕）制作

## 适用
- 目标：≤3 分钟的系统演示视频，含中文解说、烧入字幕、片头标题卡
- 对象：本地 Web 系统（如 localhost:8000 的驾驶舱/大屏）
- 优势：比手动录屏可控 —— 解说与画面时间轴精确对齐、单段可重录

## 前置检查
```bash
which ffmpeg ffprobe                      # 必须有
python3 -c "import playwright" || pip install -i https://pypi.tuna.tsinghua.edu.cn/simple playwright
playwright install chromium               # 或 PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright
which edge-tts || pip install -i https://pypi.tuna.tsinghua.edu.cn/simple edge-tts
fc-list | grep -i wqy                     # 中文字体(文泉驿正黑 /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc)
```

## 关键坑（先看这里）
1. **edge-tts 必须走 socks5 代理**：`HTTP_PROXY/HTTPS_PROXY` 会导致 `Connection reset by peer`，只有 `all_proxy=socks5://127.0.0.1:7890` 能通。运行时清除 http/https 代理变量：
   ```bash
   env -u HTTP_PROXY -u HTTPS_PROXY -u http_proxy -u https_proxy all_proxy=socks5://127.0.0.1:7890 edge-tts ...
   ```
2. **edge-tts 连接不稳定**（约 30-50% 失败率）：必须**重试 15 次**，且每次生成后用 `ffprobe` 校验能读出 duration —— 失败会留下**截断的假成功文件**（size>0 但损坏）。
3. **只裁首尾静音**，别用 `silenceremove stop_periods=-1`（会削掉句中停顿，听起来赶）。正确做法：去头静音 → `areverse` 去头 → 再 `areverse`。
4. **解说词里的数字必须从界面实算输出抓取**，不要凭空写。先跑一遍交互把面板/表格文本 dump 出来（`page.locator(...).inner_text()`），再据此写解说词。
   **为什么不能直接调同一个 API**：前端往往把参数重新包装后再发（实测 `fetch(..., body: JSON.stringify({params: p}))`，且滑块数值 `/100` 后传 0.2 而不是 20）。直接调 `/api/...` 会得到**另一套数字**（本会话直接调得累计门诊 5.76 万、界面实算 4.6 万，差 25%）。所以：先按真实交互流程跑一遍、抓面板文本，再写解说词；录完抽帧回看时数字与解说要对得上，否则答辩会被抓。
5. 页面里很多 `window.__xxx()` 全局函数挂在 `window` 上，可直接 `page.evaluate`/点击调用，比点 DOM 稳。
6. 时长控制：中文 edge-tts 约 5.3 字/秒（0% 语速）。超时优先**提语速**（`--rate=+15%` 约可压缩 13%），其次删文案。
7. 输出的 xlsx/mp4 若被 Excel/播放器占用会 `PermissionError`，**换成 v2/v3 新文件名**输出，别覆盖。
8. **Playwright 浏览器版本要与包版本匹配**：报 `Executable doesn't exist at .../chromium_headless_shell-1234` 时，用国内镜像秒下：
   ```bash
   PLAYWRIGHT_DOWNLOAD_HOST=https://cdn.npmmirror.com/binaries/playwright playwright install chromium
   ```
9. **演示服务要先确认"哪个路径的进程"在跑**：端口被旧进程占用时新的 uvicorn 启动失败但旧进程仍在服务 —— 表现为接口 500/404 而日志显示 startup complete。先 `ps aux | grep app.py` 核对工作目录，清掉旧进程再从当前项目目录启动。
8. **录制前先确认"在跑的是哪个路径的进程"**：演示服务若曾从旧目录启动，端口被它占着，新起的 uvicorn 会 `address already in use` 后退出，而接口表现为 **500/404**（旧进程仍用已不存在的路径服务静态文件）。先 `ps aux | grep app.py` 看工作目录、`ss -lntp | grep <端口>`，清掉旧进程再从当前项目目录启动，再开始录。
9. **开头 2-4s 是页面加载黑屏**，别直接开录就交给用户 —— 用 drawtext 标题卡覆盖这段时间（见流程 §5），既遮黑屏又强化片头。

## 流程

### 0. 先读项目材料，提炼分镜
读设计方案/提报材料，挑 5-6 个能讲清"数字智能 / AI / 数字孪生"卖点的功能点，每段 20-45 秒。
分镜必须能落到**具体交互**上（点哪个按钮、出什么面板/数字），不能只写"展示平台能力"。

### 1. 摸清页面交互
```python
# diag: 控制台错误 + canvas + 可见按钮文本 + 关键 DOM 结构
page.on("pageerror", ...); page.on("console", ...)
page.evaluate("""() => ({canvases:[...document.querySelectorAll('canvas')].length,
  webgl: !!(document.createElement('canvas').getContext('webgl')),
  btns:[...document.querySelectorAll('.btn')].map(b=>b.innerText.trim())})""")
```
再 `search_files` 读页面源码里的 `window.__` 函数、overlay id、按钮 id。
**先跑 smoke test**（打开→点每个关键交互→断言 overlay 可见/结果非空），再正式录制，避免 3 分钟白跑。

### 2. 写分镜脚本 script.txt
格式（脚本会被程序解析）：
```
[SCENE1 | 开场·数字孪生沙盘 | 22s]
解说词第一句。
解说词第二句。
```
解说词写成**口播体**：数字用中文读法（"百分之六十八"、"两点六万"、"一万三千七百五十九"），避免阿拉伯数字和英文缩写。

### 3. 生成配音 + 测时长
`gen_tts.py`：解析 script.txt → 逐场 edge-tts → ffprobe 测 duration → 写 scenes.json。
`trim_audio.py`：裁首尾静音 → 重算时长；`总长 = Σ场景时长 + 0.4s×场间隔`。目标 ≤175s 留余量。

### 4. 按时间轴驱动 + 录屏
```python
ctx = browser.new_context(viewport={"width":1920,"height":1080},
                          record_video_dir="screen",
                          record_video_size={"width":1920,"height":1080},
                          accept_downloads=True, locale="zh-CN")
T0 = time.time()
def till(target):                       # 关键：把动作卡进场景时间窗
    d = target - (time.time()-T0)
    if d > 0: page.wait_for_timeout(int(d*1000))
```
- 3D 地图用 `mouse.down/move/up` 拖拽旋转（缓动、分 30 步、每步 28ms）
- 滚轮滚动前先 `mouse.move` 到目标面板中心（滚轮作用于指针下元素）
- 每场结束 `till(窗口结束时间)`；场景边界截图存证
- 结束 `ctx.close()` 落盘 webm

### 5. 合成
```bash
# 旁白音轨：各场音频 + 0.4s 静音交替，filter_complex concat
ffmpeg -y -i s1.mp3 -i sil.mp3 -i s2.mp3 ... -filter_complex "[0:a][1:a]...concat=n=N:v=0:a=1[out]" -map "[out]" narration.mp3
# 合片
ffmpeg -y -i screen.webm -i narration.mp3 -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 192k -t <总长> out.mp4
# 标题卡 + 烧字幕（中文字体用 wqy-zenhei.ttc；alpha 表达式做淡入淡出）
ffmpeg -y -i out.mp4 -vf "drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text='标题':fontcolor=0xEAF2FF:fontsize=62:x=(w-text_w)/2:y=430:alpha='if(lt(t,0.8),t/0.8,if(lt(t,5.2),1,max(0,(6.0-t)/0.8)))',subtitles=sub.srt:force_style='FontName=WenQuanYi Zen Hei,FontSize=17,PrimaryColour=&H00FFFFFF,BorderStyle=1,Outline=1,Shadow=1,MarginV=28,Alignment=2'" -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a copy final.mp4
```
SRT 生成：按 `。；` 切句，句长占比分配该场时间窗。

### 6. 验证（必做）
**不要依赖视觉子代理**：`delegate_task(toolsets=['vision'])` 在本环境会退化成用 shell（bash/terminal）而空跑，拿不到图像分析结论。用程序化核验，实测可靠：

```bash
# 逐段抽帧(每6秒)
ffmpeg -ss $t -i final.mp4 -frames:v 1 f$t.png
```
对每帧算 4 个量（numpy + PIL）：
- 平均亮度：`<8` → 疑似黑屏
- 全屏亮像素数 `(g>110).sum()`：`<15000` → 疑似空白
- 边缘密度 `(|diff_x|+|diff_y|).sum()/size`：`<1.2` → 无细节
- 底部字幕条 `(g[0.88h:] > 150).sum()`：`<300` → 字幕没烧上

注意：深色驾驶舱里"面板区方差低"是正常的（大片深色卡片底），**不要用中央区 std 判空**，要用亮像素数+边缘密度联合判断。

音轨检查（必须 `-hide_banner` 否则 volumedetect 无输出）：
```bash
ffmpeg -hide_banner -ss $t -t 3 -i final.mp4 -af volumedetect -f null - 2>&1 | grep mean_volume
```
逐段 mean_volume 应在 -30 ~ -20 dB，出现 -91 dB 说明该段静音（配音漏生成）。

**字幕渲染的终极验证 —— OCR（本机已装 tesseract + chi_sim）**：
白字黑底必须**先二值化再反转**，否则 OCR 全乱码。流程：
```python
a = np.array(Image.open(frame).convert("L"))[840:985, :]   # 取下两条字幕行
bw = (a > 150).astype(np.uint8) * 255     # 亮字 => 255
inv = 255 - bw                            # 反成黑字白底
Image.fromarray(inv).resize((w*2, h*2), Image.LANCZOS)     # 2倍放大
```
再 `tesseract img stdout -l chi_sim --psm 6`，能读回解说词原文 = 字幕真实可读。
字体是否命中可另查：`ffmpeg -v info ... -vf subtitles=...` 输出里找 `fontselect: ... -> /usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`，若出现 fallback/glyph 警告说明字体没命中会渲染成方块。
字幕行高参考：1080p 下 `FontSize=17` 实测字高约 43px（两行），清晰可读；若 <25px 需调大 FontSize。

## 交付
- mp4 放到用户指定目录，同时给：无字幕版、解说词脚本 txt、字幕 srt
- 报告里写清"解说数字均来自系统实算输出"，便于答辩追问
- 询问可调项：音色（zh-CN-YunxiNeural 云希 / XiaoxiaoNeural 晓晓 / YunyangNeural 云扬）、语速、文案、字幕开关、单段重录
