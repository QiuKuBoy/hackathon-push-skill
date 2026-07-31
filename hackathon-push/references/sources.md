# 信源清单与抓取优先级

> 所有年份相关查询与文案使用**当前年份**（由系统时间确定，如 2026），不要写死具体年份。搜索 query 中的年份用占位符 `{YYYY}`。

## T1 信源（每次必抓）

| 信源 | URL | 备注 |
|------|-----|------|
| 企鹅号/搜狗微信 | so.html5.qq.com | 搜索 `黑客松 报名`，国内赛事覆盖最全 |
| 飞桨 AI Studio | aistudio.baidu.com/projectoverview/public/1 | 开源挑战赛/黑客松 |
| 天池 | tianchi.aliyun.com | 阿里算法/开发者大赛 |
| DoraHacks | dorahacks.cn / dorahacks.com | 国内黑客松 + Hackathon |
| MLH | majorleaguehacking.com/events | 线上赛中国可参加，每周更新 |
| CSDN AI 赛事通 | blog.csdn.net（搜「AI 赛事通」）| 月度赛事汇总博客，可参考格式但内容可能延迟 |

## T2 信源（补充抓）

| 信源 | URL | 备注 |
|------|-----|------|
| 阿里云开发者社区 | developer.aliyun.com | 阿里系赛事 |
| 腾讯云开发者社区 | cloud.tencent.com/developer | 腾讯系赛事 |
| 火山引擎开发者社区 | developer.volcengine.com | 字节系赛事 |
| 百度飞桨社区 | aistudio.baidu.com | 飞桨系挑战赛 |
| 美团技术团队 | tech.meituan.com | 美团开放平台 |
| 京东开发者社区 | developer.jd.com | 京东算法赛 |
| 蚂蚁技术社区 | tech.antfin.com | 蚂蚁开发者 |
| 智谱 AI | open.bigmodel.cn | 智谱 GLM 相关活动 |
| MiniMax | minimaxi.com | AI 应用赛 |
| 科大讯飞开放平台 | xfyun.cn | 语音/认知 AI 赛 |
| 高校计算机能力挑战赛 | ncccu.org.cn | 高校榜单赛事 |

## T3 信源（兜底）

| 信源 | URL | 备注 |
|------|-----|------|
| 36kr | 36kr.com | 科技创业赛事报道 |
| 极客公园 | geekpark.net | AI 产品/创业赛事 |
| InfoQ | infoq.cn | 开发者技术大会/赛事 |
| 新榜 | newrank.cn | 微信公众号热榜（需登录）|
| CSDN 赛事博客 | blog.csdn.net 搜索「AI 赛事通」| 赛事周报汇总 |

## 搜索 Query 模板

```text
# 通用搜索（{YYYY} 替换为当前年份）
"{YYYY} 黑客松 报名 截止" + "AI"
"{YYYY} 最近一个月 AI 开发者大赛 报名"

# 定向搜索
"site:html5.qq.com 黑客松 报名 {YYYY}"
"site:blog.csdn.net {YYYY} 黑客松 报名"
"{YYYY} 黑客松 大学生 AI 算法 报名"

# 行业搜索
"{YYYY} 阿里 天池 挑战赛 报名"
"{YYYY} 腾讯 广告 算法 大赛 报名"
"{YYYY} 百度 飞桨 黑客松 报名"
```

## 注意事项

- **DoraHacks / 天池** 页面在国内网络可能超时，优先用 `WebSearch` 替代直接 `WebFetch`。
- **搜狗微信搜索** 返回企鹅号文章，内容最完整，是国内赛事信息的主要来源。
- **MLH** 以线上赛为主，中国开发者可自由参加，关注「Global Hack Week」系列。
- **CSDN 赛事通博客** 会定期发月度汇总，可参考格式但内容可能有延迟，以官方页面为准。
