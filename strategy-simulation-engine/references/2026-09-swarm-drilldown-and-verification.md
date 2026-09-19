# 蜂群原型：单街道钻取 + 浏览器客观验收纪律（2026-09-19，第 5 轮）

原型路径：`/root/agent-swarm-proto/index.html`（单文件自包含；Windows 交付 `Documents\智能体蜂群原型-v0.5.html`）。
母文档：`references/2026-09-swarm-visualization-prototype.md`（前 4 轮：数据抽取、数据锚定基线、六视图、6 个真 bug）。

## 一、用户这一轮的原话与判定
- "这个图形比之前确实是直观了，但是**看不出来每个街道的选择情况**" → 加聚合排行视图（⑦，见 SKILL.md）
- 选 A → "**单街道钻取**：点 ⑦ 里某一行 → 整屏放大这个街道的个体（按科室/偏好分组）"

规律：**用户否的从来不是"点太小"这一类表面问题，而是"信息读不出来"**。解决方案永远是"加一个聚合/钻取层级"，而不是继续调点半径或配色。每加一层都要能用一句话说清"这一层回答什么问题"。

## 二、钻取实现配方（可直接照抄的结构）

状态：
```js
S = { drillSi:null, drillBy:'dept', rowHits:null, backHit:null }
```

列表态绘制时记录行热区（每页 12 行）：
```js
S.rowHits=[];
page.forEach((r,n)=>{ const y=26+n*25;
  S.rowHits.push({y0:y-5, y1:y+21, si:r.si}); });   // 行高 25px
```

钻进/退出（统一入口，负责控件显隐 + 重绘）：
```js
function setDrill(si){
  S.drillSi=si; S.sel=-1; drawer.classList.remove('open');
  const on = si!==null;
  lbDrill.style.display = segDrill.style.display = on?'':'none';
  const showList = !on && S.view==='streets';
  segSort.style.display = lbSort.style.display = pgPrev.style.display = pgNext.style.display = showList?'':'none';
  draw();
}
```

点击分发（**必须先判返回按钮，再判个体；否则返回热区会被点阵命中抢走**）：
```js
cv.addEventListener('click', e=>{
  const mx=e.clientX-r.left, my=e.clientY-r.top;
  if(S.view==='streets'){
    if(S.drillSi!==null){
      const b=S.backHit;
      if(b && mx>=b.x0 && mx<=b.x1 && my>=b.y0 && my<=b.y1){ setDrill(null); return }
      const i=nearest(mx,my); if(i>=0){ showAgent(i); return }
    }else{
      const hit=(S.rowHits||[]).find(h=>my>=h.y0&&my<=h.y1);
      if(hit){ setDrill(hit.si); return }
    }
  }
  ...
});
```

命中必须限定范围（否则会选中"其他视图遗留坐标"的隐藏个体——这是分组/钻取布局的通用坑）：
```js
function nearest(mx,my){
  const drill = S.view==='streets' && S.drillSi!==null;
  for(let i=0;i<S.agents.length;i++){
    if(drill && S.agents[i].si!==S.drillSi) continue;   // ← 关键
    ...}
}
// 整屏重排前先把未显示的个体移出命中范围：
S.agents.forEach(a=>{a.x=-999;a.y=-999});
```

钻取分组（三种，同一份 idxs 三次投影）：
```js
let groups=[];
if(S.drillBy==='state'){ [[1,'选择我院'],[2,'选择竞争医院'],[0,'未就诊 / 其他']].forEach(g=>
  groups.push({label:g[1], list:idxs.filter(i=>S.choices[i][S.year]===g[0])})); }
else if(S.drillBy==='sens'){ const band=a=>a.distSens<0.95?0:(a.distSens<1.3?1:2);
  [['敏感度 低',0],['敏感度 中',1],['敏感度 高',2]].forEach(g=>
    groups.push({label:g[0], list:idxs.filter(i=>band(S.agents[i])===g[1])})); }
else { const m=new Map(); idxs.forEach(i=>{const d=S.agents[i].dept; (m.get(d)||m.set(d,[]).get(d)).push(i)});
  groups=[...m.entries()].sort((a,b)=>b[1].length-a[1].length).map(([d,l])=>({label:D.depts[d],list:l})); }
groups=groups.filter(g=>g.list.length>0);
```
每卡片：标题（标签 + 人数）→ 该组构成条 `stackBar()` → 组内点阵（`cell=min(boxW/gcols, boxH/grows)`，`r=clamp(cell*0.42,1.2,R()*1.15)`）。

## 三、客观验收手段（本次新增/复用的四件套）

1. **每视图绘制元素计数钩子**：`dot()` 第一行 `window.__dots=(window.__dots||0)+1; window.__dotsBy[ch]++`。测定值：
   - 人群迁徙 / 地图波前 = 全部 11,884 ｜ 双蜂群对比 = 23,768（两屏）｜ 街道阵列 = 1,707（前 30 街道）
   - 钻取 = 该街道个体数（63 === 63，**一票否决级的对齐**）
   - 注意：分带明细 / 迁移流走 `ctx.arc` 直绘、不走 `dot()`，钩子读数为 0 属**假阴性**，要用 `pixelStats()` 交叉确认
2. **画布像素分类统计** `pixelStats()`：按色带数绿/橙/灰像素，用于验证"这一层到底画出来了没有"。本次靠它抓出"地图构成条被点盖住"（增量仅 244 px）。
3. **真实 UI 路径**：`browser_click` 点按钮、`dispatchEvent(new MouseEvent('mousemove',{clientX,clientY,bubbles:true}))` 验 tooltip、`.click()` 验分页/排序、合成 `click` 验行钻取与返回。**只调内部函数会漏掉写在事件处理器里的逻辑**（本次排序/分页控件显隐就是漏的）。
4. **性能预算实测**：`for(i<5) draw()` 取平均 → 1.2 万点 2.8ms、2.5 万点 5.1ms（60fps 预算 16.7ms）。汇报时给数值，不说"很流畅"。

## 四、本轮新增的两个通用坑（已回写 SKILL.md）
1. **切换视图/分组后必须立即 `draw()`**：只靠 rAF 循环的下一帧，会让"绘制时写入"的状态（rowHits/backHit/缓存）短暂为空 → 手快的用户点不到。
2. **长链 console 脚本的失败先怀疑测试自身**：本次"点返回后排序控件未恢复"是假报（脚本跑到后半段 `S.view` 已漂移成 map，控件本就该隐藏）。关键交互要在**刷新后的干净页面**单独复验（`?v=N`），并把假报如实说明，避免把好功能改坏。
