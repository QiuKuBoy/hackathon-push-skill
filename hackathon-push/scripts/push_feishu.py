"""
push_feishu.py — 飞书赛事推送脚本（无第三方依赖）

推送策略（自动降级）：
  1. 优先使用 lark-cli（bot 身份，无需用户授权）
  2. 若 lark-cli 不可用，回退到飞书开放 API（需环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET）

配置（优先级：命令行 --chat-id > 环境变量 FEISHU_CHAT_ID > 运行时 config.json）：
  - 飞书群 chat_id：命令行 --chat-id、环境变量 FEISHU_CHAT_ID，或 ~/.workbuddy/hackathon-push/config.json
  - 开放 API 凭证：环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET（lark-cli 不可用时需要）

依赖：仅 Python 标准库（urllib），无需 pip install。

用法：
    # 预览（不实际发送）
    python push_feishu.py --dry-run --text "消息内容"

    # 发送文本
    python push_feishu.py --text "消息内容"

    # 读取结构化赛事列表并推送 + 写回去重记录
    python push_feishu.py --json cards.json --update-json

    # 查看当前生效配置
    python push_feishu.py --show-config
"""

import json
import os
import sys
import hashlib
import argparse
import subprocess
from datetime import datetime, date
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

LARK_CLI = "lark-cli"
STATE_DIR = os.path.join(os.path.expanduser("~"), ".workbuddy", "hackathon-push")
CONFIG_PATH = os.path.join(STATE_DIR, "config.json")
PUSHED_JSON = os.path.join(STATE_DIR, "pushed_hackathons.json")

# 字段中文标签（结构化赛事 → 可读文本）
FIELD_LABELS = {
    "name": "赛事名称",
    "host": "主办",
    "track": "赛道",
    "deadline": "截止",
    "contest_date": "比赛时间",
    "format": "形式",
    "team": "人数",
    "prize": "奖金",
    "requirement": "参赛要求",
    "link": "链接",
}


def compute_id(name: str, deadline: str) -> str:
    """去重 id：md5(赛事名|截止日期) 前 16 位，全局保持一致。"""
    return hashlib.md5(f"{name}|{deadline}".encode("utf-8")).hexdigest()[:16]


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def resolve_chat_id(cli_override: str = None) -> str:
    if cli_override:
        return cli_override
    env = os.environ.get("FEISHU_CHAT_ID")
    if env:
        return env
    return load_config().get("chat_id", "")


def show_config():
    cfg = load_config()
    print("当前生效配置：")
    print(f"  chat_id 来源 : {'命令行/环境变量/配置' if resolve_chat_id() else '未配置！'}")
    print(f"  chat_id      : {resolve_chat_id() or '(空)'}")
    print(f"  lark-cli     : {'可用' if _cli_available() else '不可用（将回退开放 API）'}")
    print(f"  FEISHU_APP_ID: {'已设置' if os.environ.get('FEISHU_APP_ID') else '未设置'}")
    print(f"  FEISHU_APP_SECRET: {'已设置' if os.environ.get('FEISHU_APP_SECRET') else '未设置'}")
    print(f"  状态目录      : {STATE_DIR}")
    if not resolve_chat_id():
        print("\n⚠️ 未配置 chat_id，请通过以下任一方式配置后再推送：")
        print("  1) 命令行：--chat-id oc_xxxx")
        print("  2) 环境变量：export FEISHU_CHAT_ID=oc_xxxx")
        print(f"  3) 配置文件：{CONFIG_PATH} 写入 {{\"chat_id\": \"oc_xxxx\"}}")
    if not _cli_available() and not os.environ.get("FEISHU_APP_ID"):
        print("⚠️ lark-cli 不可用且未设置 FEISHU_APP_ID/SECRET，开放 API 回退将无法使用。")


# ---------------- 状态文件（运行时目录，不进仓库） ----------------

def load_pushed() -> list:
    if not os.path.exists(PUSHED_JSON):
        return []
    try:
        with open(PUSHED_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_pushed(items: list) -> list:
    """追加已推送赛事并去重合并（同 id 不重复写）。"""
    os.makedirs(STATE_DIR, exist_ok=True)
    existing = load_pushed()
    ids = {it.get("id") for it in existing}
    added = 0
    for it in items:
        if not it.get("id") and it.get("name") and it.get("deadline"):
            it["id"] = compute_id(it["name"], it["deadline"])
        if it.get("id") and it["id"] not in ids:
            existing.append(it)
            ids.add(it["id"])
            added += 1
    with open(PUSHED_JSON, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)
    print(f"✅ 去重记录已更新：新增 {added} 条，共 {len(existing)} 条")
    return existing


# ---------------- 文本分条 ----------------

def chunk_text(text: str, size: int = 2000) -> list:
    """飞书文本消息按长度分条，避免截断。"""
    if len(text) <= size:
        return [text]
    lines = text.split("\n")
    chunks, cur = [], ""
    for ln in lines:
        if len(cur) + len(ln) + 1 > size:
            chunks.append(cur)
            cur = ln
        else:
            cur = cur + "\n" + ln if cur else ln
    if cur:
        chunks.append(cur)
    return chunks


# ---------------- 推送实现 ----------------

def _cli_available() -> bool:
    try:
        subprocess.run([LARK_CLI, "--version"], capture_output=True, text=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _post_json(url: str, payload: dict, token: str = None, timeout: int = 15) -> dict:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib_request.Request(url, data=data, headers=headers, method="POST")
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def push_via_cli(chat_id: str, chunks: list) -> bool:
    for i, part in enumerate(chunks, 1):
        cmd = [LARK_CLI, "im", "+messages-send", "--as", "bot",
               "--chat-id", chat_id, "--msg-type", "text", "--text", part]
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            print(f"⚠️ lark-cli 第 {i} 条超时")
            return False
        if r.returncode != 0:
            print(f"❌ lark-cli 失败: {r.stderr.strip()}")
            return False
        try:
            print(f"✅ lark-cli 推送成功（第 {i}/{len(chunks)} 条）| {json.loads(r.stdout)['data']['message_id']}")
        except Exception:
            print(f"✅ lark-cli 推送成功（第 {i}/{len(chunks)} 条）")
    return True


def _get_tenant_token() -> str:
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    if not app_id or not app_secret:
        raise RuntimeError("缺少环境变量 FEISHU_APP_ID / FEISHU_APP_SECRET（lark-cli 不可用时需要）")
    resp = _post_json(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        {"app_id": app_id, "app_secret": app_secret})
    return resp["tenant_access_token"]


def push_via_api(chat_id: str, chunks: list) -> bool:
    token = _get_tenant_token()
    url = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id"
    for i, part in enumerate(chunks, 1):
        _post_json(url, {"receive_id": chat_id, "msg_type": "text",
                         "content": json.dumps({"text": part})}, token=token)
        print(f"✅ 开放 API 推送成功（第 {i}/{len(chunks)} 条）")
    return True


def push(chat_id: str, text: str, dry_run: bool = False) -> bool:
    chunks = chunk_text(text)
    if dry_run:
        print(f"【DRY-RUN】将发送 {len(chunks)} 条消息到 chat_id={chat_id}：\n")
        for i, part in enumerate(chunks, 1):
            print(f"──── 第 {i}/{len(chunks)} 条 ────\n{part}\n")
        return True
    if not chat_id:
        print("❌ 未配置 chat_id，无法推送。用 --show-config 查看配置方式。")
        return False
    if _cli_available() and push_via_cli(chat_id, chunks):
        return True
    print("ℹ️ 使用飞书开放 API 推送")
    try:
        return push_via_api(chat_id, chunks)
    except (URLError, HTTPError, RuntimeError) as e:
        print(f"❌ 全部推送方式失败: {e}")
        return False


def build_card_message(cards: list, today: date = None) -> str:
    today = today or date.today()
    header = f"🏁 黑客松情报 · {today.strftime('%Y-%m-%d')}\n\n"
    blocks = []
    for i, c in enumerate(cards, 1):
        lines = [f"【{i}】{c.get('name', '未命名赛事')}"]
        for key in ["host", "track", "deadline", "contest_date", "format",
                    "team", "prize", "requirement", "link"]:
            val = c.get(key)
            if val:
                lines.append(f"   · {FIELD_LABELS[key]}：{val}")
        blocks.append("\n".join(lines))
    return header + "\n\n".join(blocks)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="飞书赛事推送")
    ap.add_argument("--chat-id", help="飞书群 chat_id（优先级高于环境变量/配置）")
    ap.add_argument("--text", help="直接发送的文本内容")
    ap.add_argument("--json", help="cards.json 路径，结构化赛事列表")
    ap.add_argument("--update-json", action="store_true", help="推送后写回去重记录")
    ap.add_argument("--dry-run", action="store_true", help="仅预览，不实际发送")
    ap.add_argument("--show-config", action="store_true", help="显示当前配置后退出")
    args = ap.parse_args()

    if args.show_config:
        show_config()
        exit(0)

    chat_id = resolve_chat_id(args.chat_id)

    if args.json:
        with open(args.json, "r", encoding="utf-8") as f:
            cards = json.load(f)
        text = build_card_message(cards)
    elif args.text:
        text = args.text
    else:
        print("请提供 --text 或 --json 参数")
        exit(1)

    ok = push(chat_id, text, dry_run=args.dry_run)
    if ok and not args.dry_run and args.update_json and args.json:
        save_pushed([{"name": c.get("name"), "deadline": c.get("deadline"),
                      "pushed_at": date.today().isoformat()} for c in cards])
    exit(0 if ok else 1)
