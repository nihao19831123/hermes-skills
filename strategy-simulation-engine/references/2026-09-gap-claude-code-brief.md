# 2026-09 推演方案补差:盘点结果 + claude code 任务书模板

项目根:C:\Users\wufeng\Documents\青岛市人口和就诊情况收集\(WSL 下 /mnt/c/Users/wufeng/Documents/青岛市人口和就诊情况收集/)

## 《推演方案初版.txt》差距盘点(实测 2026-09)

需求文档是"外部评审稿",写作时推演层尚缺;接单时先盘点现状,发现必做 4 项已大部实现:

| 文档要求 | 现状 | 差距 |
|---|---|---|
| 优化1 战略推演引擎 | ✅ engine.py simulate 三类动作×1-5年×134街道 | 无 |
| 优化2 A/B/C 比较 | ⚠️ /api/strategy/compare + 前端三卡 | 前端"综合建议"写死文案,非 AI 推荐 |
| 优化3 资源容量模型 | ⚠️ dept_capacity/hospital_params(科室医生/号源、全院床位64%/手术30) | 科室级床位/手术量/住院日无数据,不做 |
| 优化4 AI 战略建议 | ⚠️ 规则文本 source:"rule" | 推演/对比建议未接 DeepSeek(巡检 ai_explainer 已接) |
| 数据库 3 表 | ⚠️ strategy_config/strategy_result 有 | ai_strategy_advice 独立表缺失(建议现存 strategy_result.ai_advice 列) |
| 优化5 竞争医院影响 | ❌ | 文档标"有时间再做",本次不做 |
| ❌ 项(复杂预测/仿真/地图增强) | — | 明确不做 |

后端文件清单(全部很小,~860 行):backend/app.py(210)、ai_detector.py(120)、ai_attribution.py(54)、ai_explainer.py(89,DeepSeek 范本)、strategy_engine/engine.py(236)、capacity_profile.py(155);前端单文件 青岛街道人口热力图.html(951 行,内嵌 DATA JSON,推演工作台约 740-946 行);hospital.db 4 表。

## 委托 claude code 做增量开发的任务书模板(实测有效)

用户指令"按照《文档X》调用 claude code 实现Y"时:先自查现状(读代码/查表/grep 前端)→ 差距清单 → 任务书写到 /tmp,再
`claude -p "$(cat /tmp/task.md)" --allowedTools "Read,Edit,Write,Bash" --max-turns 40 > /tmp/out.log 2>&1`
后台(notify_on_complete=true)跑,完成后自己 curl/浏览器复验。任务书结构(照抄要点):

1. **第一步先读**(绝对路径列出需求文档 + 相关代码文件 + 指明哪个文件是"调用范例")
2. **现状(已实现,不要重做)** —— 明确列出,防止 claude code 整段重写能跑的代码
3. **差距(本次要实现)** —— 逐条:新模块函数签名、接口返回结构变化、前端改动定位(行号/关键词)
4. **硬性约束**:绝不删除/重建 hospital.db、不修改数据 JSON、不新增第三方依赖(只标准库)、key 只从环境变量/~/.hermes/.env 读禁止写进代码、不改现有 API 字段(前端兼容)、禁止 git 操作、禁止删现有文件
5. **完成后自测**(给出确切命令:py_compile、TestClient 冒烟、key 置空验证回退路径)
6. 中文总结

用户批准模式:CLI 上逐条命令弹审批,含 rm/rmdir(即使删自己刚建的空目录)会被拒 → 任何命令不带删除步骤;批量安装/改动前先贴"待执行命令清单"等批准,批准后一次跑完。

## 本会话实测要点
- engine.py __main__ 自测是现成冒烟(心内科 20%×3年:2028 累计+门诊5844/床位率65.1%/号源率78.5%)
- DeepSeek key 在 ~/.hermes/.env(grep DEEPSEEK_API_KEY 确认);app.py/ai_explainer.py 用 urllib 直连,不走代理设置——国内 api.deepseek.com 可达
- 前端改推荐区:找写死文案"💡 综合建议"字符串定位即可;接口 recommendation 缺失时保留原文案
