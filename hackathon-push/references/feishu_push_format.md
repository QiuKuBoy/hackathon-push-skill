# 飞书推送格式参考

## 卡片正文模板

```
🏁 黑客松情报 · YYYY-MM-DD HH:MM 版（真实赛事）

本轮共摸底 X+ 信源，以下为已核实赛事：

🟡 报名截止 15~30天 · 本周五推送

① 赛事名称
   · 主办：xxx
   · 赛道：xxx
   · 截止：YYYY-MM-DD（还剩 X 天）
   · 形式：线上/线下/混合
   · 人数：xxx
   · 奖金：最高 X 万元 + xxx
   · 链接：https://xxx

🟢 报名截止 > 30天 · 纳入观察列表

② 赛事名称
   · ...

🔴 已结束（确认）

③ 赛事名 → 已结束，不再推送

─────────────────────────
📡 本轮覆盖信源：企鹅号、腾讯新闻、CSDN、xxx 等
推送完毕 · pushed_hackathons.json 已更新
```

## 已结束判定

满足任一即标记 🔴 已结束，不再推送：

- 报名截止日期 < 今天
- 比赛结束日期 < 今天（若已知）

## 推送命令示例

```powershell
# 推荐：用脚本（自动分条 + 去重回写 + 配置化 chat_id）
# 先预览
python scripts/push_feishu.py --dry-run --text "🏁 黑客松情报 · ..."

# 实际发送
python scripts/push_feishu.py --text "🏁 黑客松情报 · ..."

# 结构化推送并写回去重记录
python scripts/push_feishu.py --json cards.json --update-json
```

> 不要直接拼接 `lark-cli` 命令发送——会绕过脚本的去重回写与分条逻辑。chat_id 通过命令行 `--chat-id`、`FEISHU_CHAT_ID` 环境变量或 `~/.workbuddy/hackathon-push/config.json` 提供，源码与文档中不再写死。

## 飞书消息限制与分条

- 单条文本消息过长会被截断，脚本默认按 ~2000 字自动分条发送（多条消息）。
- `lark-cli` 用 bot 身份无需用户授权，即发即用；不可用时回退飞书开放 API（需 `FEISHU_APP_ID`/`FEISHU_APP_SECRET`）。
- 发送前务必先 `--dry-run` 预览，确认内容与目标群无误，避免误推。

## 已推送赛事去重格式（pushed_hackathons.json）

```json
[
  {"id": "a1b2c3d4e5f6a7b8", "name": "模力工场×魔搭社区 AI 运营创作大赛", "pushed_at": "2026-07-30"},
  {"id": "c9d0e1f2a3b4c5d6", "name": "第二届钱潮杯 AI+跨境出海全球创业大赛", "pushed_at": "2026-07-30"}
]
```

- `id = md5(赛事名|报名截止日期)[:16]`（与 SKILL.md、push_feishu.py 保持一致）。
- 示例中的 id 为示意，实际由 `compute_id()` 计算，请勿手动编造。
