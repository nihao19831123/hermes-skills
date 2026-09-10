#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
演示视频录制模板: 按分镜时间窗驱动 Web 页面, 全程录屏(webm).
前置:
  1) 已生成 scenes.json = {"scenes":[{"n":1,"title":"...","dur":22.18,"text":"..."}...],"gap":0.4}
     (每个 dur 来自该段 TTS 音频的 ffprobe 时长 —— 先做配音再录屏)
  2) 目标页面/服务已在本机启动(注意: 先确认是当前项目路径的进程在跑)
用法: python3 record_timeline.py <URL>
产出: screen/*.webm + shots/*.png(每段结束抽帧, 便于自检)
"""
import json, os, sys, time
from playwright.sync_api import sync_playwright

URL   = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
BASE  = "/root/video"
VID, SHOT = f"{BASE}/screen", f"{BASE}/shots"
os.makedirs(VID, exist_ok=True); os.makedirs(SHOT, exist_ok=True)

D = json.load(open(f"{BASE}/scenes.json", encoding="utf-8"))
scenes, GAP = D["scenes"], D.get("gap", 0.4)

# ---- 分镜时间窗: [start, end] ----
t = 0.0; WINDOWS = []
for s in scenes:
    WINDOWS.append((round(t, 2), round(t + s["dur"], 2)))
    t += s["dur"] + GAP
TOTAL = round(t - GAP, 2)
print("时间窗:", WINDOWS, "总长", TOTAL)

with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader",
                                "--enable-unsafe-swiftshader", "--no-sandbox", "--hide-scrollbars"])
    ctx = b.new_context(viewport={"width": 1920, "height": 1080},
                        record_video_dir=VID, record_video_size={"width": 1920, "height": 1080},
                        accept_downloads=True, locale="zh-CN")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: print("PAGEERROR", str(e)[:120], flush=True))
    T0 = time.time()

    def log(m): print(f"[{time.time()-T0:7.2f}s] {m}", flush=True)

    def till(target):
        """等到绝对时刻 target(秒) —— 把每个分镜结束时间钉死, 这是音画对齐的关键"""
        d = target - (time.time() - T0)
        if d > 0: pg.wait_for_timeout(int(d * 1000))

    def click_sel(sel, note=""):
        try: pg.click(sel, timeout=4000); log(f"click {sel} {note}")
        except Exception as e: log(f"!! click {sel} 失败 {str(e)[:80]}")

    def drag(dx, dy, steps=30, note=""):
        """3D 地图缓转: 模拟鼠标拖拽(不依赖 map 句柄)"""
        try:
            box = pg.locator(".maplibregl-canvas").bounding_box()
            cx, cy = box["x"] + box["width"]/2, box["y"] + box["height"]/2
            pg.mouse.move(cx, cy); pg.mouse.down()
            for i in range(1, steps + 1):
                pg.mouse.move(cx + dx*i/steps, cy + dy*i/steps); pg.wait_for_timeout(28)
            pg.mouse.up(); log(f"drag {note}")
        except Exception as e: log(f"!! drag 失败 {str(e)[:80]}")

    def scroll(sel, ticks=5, step=240):
        """滚动指定面板: 先把鼠标移到面板上(wheel 作用于指针下的元素)"""
        try:
            bb = pg.locator(sel).bounding_box()
            pg.mouse.move(bb["x"]+bb["width"]/2, bb["y"]+min(bb["height"], 700)/2)
        except Exception: pass
        for _ in range(ticks):
            try: pg.mouse.wheel(0, step); pg.wait_for_timeout(800)
            except Exception: pass

    # ================= 分镜动作(按目标页面的真实选择器改写) =================
    # S1 开场: 等页面加载 + 地图缓转
    log("S1 打开页面")
    pg.goto(URL, wait_until="load", timeout=90000)
    pg.wait_for_timeout(4000)
    till(min(10.0, WINDOWS[0][1])); drag(-260, 40, 34, "开场缓转")
    till(WINDOWS[0][1]); pg.screenshot(path=f"{SHOT}/s1_end.png")

    # S2..S6 示例:
    # click_sel("#playBtn", "年份动画"); till(WINDOWS[1][0] + 15)
    # pg.locator("#metricGroup > div").nth(4).click(); till(WINDOWS[1][1])

    for i in range(1, len(WINDOWS)):
        till(WINDOWS[i][1])
        pg.screenshot(path=f"{SHOT}/s{i+1}_end.png")

    log(f"目标总时长 {TOTAL}s, 实际 {time.time()-T0:.1f}s")
    ctx.close()   # ★ 必须关闭 context 视频才落盘
    b.close()

vids = sorted([f for f in os.listdir(VID) if f.endswith(".webm")], key=lambda f: os.path.getmtime(f"{VID}/{f}"))
print("视频文件:", vids[-1] if vids else "无")
print("下一步: ffmpeg -i <webm> -i narration.mp3 -c:v libx264 -crf 20 -pix_fmt yuv420p -c:a aac -movflags +faststart out.mp4")
