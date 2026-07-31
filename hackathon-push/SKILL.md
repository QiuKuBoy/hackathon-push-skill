---
name: hackathon-push
description: 中国 AI 黑客松与开发者赛事情报推送技能。当用户要求「搜黑客松」「推送赛事」「今日比赛」「帮我找 AI 比赛」「推送飞书」或定时触发赛事巡查时使用；英文触发：search hackathon, find AI competitions, push contest digest to Feishu。职责：多信源搜索 → 去重 → 结构化整理 → 飞书推送 → 更新去重记录。
agent_created: true
---

# 黑客松情报员 · SKILL

## 核心工作流

```
多信源搜索 → 读取 pushed_hackathons.json 去重 → 生成情报卡片 → 推送飞书 → 更新 pushed_hackathons.json
```

本技能用于周期性（建议每日 + 每周五）巡查中国及可参加的国际 AI 黑客松 / 开发者赛事，整理为结构化情报并推送到飞书群。

## 0. 时间基准（重要）

- 所有年份、截止日期判断一律以**系统当前时间**为准（如 2026），**禁止写死具体年份**。
- 「距今 X 天」用 `datetime.date.today()` 计算，不要估算。
- 搜索 query 中的年份用占位符 `{YYYY}`，运行时替换为当前年份。

## 第一步：多信源搜索

完整信源清单与优先级见 `references/sources.md`，按 **T1（必抓）→ T2（补充）→ T3（兜底）** 顺序搜索。

**搜索策略：**

- 使用 Agent 提供的联网搜索能力；每次查询拼接当前年份（如 `2026 黑客松 报名 截止`）与「最近一个月 / 近期」等表述以筛选新赛事。
- 使用网页抓取能力读取赛事详情页，补全报名截止、奖金、链接等字段。
- 企鹅号 / 搜狗微信搜索结果通常含最完整的国内赛事情报，优先抓取。
- 对国内可能超时的站点（DoraHacks、天池），优先用搜索摘要而非直接抓取详情页。

## 第二步：去重检查

读取技能目录下的 `pushed_hackathons.json`（与 SKILL.md 同级）。

- 文件不存在 → 视为空列表 `[]`，首次运行先写入 `[]`。
- 以 `id` 字段比对，已存在的赛事跳过。

**id 生成规则（全局唯一，必须一致）：**

```
id = md5(f"{赛事名}|{报名截止日期}")[:16]
```

例：赛事名「模力工场×魔搭社区 AI 运营创作大赛」、截止 `2026-08-15`
→ `id = md5("模力工场×魔搭社区 AI 运营创作大赛|2026-08-15")[:16]`

可用 `scripts/push_feishu.py` 的 `compute_id(name, deadline)` 辅助生成。

## 第三步：情报卡片格式

每个赛事整理为以下字段（缺失字段标注「暂无」而非留空）：

```
【赛事名称】
- 主办方：xxx
- 赛道/方向：xxx
- 报名截止：YYYY-MM-DD（距今 X 天）
- 比赛时间：YYYY-MM-DD ~ YYYY-MM-DD
- 形式：线上/线下/混合
- 人数：个人/团队/最多 X 人
- 奖金：最高 X 万元 + 其他权益
- 参赛要求：xxx
- 报名链接：https://xxx
```

**分类与推送策略：**

- 报名截止 ≤ 15 天 → **立即推送**（飞书消息）
- 报名截止 15~30 天 → **周五推送**（记入观察列表，本周五一并发送）
- 报名截止 > 30 天 → **不主动推**，纳入每周简报
- 报名截止 < 今天 或 比赛结束 < 今天 → 标记 **🔴 已结束**，不再推送

卡片排版与分隔样式见 `references/feishu_push_format.md`。

## 第四步：推送飞书

**一律通过 `scripts/push_feishu.py` 推送，不要让模型自行拼接 `lark-cli` 命令**——直接敲命令会绕过脚本的去重回写与分条逻辑。

```powershell
# 仅预览，不实际发送（推荐先跑一次确认内容）
python scripts/push_feishu.py --dry-run --text "🏁 黑客松情报 · ..."

# 实际发送
python scripts/push_feishu.py --text "🏁 黑客松情报 · ..."

# 结构化推送并写回去重记录
python scripts/push_feishu.py --json cards.json --update-json
```

**配置 chat_id（三选一，优先级从高到低）：**

1. 命令行 `--chat-id oc_xxxx`
2. 环境变量 `FEISHU_CHAT_ID=oc_xxxx`
3. 运行时配置文件 `config.json`（位于状态目录）写入 `{"chat_id": "oc_xxxx"}`

**状态目录**（存放 config.json 与去重记录，agent 无关，自动解析）：
- 环境变量 `HACKATHON_PUSH_STATE_DIR` 指定 → 否则默认技能包内 `data/` 目录。

**推送实现说明：**

- 默认尝试 `lark-cli`（bot 身份，无需用户授权）。
- 若 `lark-cli` 不可用，自动回退到**飞书开放 API**：读取环境变量 `FEISHU_APP_ID`、`FEISHU_APP_SECRET`，换 `tenant_access_token` 后调用发送消息接口（需自建应用并开通 `im:message`、`im:message:send_as_bot`，且机器人已入群）。
- 单条消息过长时按 ~2000 字自动分条发送，避免截断。
- 脚本仅依赖 Python 标准库，无需 `pip install`。

可用 `python scripts/push_feishu.py --show-config` 检查当前生效配置。

## 第五步：更新去重记录

推送完成后，将本轮实际推送的赛事以 `{id, name, pushed_at}` 追加写入**运行时状态文件** `pushed_hackathons.json`（位于状态目录，默认技能包内 `data/`，可经 `HACKATHON_PUSH_STATE_DIR` 覆盖），同 id 去重合并（不重复写）。

- 用脚本 `--json cards.json --update-json` 模式时，脚本会自动写回。
- 若直接 `--text` 推送，可在推送后由模型用脚本的 `save_pushed` 逻辑补写，或下次改用 `--json` 模式以自动维护去重。

## 参考文件

- `references/feishu_push_format.md` — 飞书卡片格式模板与示例、已结束标记、分条说明
- `references/sources.md` — 各信源 URL 清单与抓取优先级、搜索 query 模板
- `scripts/push_feishu.py` — 飞书推送脚本（lark-cli 优先，开放 API 回退，支持分条）

## 定时巡查（可选）

要周期性自动运行，可在所用 Agent 的定时任务 / 自动化功能里创建计划，提示词写：「运行 hackathon-push 技能，执行今日赛事巡查并推送飞书。」建议：每天一次（覆盖 ≤15 天即时推送）+ 每周五一次（覆盖 15~30 天观察列表）。

## 快速启动口令

当用户说以下任一内容时，触发本技能：

- 「搜一下最近的黑客松」
- 「帮我找 AI 比赛」
- 「推送赛事到飞书」
- 「今日赛事巡查」
- 「最近有哪些可以报名的比赛」
