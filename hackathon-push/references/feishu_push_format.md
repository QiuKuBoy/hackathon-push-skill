# 飞书推送格式参考

## 一、消息卡片正文模板（脚本自动生成）

```
🏁 黑客松情报 · YYYY-MM-DD（高价值赛事）

🟠 紧急（≤15天）· 立即报名
【1】赛事名称（还剩 X 天）
   · 来源分类：大厂
   · 主办：xxx
   · 赛道：xxx
   · 截止：YYYY-MM-DD
   · 形式：线上/线下/混合
   · 人数：xxx
   · 奖金：最高 X 万元 + xxx
   · 链接：https://xxx

🟡 观察（15~30天）· 本周关注
【2】……

🟢 前瞻（>30天）· 储备关注
【3】……（仅周五随简报出现）

🔴 已结束 · 不再推送
【4】赛事名 → 已结束，仅入多维表

──────────────
📡 数据已同步至飞书多维表格，可筛选排序。
```

- 消息是否发送、发送哪档，由 `push_frequency` 决定（详见 SKILL.md 第 0 步）；**多维表格每次都更新**，不受频率限制。
- 单日消息最多 `daily_cap` 条（默认 12），超出截断以避免刷屏。

## 二、飞书多维表格（Bitable）字段 schema

脚本会把每条赛事 upsert 进你配置的飞书多维表格。建议建表时保留以下字段（**全部文本类型**，避免飞书字段类型坑；你可在飞书 UI 自行改为日期/数字）：

| 字段名 | 说明 | 示例 |
|--------|------|------|
| 赛事名称 | 名称 | 阿里云天池 AI 大模型挑战赛 |
| 主办方 | host | 阿里云 |
| 赛道方向 | track | 大模型应用 |
| 报名截止 | deadline（YYYY-MM-DD，未知为「暂无」） | 2026-08-05 |
| 剩余天数 | 由脚本计算（已结束为「」） | 5 |
| 比赛时间 | contest_date | 2026-08-20~2026-08-25 |
| 形式 | 线上/线下/混合 | 线上 |
| 人数 | team | 团队≤3人 |
| 奖金 | prize | 最高30万元 |
| 来源分类 | category | 大厂 / 金融 / 政府/学会 / 国际 / 其他 |
| 状态 | 招募中 / 即将截止(≤7天) / 已结束 | 即将截止 |
| 链接 | link | https://... |
| 去重ID | md5(赛事名\|截止)[:16]，upsert 主键 | a1b2c3d4e5f6a7b8 |
| 更新时间 | 最近同步日期 | 2026-07-31 |

> 多维表格的价值在于**可筛选/排序**：参赛者可按「来源分类=金融」「状态=即将截止」「剩余天数」快速定位高价值赛事。

## 三、已结束判定

满足任一即标记 🔴 已结束，消息不推送（仅入多维表）：

- 报名截止日期 < 今天
- 比赛结束日期 < 今天（若已知）

## 四、推送命令示例

```bash
# 推荐：结构化推送 + 写去重 + 同步多维表（常态化）
python scripts/push_feishu.py --json cards.json --update-json

# 先预览，不实际发送
python scripts/push_feishu.py --dry-run --json cards.json

# 仅同步多维表 / 本地 CSV（不发消息）
python scripts/push_feishu.py --json cards.json --sync-bitable

# 设置推送频率（首次/变更时）
python scripts/push_feishu.py --set-frequency daily   # weekly_fri / manual

# 临时覆盖推送开关（无视 config.push_enabled）
python scripts/push_feishu.py --json cards.json --update-json --push     # 强制发（忽略频率闸门）
python scripts/push_feishu.py --json cards.json --update-json --no-push  # 只更新库/多维表
```

> **推送飞书是可选项**：`push_enabled` 默认 `true`（配好 chat_id 即按频率推送）；改成 `false` 则只更新多维表、绝不发消息。每次运行还可用 `--push` / `--no-push` 临时覆盖。优先级：`--no-push` > `--push` > `push_enabled`。多维表同步不受此开关影响，始终更新。

> **不要直接拼接 `lark-cli` 命令发送**——会绕过脚本的频率闸门、去重回写与多维表同步。chat_id 通过 `--chat-id`、`FEISHU_CHAT_ID` 或状态目录 `config.json` 提供，源码与文档不再写死。

## 五、飞书消息限制与分条

- 单条文本过长会被截断，脚本按 ~2000 字自动分条发送。
- `lark-cli` 用 bot 身份即发即用；不可用时回退飞书开放 API（需 `FEISHU_APP_ID`/`FEISHU_APP_SECRET` 及相应权限，且机器人已入群）。
- 发送前务必先 `--dry-run` 预览，确认内容与目标群无误。

## 六、去重记录格式（pushed_hackathons.json）

```json
[
  {"id": "a1b2c3d4e5f6a7b8", "name": "阿里云天池 AI 大模型挑战赛",
   "deadline": "2026-08-05", "pushed_at": "2026-07-31"}
]
```

- `id = md5(赛事名|报名截止日期)[:16]`（与 SKILL.md、push_feishu.py 一致）。
- 多维表以「去重ID」字段 upsert，与去重记录独立。
