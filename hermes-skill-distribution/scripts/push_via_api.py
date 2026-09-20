#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""当 git(gnutls) 无法向 GitHub 推送时，用 GitHub Git Data API 提交本地目录（等价于 push）。

用法：python3 push_via_api.py <仓库相对目录或文件...> -m "提交信息"
  例：python3 push_via_api.py strategy-simulation-engine -m "add skill: ..."
密钥只从 /root/gh_token.txt 读取（不写进任何命令或文件）；显式禁用代理（api.github.com 直连可达）。
"""
import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "nihao19831123/hermes-skills"
TOKEN_FILE = os.path.join("/root", "gh_" + "token.txt")
API = "https://api.github.com"


def token():
    with open(TOKEN_FILE) as f:
        return f.read().strip()


def call(method, path, body=None):
    url = API + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", "Bearer " + token())
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    # 显式禁用环境代理（api.github.com 需直连）
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:            # 打印响应体，否则 400 无从下手
        print(f"HTTP {e.code} on {method} {path}\n{e.read().decode()[:700]}")
        raise


def collect(paths):
    """收集要上传的文件：{仓库相对路径: 本地绝对路径}"""
    out = {}
    for p in paths:
        if os.path.isfile(p):
            out[os.path.basename(p)] = p
        else:
            for root, _dirs, files in os.walk(p):
                for fn in files:
                    full = os.path.join(root, fn)
                    rel = os.path.relpath(full, ".")
                    out[rel] = full
    return out


def main():
    args = sys.argv[1:]
    if "-m" not in args:
        print(__doc__)
        return 2
    mi = args.index("-m")
    message = args[mi + 1]
    paths = [a for a in args[:mi] if not a.startswith("-")]
    files = collect(paths)
    print(f"待上传 {len(files)} 个文件：")
    for rel in sorted(files):
        print(f"  {rel} ({os.path.getsize(files[rel]):,} B)")

    ref = call("GET", f"/repos/{REPO}/git/ref/heads/main")
    base_commit = ref["object"]["sha"]
    commit = call("GET", f"/repos/{REPO}/git/commits/{base_commit}")
    base_tree = commit["tree"]["sha"]
    print(f"远端 main = {base_commit[:8]}（本地先看它没有被别人改写）")

    tree = []
    for rel, full in sorted(files.items()):
        with open(full, "rb") as f:
            content = base64.b64encode(f.read()).decode()
        blob = call("POST", f"/repos/{REPO}/git/blobs", {"content": content, "encoding": "base64"})
        tree.append({"path": rel.replace(os.sep, "/"), "mode": "100644", "type": "blob", "sha": blob["sha"]})
        print(f"  blob ✓ {rel} → {blob['sha'][:8]}")

    new_tree = call("POST", f"/repos/{REPO}/git/trees", {"base_tree": base_tree, "tree": tree})
    new_commit = call("POST", f"/repos/{REPO}/git/commits",
                      {"message": message, "tree": new_tree["sha"], "parents": [base_commit]})
    call("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": new_commit["sha"]})
    print(f"\n✅ 已提交：{new_commit['sha'][:8]} {message}")

    # 验收：raw 直连读回校验（用 curl，Python 直连 raw 常握手超时）
    for rel in sorted(files)[:2]:        # 只抽验 2 个（全量校验会被 raw 限速拖到超时）
        url = f"https://raw.githubusercontent.com/{REPO}/main/{rel.replace(os.sep, '/')}"
        out = subprocess.run(["curl", "-s", "--noproxy", "*", "-o", "/tmp/_raw_check", "-w", "%{http_code}",
                              url], capture_output=True, text=True)
        code = out.stdout.strip()
        size = os.path.getsize("/tmp/_raw_check") if os.path.exists("/tmp/_raw_check") else 0
        same = size == os.path.getsize(files[rel])
        print(f"  raw {rel}: HTTP={code} {size:,} B 与本地一致={same} {'✔' if same else '✘'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
