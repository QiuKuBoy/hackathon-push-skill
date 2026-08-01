---
name: hackathon-push
description: 面向 AI 黑客松参赛者的高价值赛事情报技能。当用户要求「搜黑客松」「推送赛事」「今日比赛」「帮我找 AI 比赛」「推送飞书」「生成赛事多维表」或定时触发赛事巡查时使用；英文触发：search hackathon, find AI competitions, push contest digest to Feishu, build hackathon table。职责：高价值信源搜索 → 截止日校验 → 分类（大厂/金融/政府/国际）→ 飞书消息推送（按用户设定频率闸门）+ 多维表格同步 → 去重。
agent_created: true
---

# hackathon-push · SKILL

面向 AI 黑客松参赛者，从互联网大厂、金融、政府/学会机构等高含金量信源巡查赛事情报，整理为结构化卡片，推送到飞书群，并同步进飞书多维表格（可筛选/排序的赛事库）。

本技能与具体 Agent 无关：状态目录可通过 `HACKATHON_PUSH_STATE_DIR` 覆盖，默认落在技能包 `data/` 子目录。

## 核心工作流

```
确定推送频率(首次交互) → 高价值信源搜索 → 截止日校验 → 生成 cards.json(带来源分类)
→ 飞书消息推送(按频率闸门) + 多维表格同步(始终更新) → 写去重记录
```

## 0. 时间基准

- 所有年份、截止日判断以系统当前时间为准，禁止写死年份。
- 「距今 X 天」用脚本的 `days_left()` 计算（基于 `datetime.date.today()`），不要估算。
- 搜索 query 中的年份用占位符 `{YYYY}`，运行时替换为当前年份。

## 第 0 步：确定推送频率 + 配置 chat_id（首次/缺失时）

若状态目录 `config.json` 未设置 `push_frequency`，用所在 Agent 的提问能力询问推送频率，三选一并写入：

- 每天（daily）：每个工作日推送紧急+观察赛事，周五附前瞻简报。
- 每周五（weekly_fri）：仅在周五推送当周汇总（紧急+观察+前瞻）。
- 仅手动（manual）：不自动发消息，仅在用户主动说「推送」时发；多维表仍每次更新。

```bash
python scripts/push_feishu.py --set-frequency daily      # 或 weekly_fri / manual
```

若 `chat_id` 未配置，脚本会打印获取方式与配置模板并退出。先引导用户完成配置再继续：

- 让用户去飞书群「群设置 → 群机器人 / 群 ID」拿到 chat_id（形如 `oc_xxxx`）；
- 选择一种配置方式：命令行 `--chat-id`、环境变量 `FEISHU_CHAT_ID`、或状态目录 `config.json` 写入 `{"chat_id":"oc_xxxx"}`；
- 用 `python scripts/push_feishu.py --show-config` 确认已生效。

飞书消息推送为可选项，由 `config.push_enabled` 控制（默认 `true`）。设为 `false` 时技能只更新多维表/数据库、不发消息；也可用 `--push` / `--no-push` 在单次运行时临时覆盖（见第四步）。多维表同步不受此开关影响，始终更新。

频率、chat_id 与 push_enabled 存于 `config.json`，后续脚本自动据此决定是否发消息（多维表始终更新）。

## 第一步：高价值信源搜索

完整信源与优先级见 `references/sources.md`。按 T1（大厂/金融/政府主办的高含金量平台）→ T2（大厂官方开发者社区）→ T3（国际）顺序，优先抓高含金量赛事。

- 用 Agent 的联网搜索能力；query 拼接当前年份（如 `2026 阿里 天池 大模型 挑战赛 报名`）与「报名中 / 截止」等表述。
- 用网页抓取能力读取赛事官方报名页，补全字段。
- 重点保真：大厂、金融、政府及学会赛事优先；低讨论度的厂商博客不主动抓。

## 第二步：截止日校验

- 每条候选赛事必须 WebFetch 其官方报名/官网页确认报名截止日，不要仅依赖搜索摘要（摘要常缺截止日，抽错会误判已结束或导致去重失效）。
- 截止日格式统一为 `YYYY-MM-DD`。无法确认时写 `暂无`，切勿编造日期（编造会导致去重 id 错乱、重复或漏推）。
- 已结束（截止日 < 今天）的赛事标记 🔴，进入多维表但不再推送消息。

## 第三步：生成情报卡片（带来源分类）

每个赛事整理为以下字段写入 `cards.json`（缺失字段标注「暂无」）：

```json
{
  "name": "赛事名称",
  "host": "主办方",
  "track": "赛道/方向",
  "deadline": "YYYY-MM-DD（或 暂无）",
  "contest_date": "YYYY-MM-DD ~ YYYY-MM-DD",
  "format": "线上/线下/混合",
  "team": "个人/团队/最多 X 人",
  "prize": "最高 X 万元 + 其他权益",
  "link": "https://报名链接",
  "category": "大厂 | 金融 | 政府/学会 | 国际 | 其他"
}
```

`category` 由该赛事的信源类型决定（见 sources.md 各信源标注），用于多维表筛选与消息分组。

分类与推送策略由脚本自动执行：

- 剩余 ≤ 15 天 → 🟠 紧急，纳入消息
- 剩余 15~30 天 → 🟡 观察，纳入消息
- 剩余 > 30 天 → 🟢 前瞻，仅周五随简报纳入消息
- 已结束 / 无日期 → 🔴 仅入多维表，不推送

卡片排版见 `references/feishu_push_format.md`。

## 第四步：飞书推送 + 多维表格同步

常态化推送必须用结构化路径（自动写去重、同步多维表）：

```bash
# 先预览（不发送）
python scripts/push_feishu.py --dry-run --json cards.json

# 实际推送 + 写去重 + 同步多维表（推荐）
python scripts/push_feishu.py --json cards.json --update-json

# 仅同步多维表 / 本地 CSV（不发消息）
python scripts/push_feishu.py --json cards.json --sync-bitable

# 临时覆盖推送开关（无视 config.push_enabled）
python scripts/push_feishu.py --json cards.json --update-json --push     # 强制发
python scripts/push_feishu.py --json cards.json --update-json --no-push  # 只更新库/多维表
```

消息是否发送、发送哪档，由 `push_frequency` 决定；多维表格每次都更新。推送开关规则：

- `push_enabled=true`（默认）且未传 `--no-push` → 按 `push_frequency` 闸门发消息；
- `push_enabled=false` → 绝不发消息，只更新多维表（除非本次显式 `--push`）；
- `--no-push` → 本次只更新库/多维表，绝不发消息（优先级最高）；
- `--push` → 本次强制发消息，并忽略 `manual` 频率闸门（手动「现在就推一份摘要」用）。

禁止用 `--text` 做常态化推送（`--text` 仅用于临时草稿预览，且不写去重）。单日消息最多 `daily_cap` 条（默认 12，可在 config 改）。

配置优先级：命令行 `--chat-id` > 环境变量 `FEISHU_CHAT_ID` > 状态目录 `config.json`。

1. `chat_id`：飞书群 ID。
2. `push_frequency`：daily / weekly_fri / manual（用 `--set-frequency` 写入）。
3. `push_enabled`：飞书消息推送总开关（默认 `true`；设 `false` 则只更新库/多维表、不发消息）。
4. `bitable_app_token` + `bitable_table_id`：飞书多维表格（可选，见下）。
5. `daily_cap`：单日消息上限（可选，默认 12）。
6. 开放 API 回退：`FEISHU_APP_ID` / `FEISHU_APP_SECRET`（lark-cli 不可用时需要）。

状态目录（存放 config.json、去重记录、本地 CSV，agent 无关）：环境变量 `HACKATHON_PUSH_STATE_DIR` 指定，否则默认技能包内 `data/`。

飞书多维表格（可选但推荐）：

1. 在飞书新建一个多维表格（Bitable），记下底座 `app_token`（URL 中 `/base/xxx` 的 xxx）。
2. 在表内新建一个数据表，记下 `table_id`（表 URL 中 `tblxxxx`）。
3. 把上述两个值写入状态目录 `config.json`：`{"bitable_app_token":"bascnXXX","bitable_table_id":"tblXXX"}`。
4. 脚本会自动 upsert 记录（按去重 ID 判重），字段见 `references/feishu_push_format.md`。
5. 若未配置，脚本跳过飞书多维表，仅生成本地 `data/hackathons.csv`（可移植的多维表兜底）。

推送实现：默认尝试 `lark-cli`（bot 身份）；不可用则回退飞书开放 API（需 `im:message`、`im:message:send_as_bot` 权限且机器人已入群）。脚本仅依赖 Python 标准库。

可用 `python scripts/push_feishu.py --show-config` 检查配置。

## 第五步：去重记录

`--update-json` 模式下，脚本把本轮实际推送的消息赛事以 `{id, name, deadline, pushed_at}` 追加写入状态目录 `pushed_hackathons.json`，同 id 去重合并。多维表同步走 upsert，不依赖此文件。

## 参考文件

- `references/feishu_push_format.md` — 卡片模板、多维表格字段 schema、分条与已结束标记
- `references/sources.md` — 高价值信源清单（大厂/金融/政府/国际）与搜索 query
- `scripts/push_feishu.py` — 推送+多维表脚本（lark-cli 优先 / API 回退 / 频率闸门 / 去重 / CSV）

## 定时巡查（可选）

建一个每日自动化（如每天 09:00）即可，频率由 `config.push_frequency` 决定，脚本内部处理「今天推不推、推哪档」，无需为周五单独建任务。提示词示例：

> 运行 hackathon-push 技能：搜索高价值 AI 黑客松赛事 → 校验截止日 → 生成 cards.json → 用 `python scripts/push_feishu.py --json cards.json --update-json` 推送并同步多维表（先 --dry-run 确认）。若 config 无 push_frequency，先问我推送频率。

## 快速启动口令

- 「搜一下最近的黑客松」
- 「帮我找 AI 比赛」
- 「推送赛事到飞书」
- 「生成赛事多维表」
- 「最近有哪些可以报名的比赛」
