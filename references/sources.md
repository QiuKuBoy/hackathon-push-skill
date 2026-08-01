# 高价值信源清单（面向 AI 黑客松参赛者）

> 定位：**高含金量**赛事。优先大厂、金融、政府/学会机构；专业竞赛平台承载大量企业/政府/金融命题赛；国际平台补充可参加的高价值赛事。
> 所有年份查询与文案使用**当前年份**（由系统时间确定），搜索 query 年份用占位符 `{YYYY}`。

## 如何给赛事打 `category`（写入 cards.json）

| 信源性质 | category 取值 |
|----------|---------------|
| 阿里/腾讯/字节/百度/华为/美团/京东/蚂蚁/小米/网易/快手等大厂主办或承办 | `大厂` |
| 银行/券商/保险/金融科技公司主办的金融科技/算法赛 | `金融` |
| 政府/学会/高校/事业单位主办（WAIC、中国人工智能学会、教育部赛事、地方政府双创等） | `政府/学会` |
| MLH / Devpost / Kaggle / HackerEarth / GitHub 等国际平台 | `国际` |
| 其他（媒体、创业社区、未明确归类） | `其他` |

---

## T1（每次必抓 · 高含金量竞赛平台）

| 信源 | URL | 覆盖 | category |
|------|-----|------|----------|
| 阿里天池 | tianchi.aliyun.com | 阿里系算法/大模型/AI 开发者大赛，含大量企业命题赛 | 大厂 |
| 百度飞桨 AI Studio | aistudio.baidu.com | 飞桨开源挑战赛、AI 创作大赛、高校赛 | 大厂 |
| Biendata | biendata.com | 高校/企业/政府 AI 挑战赛，含金量高 | 大厂/政府/学会 |
| DataFountain（数据科学竞赛） | datafountain.com | 政府/金融/企业命题赛聚集地 | 金融/政府/学会 |
| 和鲸 Kesci | kesci.com | 数据科学竞赛，常承接企业/机构赛 | 大厂/其他 |
| FlyAI | flyai.com | AI 算法与应用赛 | 其他 |
| 讯飞开放平台 AI 开发者大赛 | xfyun.cn | 科大讯飞主办，语音/认知 AI 赛 | 大厂 |
| 微信/企鹅号（国内赛事情报） | weixin.sogou.com（微信文章搜索）；企鹅号文章见 new.qq.com / om.qq.com | 政府/金融/大厂赛事的媒体发布与汇总，最全 | 按实际主办归类 |

## T2（补充抓 · 大厂官方开发者社区）

| 信源 | URL | category |
|------|-----|----------|
| 阿里云开发者社区 | developer.aliyun.com | 大厂 |
| 腾讯云开发者社区 | cloud.tencent.com/developer | 大厂 |
| 华为云开发者社区 | developer.huaweicloud.com；华为软件精英挑战赛 huawei.com | 大厂 |
| 字节跳动 / 火山引擎开发者社区 | developer.volcengine.com | 大厂 |
| 百度飞桨社区 | aistudio.baidu.com | 大厂 |

> 大厂社区主要发布**自家**赛事，命中率有限；每次必抓 T1，T2 作为补充，不主动穷举每个厂商博客。

## T3（兜底 · 政府/学会/国际 + 高价值金融）

| 信源 | URL | category |
|------|-----|----------|
| 世界人工智能大会 WAIC 黑客松 | worldaic.com.cn | 政府/学会 |
| 中国人工智能学会 CAAI | caai.cn | 政府/学会 |
| 教育部/国家级赛事（中国软件杯、中国大学生计算机设计大赛等） | 各赛事官网 / 教育部门户 | 政府/学会 |
| 地方政府双创/AI 大赛（中关村、深圳、上海等） | 各地政府官网 / 新闻 | 政府/学会 |
| 金融科技专项（银行/券商金融科技大赛，如招行、工行、华泰等） | 各机构官网 / 天池·DataFountain 承接页 | 金融 |
| MLH | majorleaguehacking.com/events | 国际 |
| Devpost | devpost.com | 国际 |
| HackerEarth | hackerearth.com | 国际 |
| Kaggle | kaggle.com（competitions + 关键词 hackathon） | 国际 |
| GitHub | github.com/topics/hackathon | 国际 |

---

## 搜索 Query 模板

```text
# 大厂
"{YYYY} 阿里 天池 大模型 挑战赛 报名"
"{YYYY} 腾讯 云 算法 大赛 报名"
"{YYYY} 华为 软件精英挑战赛 报名"
"{YYYY} 百度 飞桨 黑客松 报名"

# 金融
"{YYYY} 银行 金融科技 大赛 报名"
"{YYYY} 券商 算法 大赛 报名 金融科技"

# 政府/学会
"{YYYY} 世界人工智能大会 WAIC 黑客松 报名"
"{YYYY} 中国人工智能学会 竞赛 报名"
"{YYYY} 地方政府 AI 大赛 创新创业 报名"

# 专业平台
"site:biendata.com {YYYY} 挑战赛"
"site:datafountain.com {YYYY} 金融科技"
"site:tianchi.aliyun.com {YYYY} 大模型"

# 国际
"site:devpost.com hackathon AI {YYYY}"
"site:kaggle.com competitions AI"
"github topics hackathon AI"
```

## 注意事项

- **微信/企鹅号**：用 `weixin.sogou.com` 搜微信文章；企鹅号文章真实域名是 `new.qq.com` / `om.qq.com`，不要把搜索限制在 `html5.qq.com`（那是搜狗网页搜索，非微信）。
- **DoraHacks** 已迁移至 `hackathon.dorahacks.io`，如纳入国际/其他赛事以该域名为准。
- **截止日必须校验**：天池/飞桨/DataFountain 等赛事页可能是动态加载，搜索摘要常缺截止日，务必 WebFetch 官方报名页确认（见 SKILL.md 第二步），切勿凭摘要猜测。
- **T1 每次必抓，T2/T3 按命中与时效补充**；连续多次无产出的信源可临时降权，不必每次穷举。
- **以官方页面日期为准**，媒体转发文章的日期可能有误。
