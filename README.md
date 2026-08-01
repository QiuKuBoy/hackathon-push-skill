# hackathon-push-skill · 黑客松情报员

> 通用 AI Agent Skill，可在任意支持 `SKILL.md` 规范的智能体中使用，与具体 Agent / 平台无关。
> 面向 AI 黑客松参赛者，从互联网大厂、金融、政府/学会机构等高含金量信源巡查赛事情报，整理为结构化卡片，推送到飞书群，并同步进飞书多维表格（可筛选/排序的赛事库）。

[English](#english) · [安装](#安装) · [配置](#配置) · [使用](#使用) · [隐私与安全](#隐私与安全)

---

## 它能做什么

- **高价值信源巡查**：阿里天池、飞桨、Biendata、DataFountain、和鲸、讯飞、微信/企鹅号，以及大厂开发者社区、WAIC / 中国人工智能学会 / 教育部赛事、银行券商金融科技赛、MLH / Devpost / Kaggle 等国际平台（详见 `references/sources.md`）。
- **截止日校验**：每条赛事强制回官方页确认报名截止日，避免抽错导致误判或去重失效。
- **来源分类**：每条赛事标注 `大厂 / 金融 / 政府·学会 / 国际 / 其他`，便于筛选。
- **可交互的推送频率**：首次使用询问「每天 / 每周五 / 仅手动」，存配置后脚本自动按频率闸门决定发消息。
- **飞书多维表格**：每次同步进 Bitable（可筛选排序）；未配置 Bitable 时生成本地 `hackathons.csv` 兜底。
- **智能去重**：基于 `md5(赛事名|截止日期)` 记录已推送赛事，避免重复骚扰。
- **推送可开关**：飞书消息推送为可选项，可手动触发或交给定时任务，也可只维护赛事库而不推送。

## 安装

```bash
# 克隆后，把整个仓库目录（即技能根，含 SKILL.md）放进所用 Agent 的 skills 目录
git clone https://github.com/QiuKuBoy/hackathon-push-skill.git
cp -r hackathon-push-skill <agent-skills-dir>/
```

## 配置

所有配置存于**状态目录**（`HACKATHON_PUSH_STATE_DIR` 环境变量可覆盖，否则默认技能包内 `data/`）的 `config.json`：

```json
{
  "chat_id": "oc_xxxx",
  "push_frequency": "daily",
  "push_enabled": true,
  "bitable_app_token": "bascnXXXX",
  "bitable_table_id": "tblXXXX",
  "daily_cap": 12
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| `chat_id` | 是* | 飞书群 ID（也可用 `--chat-id` 或环境变量 `FEISHU_CHAT_ID`）。*仅当要推送飞书消息时需要 |
| `push_frequency` | 否 | `daily` / `weekly_fri` / `manual`，默认 `daily`；也可用 `--set-frequency` 写入 |
| `push_enabled` | 否 | 飞书消息推送总开关，默认 `true`；设 `false` 则只更新库 / 多维表、绝不发消息 |
| `bitable_app_token` | 否 | 飞书多维表格底座 app_token（URL 中 `/base/xxx` 的 xxx） |
| `bitable_table_id` | 否 | 多维表格内的数据表 table_id（`tblxxxx`） |
| `daily_cap` | 否 | 单日消息最多推送几条赛事，默认 12 |

**获取 chat_id**：飞书客户端打开目标群 → 群设置 → 群机器人 / 群 ID，或通过开放平台 API 查询。

**飞书开放 API 回退（可选）**：若环境无 `lark-cli`，脚本回退开放 API，需自建应用并配置环境变量 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`，开通 `im:message`、`im:message:send_as_bot`，且机器人已入群。

**多维表格（可选但推荐）**：在飞书新建多维表格 → 记下 app_token 与 table_id → 写入上述 config。字段 schema 见 `references/feishu_push_format.md`。未配置则仅生成本地 CSV。

## 使用

触发口令：「搜一下最近的黑客松」「帮我找 AI 比赛」「推送赛事到飞书」「生成赛事多维表」……

首次运行若未设 `push_frequency`，技能会先询问推送频率再工作。

推荐在所用 Agent 的定时任务里建一个**每日**计划（频率由 config 决定，脚本内部处理「今天推不推」）。提示词示例：
> 运行 hackathon-push 技能：搜索高价值 AI 黑客松 → 校验截止日 → 生成 cards.json → `python scripts/push_feishu.py --json cards.json --update-json`（先 --dry-run 确认）。若 config 无 push_frequency，先问我推送频率。

手动调用（脚本式）：
```bash
python scripts/push_feishu.py --dry-run --json cards.json                 # 预览
python scripts/push_feishu.py --json cards.json --update-json            # 推送+去重+同步多维表
python scripts/push_feishu.py --json cards.json --sync-bitable           # 仅同步多维表/CSV
python scripts/push_feishu.py --json cards.json --update-json --push     # 强制发（忽略频率闸门）
python scripts/push_feishu.py --json cards.json --update-json --no-push  # 只更新库/多维表
python scripts/push_feishu.py --set-frequency weekly_fri                 # 设置频率
python scripts/push_feishu.py --show-config                             # 查看配置
```

推送飞书为可选项：`push_enabled` 默认 `true`（配好 chat_id 即按频率推送）；设为 `false` 则只更新多维表、绝不发消息。每次运行可用 `--push` / `--no-push` 临时覆盖（优先级 `--no-push` > `--push` > `push_enabled`）。多维表同步不受此开关影响。

`cards.json` 字段与 `category` 取值见 SKILL.md「第三步：生成情报卡片」代码块。

## 目录结构

```
hackathon-push-skill/
├── SKILL.md                      # 技能定义（工作流、触发词、频率交互）
├── README.md
├── LICENSE
├── .gitignore
├── scripts/
│   └── push_feishu.py            # 推送+多维表脚本（仅标准库，lark-cli 优先 / API 回退 / 频率闸门 / 去重 / CSV）
└── references/
    ├── sources.md                # 高价值信源清单（大厂 / 金融 / 政府 / 国际）
    └── feishu_push_format.md     # 卡片模板、多维表格字段 schema
```

## 隐私与安全

- 本仓库不包含任何个人飞书凭据：所有 `chat_id` / `app_id` / `app_secret` 均为占位符或运行时从环境变量 / 本地 `config.json` 读取。
- 状态文件全部本地：去重记录、`config.json` 位于状态目录（默认 `data/`），已被 `.gitignore` 忽略，不会进入 git / GitHub。
- 本仓库仅发布源码：`hackathon-push-skill.skill` 为本地打包产物，不纳入版本控制（见 `.gitignore`），仅供本地一键导入；GitHub 上请直接 clone 本仓库使用。
- 仅标准库依赖：`push_feishu.py` 只使用 Python 标准库（`urllib`），无需 `pip install`。

## 常见问题

- **推送没反应？** 先 `--show-config` 确认 chat_id 与 lark-cli / 凭证。
- **多维表没更新？** 确认 `bitable_app_token` / `bitable_table_id` 正确，且应用有 Bitable 读写权限；否则会退化为本地 CSV。
- **脚本报缺依赖？** 仅用 Python 标准库，无需 `pip install`。
- **会骚扰我的群吗？** 发布的版本不含任何写死的 chat_id；始终先 `--dry-run` 预览再实发。

## License

[MIT](LICENSE)

---

## English

**hackathon-push-skill** is an AI-Agent skill (framework-agnostic, works with any agent that supports the `SKILL.md` convention). It scans high-value AI hackathon sources — big-tech developer platforms, finance, government / academic societies, and international platforms — curates structured contest cards, pushes them to a Feishu group, and syncs them into a Feishu Bitable (a filterable / sortable contest database).

- Install: copy this repository folder (the skill root, containing `SKILL.md`) into your agent's skills directory.
- Configure: a local `config.json` in the state dir holds `chat_id`, `push_frequency`, optional `bitable_app_token` / `bitable_table_id`. No secrets are hardcoded.
- Push is optional: `push_enabled` (default `true`) gates Feishu messages; `--push` / `--no-push` override per run. The Bitable / CSV database always stays up to date.
- Zero dependencies: pure Python standard library.

See `references/sources.md` for the source list and `references/feishu_push_format.md` for the card schema.

## Contributing

Issues and PRs are welcome. Please keep `config.json` / state files out of commits (already gitignored).
