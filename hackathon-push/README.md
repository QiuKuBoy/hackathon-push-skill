# hackathon-push · 黑客松情报员（高价值版）

面向 **AI 黑客松参赛者**，从**互联网大厂、金融、政府/学会机构**等高含金量信源巡查赛事情报，整理为结构化卡片，推送到 **飞书群**，并同步进 **飞书多维表格**（可筛选/排序的赛事库）。

> 通用 Agent Skill，可在任意支持 SKILL.md 规范的 AI Agent 中使用；与具体 Agent / 平台无关。

## 它能做什么

- **高价值信源巡查**：阿里天池、飞桨、Biendata、DataFountain、和鲸、讯飞、微信/企鹅号，以及大厂开发者社区、WAIC/中国人工智能学会/教育部赛事、银行券商金融科技赛、MLH/Devpost/Kaggle 等国际平台（详见 `references/sources.md`）。
- **截止日校验**：每条赛事强制回官方页确认报名截止日，避免抽错导致误判/去重失效。
- **来源分类**：每条赛事标注 `大厂 / 金融 / 政府·学会 / 国际 / 其他`，便于筛选。
- **可交互的推送频率**：首次使用询问「每天 / 每周五 / 仅手动」，存配置后脚本自动按频率闸门决定发消息。
- **飞书多维表格**：每次同步进 Bitable（可筛选排序）；未配置 Bitable 时生成本地 `hackathons.csv` 兜底。
- **智能去重**：基于 `md5(赛事名|截止日期)` 记录已推送赛事，避免重复骚扰。

## 安装

**方式一：导入 `.skill` 包**
1. 从 [Releases](../../releases) 下载 `hackathon-push.skill`。
2. 在所用 Agent 的技能管理界面导入即可。

**方式二：放源码到 skills 目录**
```bash
cp -r hackathon-push <agent-skills-dir>/
```

## 配置

所有配置存于**状态目录**（环境变量 `HACKATHON_PUSH_STATE_DIR` 指定，否则默认技能包内 `data/`）的 `config.json`：

```json
{
  "chat_id": "oc_xxxx",
  "push_frequency": "daily",
  "bitable_app_token": "bascnXXXX",
  "bitable_table_id": "tblXXXX",
  "daily_cap": 12
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `chat_id` | 是 | 飞书群 ID（也可用 `--chat-id` 或环境变量 `FEISHU_CHAT_ID`） |
| `push_frequency` | 否 | `daily` / `weekly_fri` / `manual`，默认 `daily`；也可用 `--set-frequency` 写入 |
| `bitable_app_token` | 否 | 飞书多维表格底座 app_token（URL 中 `/base/xxx` 的 xxx） |
| `bitable_table_id` | 否 | 多维表格内的数据表 table_id（`tblxxxx`） |
| `daily_cap` | 否 | 单日消息最多推送几条赛事，默认 12 |

**获取 chat_id**：飞书客户端打开目标群 → 群设置 → 群机器人/群 ID，或通过开放平台 API 查询。

**飞书开放 API 回退（可选）**：若环境无 `lark-cli`，脚本回退开放 API，需自建应用并配置环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`，开通 `im:message`、`im:message:send_as_bot`，且机器人已入群。

**多维表格（可选但推荐）**：在飞书新建多维表格 → 记下 app_token 与 table_id → 写入上述 config。字段 schema 见 `references/feishu_push_format.md`。未配置则仅生成本地 CSV。

## 使用

触发口令：「搜一下最近的黑客松」「帮我找 AI 比赛」「推送赛事到飞书」「生成赛事多维表」……

首次运行若未设 `push_frequency`，技能会**询问你推送频率**后再工作。

推荐在所用 Agent 的定时任务里建一个**每日**计划（频率由 config 决定，脚本内部处理「今天推不推」）。提示词示例：
> 运行 hackathon-push 技能：搜索高价值 AI 黑客松 → 校验截止日 → 生成 cards.json → `python scripts/push_feishu.py --json cards.json --update-json`（先 --dry-run 确认）。若 config 无 push_frequency，先问我推送频率。

手动调用（脚本式）：
```bash
python scripts/push_feishu.py --dry-run --json cards.json   # 预览
python scripts/push_feishu.py --json cards.json --update-json   # 推送+去重+同步多维表
python scripts/push_feishu.py --json cards.json --sync-bitable   # 仅同步多维表/CSV
python scripts/push_feishu.py --set-frequency weekly_fri   # 设置频率
python scripts/push_feishu.py --show-config   # 查看配置
```

`cards.json` 字段见 `examples/cards.example.json`。

## 目录结构

```
hackathon-push/
├── SKILL.md                      # 技能定义（工作流、触发词、频率交互）
├── README.md
├── LICENSE
├── .gitignore
├── scripts/
│   └── push_feishu.py            # 推送+多维表脚本（标准库，lark-cli 优先/API 回退/频率闸门/去重/CSV）
├── references/
│   ├── sources.md                # 高价值信源清单（大厂/金融/政府/国际）
│   └── feishu_push_format.md     # 卡片模板、多维表格字段 schema
└── examples/
    ├── cards.example.json
    └── pushed_hackathons.example.json
```

## 常见问题

- **推送没反应？** 先 `--show-config` 确认 chat_id 与 lark-cli / 凭证。
- **多维表没更新？** 确认 `bitable_app_token`/`bitable_table_id` 正确，且应用有 Bitable 读写权限；否则会退化为本地 CSV。
- **脚本报缺依赖？** 仅用 Python 标准库，无需 `pip install`。
- **隐私？** 发布的版本不含任何写死的 chat_id；状态文件均在状态目录，已被 `.gitignore` 忽略。

## License

[MIT](LICENSE)
