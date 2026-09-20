# 2026-09 第二轮:推演方案 4 项结构性缺口(claude code 任务书与侦察)

背景:第一轮只补了"AI 建议 DeepSeek 化"(strategy_advisor.py / recommendation / ai_strategy_advice 表),用户判定"claude code 并没有按照《推演方案初版》进行修改"。原因:文档明示的结构性功能点未落地。用户经 clarify 选定"补齐全部 4 项缺口"。

## 用户选定范围(4 项)
1. 街道级选区:影响区域选到某区 → 街道多选 chips → streets:[街道名...] 传 run/compare(engine 已支持 streets 参数,空=全域;SKILL.md 记有 selStreets={name:1} 机制,任务是确保真实可用并全链路贯通,别重做已有 UI)
2. 输出指标:HRI 变化 + 专科患者增量(优化1/2 的输出列"患者人数/HRI/辐射半径/专科患者/资源压力"中的 HRI、专科患者两项)
3. 医院资源容量画像页(优化3):后端 GET /api/hospital/departments + 前端画像面板
4. AI 战略助手联动(优化4):巡检事件 → 判断+建议动作(专科提升/医联体/扩容)→ 点击预填推演工作台

## 数据侦察结论(写任务书前实测,2026-09)
- backend/heatmap_data.json 顶层键:years/population/discharge/opd/coords/street_geo/district_geo/hospitals/departments/diseases_data/ai/quadrant/radius/inspection。**无独立街道 hri 键**
- 前端地图有街道级"HRI 辐射指数"图层(2025 最高:香港中路街道 1.674)——口径公式在 HTML 的 JS 中。后端要输出 HRI 变化须从前端 JS 反查口径,同口径实现 hri_street()/区域聚合;若无公式(纯内嵌表)则退用"就诊渗透率"口径并在汇报中说明
- 前端 HTML 169 行附近内嵌 2MB+ DATA 巨行:Read 工具会拒(>100K),任务书必须写明"严禁 Read 整读 html/heatmap_data.json,用 grep -n/sed -n '起,止p' 分段"
- dept_capacity 表 106 行:dept_name/big_dept/doctors/chief_doctors/associate_chief/attending/weekly_numsource/numsource_fees/numsource_weekdays。含特殊行(低保老人义齿安装 号源633、健康管理中心 528)。科室级床位/手术量/平均住院日**无数据源,不编造不展示**
- hospital_params:beds 800/bed_usage_rate 0.64/annual_opd 550000/annual_ipd 26000/surgery_per_day 30/avg_wait_min 5/radius80_km 15.1

## 任务书硬约束(与第一轮相同)
不删/重建/ALTER hospital.db(只 CREATE TABLE IF NOT EXISTS);不新增第三方依赖(标准库 urllib);DeepSeek key 只从 env/~/.hermes/.env 读;禁止 git、禁止删文件(只允许新增 backend/ai_advisor.py 等);UTF-8 中文注释;旧字段数值与结构不变(仅新增字段),前端旧逻辑不破;自测含 happy path + 无 key 回退,报告改动行号区间。

## 验证纪律(用户在 2026-09 实测表现)
- curl POST /api/strategy/run(会 INSERT 到 strategy_config/result/advice)被用户**连续拒绝两次**(第二次同命令只留只读调用也被拒——命令含 write 痕迹即整体拒绝,分开提交只读命令才通过)
- 通过路径:GET capacity/list、POST /api/strategy/compare(纯计算不落库)、python 直调 engine.simulate + strategy_advisor.advise_single/advise_compare(内存,monkeypatch _load_key=lambda:"" 测 rule 回退)
- 浏览器实测:打开推演工作台 → 点"A/B/C 对比"按钮(#stratCompare,不写库)验证卡片+AI 推荐;不要替用户点"运行推演"(写库属预期功能,留给用户)
- claude code 冒烟自测插的行必须自行清理;验证后 sqlite3 检查行数回到测试前

## 第二轮任务书文件位置
/tmp/strategy_task2.md(本会话);执行:claude -p "$(cat ...)" --allowedTools "Read,Edit,Write,Bash" --max-turns 60,后台+notify,输出 /tmp/claude_strategy2_out.log
