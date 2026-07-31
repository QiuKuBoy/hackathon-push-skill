# hackathon-push · 黑客松情报员

自动巡查中国及可参加的国际 **AI 黑客松 / 开发者赛事**，整理成结构化情报并推送到 **飞书群**。支持多信源搜索、去重、分类推送（紧急即时 / 周五汇总 / 长期观察）、状态持久化。

> 这是一个 [WorkBuddy](https://www.codebuddy.cn) Skill。

## 它能做什么

- **多信源巡查**：企鹅号/搜狗微信、天池、飞桨 AI Studio、DoraHacks、MLH、CSDN 等（详见 `references/sources.md`），按 T1/T2/T3 优先级搜索。
- **智能去重**：基于 `md5(赛事名|截止日期)` 记录已推送赛事，避免重复骚扰。
- **分类推送**：
  - 报名截止 ≤ 15 天 → 立即推送
  - 报名截止 15~30 天 → 本周五推送
  - 报名截止 > 30 天 → 纳入每周简报
  - 已结束 → 标记不再推送
- **飞书推送**：通过 `lark-cli`（首选）或飞书开放 API 推送，自动分条防截断。

## 安装

**方式一：导入 `.skill` 包**
1. 从 [Releases](../../releases) 下载 `hackathon-push.skill`。
2. 在 WorkBuddy 中导入该技能文件即可。

**方式二：放源码到 skills 目录**
```bash
# 把本仓库的 hackathon-push/ 目录放到用户级技能目录
cp -r hackathon-push ~/.workbuddy/skills/
```

## 配置

推送前需要告诉脚本**推到哪个飞书群**（chat_id），三选一，优先级从高到低：

1. 命令行参数：`--chat-id oc_xxxx`
2. 环境变量：`export FEISHU_CHAT_ID=oc_xxxx`
3. 配置文件：`~/.workbuddy/hackathon-push/config.json` 写入
   ```json
   {"chat_id": "oc_xxxx"}
   ```

**获取 chat_id**：在飞书客户端打开目标群 → 群设置 → 群机器人/群 ID，或通过飞书开放平台 API 查询。

**飞书开放 API 回退（可选）**：若环境没有 `lark-cli`，脚本会回退到飞书开放 API。需自建应用并配置环境变量：
```bash
export FEISHU_APP_ID=cli_xxxx
export FEISHU_APP_SECRET=xxxx
```
并给应用开通 `im:message`、`im:message:send_as_bot` 权限，且机器人已加入目标群。

> 状态文件（去重记录、配置）默认存放在 `~/.workbuddy/hackathon-push/`，**不会污染技能目录 / 仓库**。

## 使用

技能会在你说以下任一口令时触发：「搜一下最近的黑客松」「帮我找 AI 比赛」「推送赛事到飞书」「今日赛事巡查」……

也可建一个 WorkBuddy 自动化（每天 + 每周五）周期性巡查。提示词示例：
> 运行 hackathon-push 技能，执行今日赛事巡查并推送飞书。

手动预览 / 发送（脚本式，推荐）：
```bash
# 预览，不实际发送
python scripts/push_feishu.py --dry-run --text "🏁 黑客松情报 · ..."

# 实际发送
python scripts/push_feishu.py --text "🏁 黑客松情报 · ..."

# 结构化推送并维护去重
python scripts/push_feishu.py --json cards.json --update-json

# 查看当前生效配置
python scripts/push_feishu.py --show-config
```

`cards.json` 字段见 `examples/cards.example.json`。

## 目录结构

```
hackathon-push/
├── SKILL.md                      # 技能定义（工作流、触发词）
├── README.md
├── LICENSE
├── .gitignore
├── scripts/
│   └── push_feishu.py            # 飞书推送脚本（仅标准库，lark-cli 优先 / API 回退 / 分条 / dry-run）
├── references/
│   ├── sources.md                # 信源清单与搜索 query 模板
│   └── feishu_push_format.md     # 卡片格式与分条说明
└── examples/
    ├── cards.example.json        # 结构化赛事示例
    └── pushed_hackathons.example.json
```

## 常见问题

- **推送没反应？** 先跑 `--show-config` 确认 chat_id 与 lark-cli / 凭证是否就绪。
- **脚本报缺依赖？** 本脚本仅用 Python 标准库，无需 `pip install`。
- **如何不骚扰我的群？** 始终先 `--dry-run` 预览；发布出去的版本不含任何写死的 chat_id。

## License

[MIT](LICENSE)
