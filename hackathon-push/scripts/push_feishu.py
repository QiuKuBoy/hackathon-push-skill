"""
push_feishu.py — 飞书赛事推送 + 多维表格同步（无第三方依赖）

推送策略（自动降级）：
  1. 优先使用 lark-cli（bot 身份，无需用户授权）发送消息
  2. 若 lark-cli 不可用，回退到飞书开放 API 发送消息（需 FEISHU_APP_ID / FEISHU_APP_SECRET）

多维表格（Bitable，可选）：
  - 若配置 BITABLE_APP_TOKEN + BITABLE_TABLE_ID，则把赛事同步进飞书多维表格（upsert）
  - 未配置则跳过，仅生成本地 data/hackathons.csv 作为可移植的多维表兜底

配置（优先级：命令行 --chat-id > 环境变量 > 状态目录 config.json）：
  - chat_id        : 飞书群 ID（消息推送目标）
  - push_frequency : daily（每天）/ weekly_fri（仅周五）/ manual（仅手动触发时推送消息）
  - push_enabled   : 飞书消息推送总开关（默认 true；设为 false 则只更新库/多维表，绝不发消息）
  - bitable_app_token / bitable_table_id : 多维表格（可选）
  - daily_cap      : 单日消息最多推送几条赛事（默认 12）
  - FEISHU_APP_ID / FEISHU_APP_SECRET : lark-cli 不可用时开放 API 回退需要

状态目录（agent 无关）：
  1. 环境变量 HACKATHON_PUSH_STATE_DIR
  2. 默认：脚本所在技能包的 data/ 子目录

依赖：仅 Python 标准库（urllib / json / hashlib），无需 pip install。

用法：
    # 预览（不实际发送）
    python push_feishu.py --dry-run --text "消息内容"

    # 发送文本（草稿/临时，不建议常态化使用，因无法写去重）
    python push_feishu.py --text "消息内容"

    # 推荐：结构化推送 + 写去重 + 同步多维表（常态化用法）
    python push_feishu.py --json cards.json --update-json

    # 仅同步多维表 / 本地 CSV（不发消息）
    python push_feishu.py --json cards.json --sync-bitable

    # 临时覆盖推送开关（无视 config.push_enabled）
    python push_feishu.py --json cards.json --update-json --push     # 强制发
    python push_feishu.py --json cards.json --update-json --no-push  # 只更新库

    # 查看当前生效配置
    python push_feishu.py --show-config
"""

import json
import os
import sys
import csv
import hashlib
import argparse
import subprocess
from datetime import datetime, date
from urllib import request as urllib_request
from urllib.error import URLError, HTTPError

LARK_CLI = "lark-cli"


# ----------------------------------------------------------------------------
# 状态目录与配置
# ----------------------------------------------------------------------------

def resolve_state_dir() -> str:
    """状态目录：环境变量 HACKATHON_PUSH_STATE_DIR > 默认技能包内 data/。"""
    env = os.environ.get("HACKATHON_PUSH_STATE_DIR")
    if env:
        return env
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


STATE_DIR = resolve_state_dir()
CONFIG_PATH = os.path.join(STATE_DIR, "config.json")
PUSHED_JSON = os.path.join(STATE_DIR, "pushed_hackathons.json")
LAST_PUSH_JSON = os.path.join(STATE_DIR, "last_push.json")
CSV_PATH = os.path.join(STATE_DIR, "hackathons.csv")

# 卡片字段 → 中文标签
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

# 多维表格字段（全部文本，避免飞书字段类型坑；用户可在飞书 UI 改类型）
BITABLE_FIELDS = [
    "赛事名称", "主办方", "赛道方向", "报名截止", "剩余天数",
    "比赛时间", "形式", "人数", "奖金", "来源分类", "状态", "链接",
    "去重ID", "更新时间",
]


def compute_id(name: str, deadline: str) -> str:
    """去重 id：md5(赛事名|截止日期) 前 16 位，全局一致。"""
    return hashlib.md5(f"{name}|{deadline}".encode("utf-8")).hexdigest()[:16]


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg: dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def resolve_chat_id(cli_override: str = None) -> str:
    if cli_override:
        return cli_override
    env = os.environ.get("FEISHU_CHAT_ID")
    if env:
        return env
    return load_config().get("chat_id", "")


def print_chat_id_help():
    """chat_id 缺失时，打印获取方式与配置模板（替代冷冰冰的报错）。"""
    print("\n" + "=" * 52)
    print("未配置飞书群 chat_id，无法推送消息")
    print("=" * 52)
    print("如何获取 chat_id：")
    print("  飞书客户端打开目标群 → 群设置 → 群机器人 / 群 ID")
    print("  （形如 oc_xxxxxxxxxxxxxxxx，也可通过飞书开放平台 API 查询）")
    print("\n配置方式（任选其一，优先级从高到低）：")
    print("  1) 命令行   : python push_feishu.py --chat-id oc_xxxx ...")
    print("  2) 环境变量 : export FEISHU_CHAT_ID=oc_xxxx")
    print("  3) 配置文件 : 在状态目录 config.json 写入下例：")
    print('       {"chat_id": "oc_xxxx"}')
    print(f"\n状态目录：{STATE_DIR}")
    print("配置后运行  python push_feishu.py --show-config  验证是否生效。")
    print("=" * 52 + "\n")


def show_config():
    cfg = load_config()
    print("当前生效配置：")
    print(f"  chat_id        : {resolve_chat_id() or '(空)'}")
    print(f"  push_frequency : {cfg.get('push_frequency', 'daily（默认）')}")
    print(f"  push_enabled   : {cfg.get('push_enabled', True)}（true=发消息 / false=只更新库）")
    print(f"  daily_cap      : {cfg.get('daily_cap', 12)}")
    print(f"  lark-cli       : {'可用' if _cli_available() else '不可用（将回退开放 API）'}")
    print(f"  FEISHU_APP_ID  : {'已设置' if os.environ.get('FEISHU_APP_ID') else '未设置'}")
    print(f"  BITABLE_APP    : {'已设置' if cfg.get('bitable_app_token') else '未设置（跳过多维表）'}")
    print(f"  状态目录        : {STATE_DIR}")
    if not resolve_chat_id():
        print_chat_id_help()
    if not _cli_available() and not os.environ.get("FEISHU_APP_ID"):
        print("⚠️ lark-cli 不可用且未设置 FEISHU_APP_ID/SECRET，开放 API 回退将无法使用。")


# ----------------------------------------------------------------------------
# 去重状态
# ----------------------------------------------------------------------------

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


def load_last_push() -> dict:
    if not os.path.exists(LAST_PUSH_JSON):
        return {}
    try:
        with open(LAST_PUSH_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_last_push(freq: str, bucket: str):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(LAST_PUSH_JSON, "w", encoding="utf-8") as f:
        json.dump({"date": date.today().isoformat(), "freq": freq, "bucket": bucket},
                  f, ensure_ascii=False, indent=2)


# ----------------------------------------------------------------------------
# 分类与过滤（精准度核心）
# ----------------------------------------------------------------------------

def days_left(deadline_str: str):
    """返回距截止日的天数；无法解析返回 None。"""
    if not deadline_str:
        return None
    s = str(deadline_str).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            d = datetime.strptime(s, fmt).date()
            return (d - date.today()).days
        except ValueError:
            continue
    return None


def classify(cards: list) -> dict:
    """
    按剩余天数与状态分类。
    返回 {urgent(<=15), obs(15~30), far(>30), ended(已结束/无日期)} 四个列表。
    每个 card 附带 _days（剩余天数，None 表示未知）。
    """
    buckets = {"urgent": [], "obs": [], "far": [], "ended": []}
    for c in cards:
        n = days_left(c.get("deadline"))
        c["_days"] = n
        if n is None or n < 0:
            buckets["ended"].append(c)
        elif n <= 15:
            buckets["urgent"].append(c)
        elif n <= 30:
            buckets["obs"].append(c)
        else:
            buckets["far"].append(c)
    return buckets


def decide_message_cards(cards: list, freq: str, cap: int) -> list:
    """
    依据 push_frequency 决定「今天该发哪些赛事的消息」。
    - manual      ：永不自动发消息（仅手动 --text 时发）
    - weekly_fri  ：仅周五发（urgent + obs + 周五附 far 简报）
    - daily       ：每天发（urgent + obs + 周五附 far 简报）
    返回用于发消息的 card 列表（已截断到 cap 条）。
    """
    b = classify(cards)
    is_friday = date.today().weekday() == 4
    if freq == "manual":
        msg = []
    elif freq == "weekly_fri":
        msg = (b["urgent"] + b["obs"]) if is_friday else []
        if is_friday:
            msg = msg + b["far"]
    else:  # daily
        msg = b["urgent"] + b["obs"]
        if is_friday:
            msg = msg + b["far"]
    # 单日上限（仅限制消息条数，多维表不受影响）
    if cap and len(msg) > cap:
        msg = msg[:cap]
    return msg


def status_of(card: dict) -> str:
    n = card.get("_days")
    if n is None or n < 0:
        return "已结束"
    if n <= 7:
        return "即将截止"
    return "招募中"


# ----------------------------------------------------------------------------
# 文本分条
# ----------------------------------------------------------------------------

def chunk_text(text: str, size: int = 2000) -> list:
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


# ----------------------------------------------------------------------------
# 消息内容构建
# ----------------------------------------------------------------------------

def build_card_message(cards: list, today: date = None) -> str:
    today = today or date.today()
    b = classify(cards)
    header = f"🏁 黑客松情报 · {today.strftime('%Y-%m-%d')}（高价值赛事）\n"
    parts = []

    def render(lst, tag):
        if not lst:
            return ""
        lines = [tag]
        for i, c in enumerate(lst, 1):
            n = c.get("_days")
            dleft = f"（还剩 {n} 天）" if isinstance(n, int) and n >= 0 else ""
            block = [f"【{i}】{c.get('name', '未命名赛事')}{dleft}",
                     f"   · 来源分类：{c.get('category', '其他')}"]
            for key in ["host", "track", "deadline", "contest_date", "format",
                        "team", "prize", "requirement", "link"]:
                val = c.get(key)
                if val:
                    block.append(f"   · {FIELD_LABELS[key]}：{val}")
            lines.append("\n".join(block))
        return "\n".join(lines)

    urgent = render(b["urgent"], "🟠 紧急（≤15天）· 立即报名")
    obs = render(b["obs"], "🟡 观察（15~30天）· 本周关注")
    far = render(b["far"], "🟢 前瞻（>30天）· 储备关注")
    ended = render(b["ended"], "🔴 已结束 · 不再推送")

    body = "\n\n".join([x for x in [urgent, obs, far, ended] if x])
    if not body:
        body = "本轮未匹配到符合条件的赛事。"
    return header + "\n" + body + "\n\n──────────────\n📡 数据已同步至飞书多维表格，可筛选排序。"


# ----------------------------------------------------------------------------
# 飞书推送实现
# ----------------------------------------------------------------------------

def _cli_available() -> bool:
    try:
        subprocess.run([LARK_CLI, "--version"], capture_output=True, text=True, timeout=10)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _post_json(url: str, payload: dict, token: str = None, timeout: int = 20) -> dict:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib_request.Request(url, data=data, headers=headers, method="POST")
    with urllib_request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, token: str, timeout: int = 20) -> dict:
    req = urllib_request.Request(url, headers={"Authorization": f"Bearer {token}"}, method="GET")
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
        target = chat_id or "(预览模式，无需 chat_id)"
        print(f"【DRY-RUN】将发送 {len(chunks)} 条消息到 {target}：\n")
        for i, part in enumerate(chunks, 1):
            print(f"──── 第 {i}/{len(chunks)} 条 ────\n{part}\n")
        return True
    if not chat_id:
        print_chat_id_help()
        return False
    if _cli_available() and push_via_cli(chat_id, chunks):
        return True
    print("ℹ️ 使用飞书开放 API 推送")
    try:
        return push_via_api(chat_id, chunks)
    except (URLError, HTTPError, RuntimeError) as e:
        print(f"❌ 全部推送方式失败: {e}")
        return False


# ----------------------------------------------------------------------------
# 多维表格（Bitable）同步
# ----------------------------------------------------------------------------

def bitable_fields_of(card: dict) -> dict:
    n = card.get("_days")
    return {
        "赛事名称": card.get("name", ""),
        "主办方": card.get("host", ""),
        "赛道方向": card.get("track", ""),
        "报名截止": card.get("deadline", "") or "",
        "剩余天数": "" if n is None else str(n),
        "比赛时间": card.get("contest_date", ""),
        "形式": card.get("format", ""),
        "人数": card.get("team", ""),
        "奖金": card.get("prize", ""),
        "来源分类": card.get("category", "其他"),
        "状态": status_of(card),
        "链接": card.get("link", ""),
        "去重ID": card.get("id", ""),
        "更新时间": date.today().isoformat(),
    }


def write_bitable(cards: list) -> bool:
    """把赛事 upsert 进飞书多维表格。未配置则跳过。返回是否执行。"""
    cfg = load_config()
    app = cfg.get("bitable_app_token")
    table = cfg.get("bitable_table_id")
    if not app or not table:
        print("ℹ️ 未配置 BITABLE_APP_TOKEN / BITABLE_TABLE_ID，跳过飞书多维表格同步。")
        return False
    try:
        token = _get_tenant_token()
    except (URLError, HTTPError, RuntimeError) as e:
        print(f"❌ 获取 tenant token 失败，跳过多维表格：{e}")
        return False

    base = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app}/tables/{table}"

    # 1) 列出已有记录，建立 去重ID → record_id 映射
    existing = {}
    page = 1
    while True:
        try:
            resp = _get_json(f"{base}/records?page_size=100&page_token={page}", token)
        except Exception as e:
            print(f"❌ 读取多维表格记录失败：{e}")
            return False
        for rec in resp.get("data", {}).get("items", []):
            did = (rec.get("fields") or {}).get("去重ID", "")
            if did:
                existing[did] = rec.get("record_id")
        if not resp.get("data", {}).get("has_more"):
            break
        page += 1

    # 2) 分类为新增 / 更新
    new_recs, upd_recs = [], []
    for c in cards:
        fields = bitable_fields_of(c)
        did = c.get("id", "")
        if did in existing:
            upd_recs.append({"record_id": existing[did], "fields": fields})
        else:
            new_recs.append({"fields": fields})

    try:
        if new_recs:
            _post_json(f"{base}/records/batch_create", {"records": new_recs}, token=token)
            print(f"✅ 多维表格新增 {len(new_recs)} 条")
        if upd_recs:
            _post_json(f"{base}/records/batch_update", {"records": upd_recs}, token=token)
            print(f"✅ 多维表格更新 {len(upd_recs)} 条")
        if not new_recs and not upd_recs:
            print("ℹ️ 多维表格无变更")
        return True
    except Exception as e:
        print(f"❌ 写入多维表格失败：{e}")
        return False


def write_local_csv(cards: list):
    """本地 CSV 兜底（可移植的多维表，无需任何 API）。"""
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["赛事名称", "主办方", "赛道方向", "报名截止", "剩余天数",
                    "比赛时间", "形式", "人数", "奖金", "来源分类", "状态",
                    "链接", "去重ID", "更新时间"])
        for c in cards:
            w.writerow([
                c.get("name", ""), c.get("host", ""), c.get("track", ""),
                c.get("deadline", ""), "" if c.get("_days") is None else c["_days"],
                c.get("contest_date", ""), c.get("format", ""), c.get("team", ""),
                c.get("prize", ""), c.get("category", "其他"), status_of(c),
                c.get("link", ""), c.get("id", ""), date.today().isoformat(),
            ])
    print(f"✅ 本地多维表已生成：{CSV_PATH}")


# ----------------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------------

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="飞书赛事推送 + 多维表格同步")
    ap.add_argument("--chat-id", help="飞书群 chat_id（优先级高于环境变量/配置）")
    ap.add_argument("--text", help="直接发送的文本内容")
    ap.add_argument("--json", help="cards.json 路径，结构化赛事列表")
    ap.add_argument("--update-json", action="store_true", help="推送后写回去重记录（必须配合 --json）")
    ap.add_argument("--sync-bitable", action="store_true", help="仅同步多维表/本地CSV，不发送消息")
    ap.add_argument("--dry-run", action="store_true", help="仅预览，不实际发送")
    ap.add_argument("--push", action="store_true", help="强制发送消息（无视 push_enabled=false 与频率闸门，临时覆盖）")
    ap.add_argument("--no-push", action="store_true", help="本次只更新库/多维表、绝不发消息（无视 push_enabled=true，临时覆盖）")
    ap.add_argument("--show-config", action="store_true", help="显示当前配置后退出")
    ap.add_argument("--set-frequency", choices=["daily", "weekly_fri", "manual"],
                    help="设置推送频率并写入配置")
    args = ap.parse_args()

    if args.show_config:
        show_config()
        exit(0)

    chat_id = resolve_chat_id(args.chat_id)
    cfg = load_config()

    # 本次是否发消息：--no-push > --push > 配置 push_enabled（默认 true）
    if args.no_push:
        effective_push = False
    elif args.push:
        effective_push = True
    else:
        effective_push = cfg.get("push_enabled", True)

    if args.set_frequency:
        cfg["push_frequency"] = args.set_frequency
        save_config(cfg)
        print(f"✅ 推送频率已设为：{args.set_frequency}")
        exit(0)

    freq = cfg.get("push_frequency", "daily")
    cap = cfg.get("daily_cap", 12)

    # 读取结构化赛事
    cards = None
    if args.json:
        with open(args.json, "r", encoding="utf-8") as f:
            cards = json.load(f)
        # 确保每条有 id
        for c in cards:
            if not c.get("id") and c.get("name"):
                c["id"] = compute_id(c.get("name"), c.get("deadline") or "TBD")
    elif args.text:
        cards = None  # 纯文本草稿，无法结构化
    else:
        print("请提供 --text 或 --json 参数（常态化推送请用 --json）")
        exit(1)

    # ---- 仅同步多维表 ----
    if args.sync_bitable:
        if not cards:
            print("❌ --sync-bitable 需要 --json cards.json")
            exit(1)
        write_local_csv(cards)
        write_bitable(cards)
        exit(0)

    # ---- 消息推送 ----
    if args.text:
        # 草稿/临时：直接发文本，不写去重（避免误标）
        if not effective_push:
            print("ℹ️ 推送已禁用（push_enabled=false 或 --no-push），跳过消息发送。")
            exit(0)
        ok = push(chat_id, args.text, dry_run=args.dry_run)
        exit(0 if ok else 1)

    # 结构化路径：先分类，再按频率闸门决定发哪些
    # --push 时忽略频率闸门（用 daily 口径选择，手动想“现在就发一份摘要”）
    selection_freq = "daily" if args.push else freq
    msg_cards = decide_message_cards(cards, selection_freq, cap)
    today_bucket = freq if freq != "daily" else "daily"
    last = load_last_push()
    already_today = (last.get("date") == date.today().isoformat()
                     and last.get("freq") == freq and last.get("bucket") == today_bucket)

    if not effective_push:
        print("ℹ️ 推送已禁用（push_enabled=false 或 --no-push），跳过消息发送；仅同步多维表数据。")
        msg_cards = []
    elif not msg_cards:
        print("ℹ️ 依频率配置，今日无需推送消息；仅同步多维表数据。")
    elif already_today and not args.dry_run and not args.push:
        print("ℹ️ 今日该频率已推送过，跳过消息（多维表仍更新）。")
        msg_cards = []
    else:
        text = build_card_message(msg_cards)
        ok = push(chat_id, text, dry_run=args.dry_run)
        if ok and not args.dry_run:
            save_last_push(freq, today_bucket)
        if not ok:
            exit(1)

    # ---- 同步多维表（无论是否发消息都更新，保证数据库最新）----
    write_local_csv(cards)
    write_bitable(cards)

    # ---- 写去重 ----
    if args.update_json:
        # 仅把「实际推送的消息赛事」记过去重（草稿/未达阈值的不记）
        save_pushed([{"id": c.get("id"), "name": c.get("name"),
                      "deadline": c.get("deadline"), "pushed_at": date.today().isoformat()}
                     for c in (msg_cards if msg_cards else [])])
    else:
        print("ℹ️ 未指定 --update-json，本次不去重（建议常态化加 --update-json）。")

    exit(0)
