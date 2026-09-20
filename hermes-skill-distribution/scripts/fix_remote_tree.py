#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""清理远端仓库里被误嵌套的目录（Git Data API 的 sha=null 删除条目），并列出当前远端结构。

用法：python3 fix_remote_tree.py <按前缀删除的相对路径>   # 例：strategy-simulation-engine/strategy-simulation-engine/
"""
import json
import os
import subprocess
import sys
import urllib.request

REPO = "nihao19831123/hermes-skills"
TOKEN_FILE = os.path.join("/root", "gh_" + "token.txt")
API = "https://api.github.com"


def call(method, path, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body is not None else None,
                                 method=method)
    req.add_header("Authorization", "Bearer " + open(TOKEN_FILE).read().strip())
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("Content-Type", "application/json")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=60) as r:
        return json.loads(r.read().decode())


def remote_tree():
    ref = call("GET", f"/repos/{REPO}/git/ref/heads/main")
    sha = ref["object"]["sha"]
    tree = call("GET", f"/repos/{REPO}/git/trees/{sha}?recursive=1")
    return sha, tree["tree"]


def main():
    prefix = sys.argv[1] if len(sys.argv) > 1 else None
    sha, tree = remote_tree()
    blobs = [x for x in tree if x["type"] == "blob"]
    print(f"远端 main = {sha[:8]}，文件 {len(blobs)} 个")
    for b in sorted(blobs, key=lambda x: x["path"]):
        flag = "  ← 待删除" if (prefix and b["path"].startswith(prefix)) else ""
        print(f"  {b['size']:>7,} B  {b['path']}{flag}")
    if not prefix:
        return 0
    victims = [b["path"] for b in blobs if b["path"].startswith(prefix)]
    if not victims:
        print(f"没有匹配前缀 {prefix} 的文件，无需清理")
        return 0
    commit = call("GET", f"/repos/{REPO}/git/commits/{sha}")
    entries = [{"path": p, "mode": "100644", "type": "blob", "sha": None} for p in victims]   # sha=null 即删除
    new_tree = call("POST", f"/repos/{REPO}/git/trees",
                    {"base_tree": commit["tree"]["sha"], "tree": entries})
    new_commit = call("POST", f"/repos/{REPO}/git/commits",
                      {"message": f"chore: 删除误嵌套目录 {prefix}（{len(victims)} 个文件）",
                       "tree": new_tree["sha"], "parents": [sha]})
    call("PATCH", f"/repos/{REPO}/git/refs/heads/main", {"sha": new_commit["sha"]})
    print(f"\n✅ 已删除 {len(victims)} 个嵌套文件，提交 {new_commit['sha'][:8]}")

    # 复核：raw 直连读一个应已消失的路径
    probe = victims[0]
    out = subprocess.run(["curl", "-s", "--noproxy", "*", "-o", "/dev/null", "-w", "%{http_code}",
                          f"https://raw.githubusercontent.com/{REPO}/main/{probe}"],
                         capture_output=True, text=True)
    print(f"复核 raw {probe}: HTTP={out.stdout.strip()}（404 表示已删除）")
    sha2, tree2 = remote_tree()
    left = [b["path"] for b in tree2 if b["type"] == "blob" and b["path"].startswith(prefix)]
    print(f"远端现存匹配文件：{len(left)} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
