# 2026-09 第三/四轮:情景分析 + 决策报告导出 + 竞争压力指数 CPI

青岛医院推演平台实测沉淀(比赛增强轮次)。三个能力都是"推演平台通用扩展",任何同类平台可复用。

## ③ 情景/敏感性分析(化解"精确数字不可信"质疑)

- 概念:同一方案跑 保守/中性/乐观 三情景,给区间结论而非单点数字。三档 = 战略效果**兑现程度** 75%/100%/125%。
- 后端:POST /api/strategy/scenario,body=单方案 params(无 name/不写库):
  - 以 params.magnitude 为中性档;保守 ×0.75、乐观 ×1.25;各档 clamp 回引擎允许域(0.05-0.5)
  - 三档分别 simulate,返回 `{params, scenarios:[{name,magnitude,summary,years}×3], conclusion:{text, source:'rule'}}`
  - conclusion 由规则生成(不调 DeepSeek,秒回):"【动作 幅度%/年限】期末累计新增门诊预计 min~max 人次(中性 mid),新增住院 a~b(中性 c);期末床位使用率区间 X%~Y%(中性 Z%),三情景均低于 90% 警戒线(或:乐观情景将突破 90%,建议同步扩容床位)"——从三档 summary 取 min/max/中性,前端标注"兑现程度 75%/100%/125% 假设"
- 前端:推演工作台"⚖️ 情景分析"按钮(用当前表单参数)→ 三情景摘要卡 + ECharts 三系列折线(X=年份,累计新增门诊)+ 区间结论卡
- 实测锚点(心内科 20%/3年):累计门诊 8,766 < 11,688 < 14,610 严格递增;床位率 64.8/65.1/65.4

## ② 决策报告一键导出(纯 HTML,答辩材料秒出)

- 目标:单方案/ABC 对比 → "领导版决策报告",浏览器打印为 PDF。**报告内容必须含"数据口径与模型说明"段**——这是答辩"数据哪来的"的标准答案页。
- 后端:新建 report_html.py(纯标准库,无第三方依赖、无外部资源、内嵌 CSS、A4 打印风、页脚"本报告由平台自动生成"):
  - `build_report(kind, payload, advice) → HTML 字符串`;kind='single' 七章:封面(平台名/方案名/动作/时间)→ 方案参数 → 结果摘要(含 HRI 变化/专科患者增量)→ 分年结果表 → 重点街道 TOP8 → 风险提示 → AI 战略建议(标注 deepseek/rule)→ 数据口径与模型说明(人口=七普×WorldPop×区校准;就诊=辐射模型模拟;容量=院内真实参数:床位800/门诊55万/住院2.6万/号源13759;模拟数据仅用于决策实验演示)
  - kind='compare':封面 → 对比方案列表 → 结果对比表 → AI 综合推荐(winner+reasons+来源)→ 各方案 AI 建议 → 口径说明
  - 陷阱:html.escape() 不接受数字参数(先 str() 强转);空条目先过滤再取值
- 接口:POST /api/report/generate {kind, name, params 或完整 result, ai_advice} → {html}
  - 前端能传完整 result 就直接排版(**不二次 simulate**);只传 params 后端 simulate 补齐;ai_advice 缺失用规则兜底;全程零网络调用,实测 0.00s
- 前端:单方案结果卡 / ABC 对比区 / 历史方案详情 三处"📄 导出决策报告"按钮;openReport 用 window.open + document.write,被弹窗拦截时降级 Blob 下载 .html;提示 Ctrl+P 存 PDF

## 🏥 竞争压力指数 CPI(补"竞争环境"短板;让地图上的医院会说话)

- 数据:heatmap_data.json 的 hospitals 25 家**自带 grade 字段**(三甲15/二甲9/三乙1,无需名称推断);本院 is_main(三乙)。竞争名单 = 除本院外三级及以上(16 家)。
- 公式(competition.py 模块顶部常量可调,代码注释写明推导):
  - 距离劣势分(权重 0.6)= `100 × max(0, (d_self − d_comp)/d_self)`——"截流劣势比",本院更近时归零 ⇒ **CPI≥50 必含截流**,口径可辩护
  - 三甲密度分(权重 0.4)= 10km 内每家三甲 +25、10-15km 每家 +5,封顶 100
  - 15km 内无三甲 → CPI 封顶 25(远郊取低值)
  - 分级:低(<25)/中(25-49)/高(50-74)/极高(≥75)
- 接口:GET /api/competition → {hospitals(16家含本院), streets(134街道:cpi/level/d_self/d_comp/nearest_name/nearest_level), summary(分级计数+极高TOP10)}
- 校准样本(答辩素材):市北合肥路 89 极高(齐鲁 1.4km vs 本院 7.7km);李沧湘潭路 70 高 / 楼山 61(中心医院北部院区 1.5-1.8km < 本院 4.6km = 真实截流);城阳街道 12 低;浮山路 44 中(齐鲁 4.5km 略近于本院 4.8km);远郊东阁 6/水集 2
- AI 链路注入(**只加 competition 键,旧字段值级零 diff**):
  - ai_attribution.attribute() 返回 + `competition:{cpi, level, nearest_name, nearest_level, nearest_dist}`
  - ai_explainer:规则模板高/极高时补"该街道 X km 处有{nearest}({level}),竞争截流风险高"行;DeepSeek 系统提示词加竞争归因要求,user payload 显式带 competition
  - ai_advisor(战略建议层):高竞争压力街道 actions 优先 alliance,note 引用最近竞争医院
- 前端:指标切换组新增"🏥 竞争压力"图层(四级色阶 青绿→金黄→橙→红紫 + 图例 + hover 浮层显示最近竞争医院);懒加载 compMap(切到才 fetch /api/competition)
- 复用:距离口径与 engine.dist_km 一致(dlat×111, dlng×89.6)

## 多轮 claude code 委托的调度纪律(同批文件必须串行)

- 每轮一个独立后台 print-mode 任务;轮与轮之间**必须等上一轮完成通知**再开下一轮——多轮都改 app.py/同一 HTML,并行会互相覆盖
- 中途用户插入新需求:先写好下一轮任务书(/tmp/*.md)备着,完成通知一到立即启动;可先做只读侦察(数据字段/口径)不占文件
- 每轮完成后:kill 旧服务进程(跑的是旧代码!)→ 重启 → 只读验证 → 浏览器实测 → 一次性汇报
- 功能拆轮按"获奖杠杆"排序,用户会直接说"②③ 这个需要做"圈范围——按编号执行,不越界做文档外功能
