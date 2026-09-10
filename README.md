# hermes-skills

个人 Hermes Agent 技能库（自建技能，跨机器复用）。

## 技能清单

| 技能 | 用途 |
|---|---|
| [`web-demo-video-narration`](web-demo-video-narration/SKILL.md) | 给本地 Web 系统/数据大屏录制带中文配音解说的演示视频（≤3分钟）：Playwright 按解说时间轴驱动页面录屏 + edge-tts 中文配音 + ffmpeg 字幕/标题卡 |

## 在别的电脑上安装

### 方式一：一条命令安装（推荐）

```bash
hermes skills install nihao19831123/hermes-skills/web-demo-video-narration
```

或直接用 SKILL.md 的 raw 地址：

```bash
hermes skills install https://raw.githubusercontent.com/nihao19831123/hermes-skills/main/web-demo-video-narration/SKILL.md
```

安装前可先预览（不落地）：

```bash
hermes skills inspect nihao19831123/hermes-skills/web-demo-video-narration
```

### 方式二：手动克隆

```bash
git clone https://github.com/nihao19831123/hermes-skills.git /tmp/hermes-skills
mkdir -p ~/.hermes/skills/media
cp -r /tmp/hermes-skills/web-demo-video-narration ~/.hermes/skills/media/
hermes skills list          # 确认已识别
```

## 注意

- `templates/` 目录是技能自带的模板/脚本，`hermes skills install` 只拉取 SKILL.md 本体；
  需要模板时用方式二手动克隆，或从本仓库直接下载。
- 依赖（在目标机器上装）：`ffmpeg`、`playwright` + chromium、`edge-tts`、
  中文字体、可选 `tesseract-ocr`（用于字幕自检）。具体见各技能正文的"前置检查"。
- 换机器通常需要调整 3 处：代理设置、中文字体路径、工作目录。详见技能正文。

## 许可

个人自用，随便拿去改。
