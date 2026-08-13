// === 智能餐厅 · 前端逻辑 ===

const AGENT_ICONS = {
  "接单": "📝",
  "库存": "📦",
  "烹饪": "🍳",
  "质检": "🔍",
  "降级": "⚠️",
  "上菜": "🍽",
  "推荐": "💡",
};

const $ = (id) => document.getElementById(id);

// 切换 Tab
document.querySelectorAll(".sidebar .menu li").forEach((item) => {
  item.addEventListener("click", () => {
    document.querySelectorAll(".sidebar .menu li").forEach((l) => l.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach((t) => t.classList.remove("active"));
    item.classList.add("active");
    const tab = item.dataset.tab;
    $("tab-" + tab).classList.add("active");
    const titles = { order: "实时下单", inventory: "库存管理", history: "订单历史", monitor: "系统监控" };
    $("page-title").textContent = titles[tab];
    if (tab === "inventory") refreshInventory();
    if (tab === "history") refreshHistory();
    if (tab === "monitor") refreshMonitor();
  });
});

// 例子快捷输入
document.querySelectorAll(".example-chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    $("order-input").value = chip.dataset.q;
    $("order-input").focus();
  });
});

// 下单
$("order-btn").addEventListener("click", placeOrder);
$("order-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") placeOrder();
});

async function placeOrder() {
  const input = $("order-input").value.trim();
  if (!input) {
    alert("请输入客人点餐内容");
    return;
  }

  const btn = $("order-btn");
  btn.disabled = true;
  btn.innerHTML = '<span class="loading"></span> 处理中…';

  const resultCard = $("result-card");
  resultCard.style.display = "block";
  $("result-title").textContent = `🍽 订单：${input}`;
  $("result-status").textContent = "处理中";
  $("result-status").className = "card-tag";
  $("timeline").innerHTML = "";
  $("agent-grid").innerHTML = "";
  $("stats-row").innerHTML = "";

  try {
    const resp = await fetch("/api/order", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: input }),
    });

    if (!resp.ok) {
      const err = await resp.json();
      throw new Error(err.error || "请求失败");
    }

    const data = await resp.json();
    renderResult(data);
  } catch (e) {
    $("result-status").textContent = "失败";
    $("result-status").style.background = "#fef0f0";
    $("result-status").style.color = "#f56c6c";
    $("timeline").innerHTML = `<div class="alert-error">❌ ${e.message}</div>`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = "下单";
  }
}

function renderResult(data) {
  // 状态
  const statusEl = $("result-status");
  if (data.status === "served") {
    statusEl.textContent = "✅ 上菜";
    statusEl.style.background = "#f0f9eb";
    statusEl.style.color = "#67c23a";
  } else if (data.status === "fallback") {
    statusEl.textContent = "⚠️ 降级";
    statusEl.style.background = "#fdf6ec";
    statusEl.style.color = "#e6a23c";
  } else if (data.status === "out_of_stock") {
    statusEl.textContent = "❌ 缺货";
    statusEl.style.background = "#fef0f0";
    statusEl.style.color = "#f56c6c";
  } else {
    statusEl.textContent = "❌ 未识别";
    statusEl.style.background = "#fef0f0";
    statusEl.style.color = "#f56c6c";
  }

  // 缺货推荐（醒目展示）
  const timelineEl = $("timeline");
  let recBox = $("recommendation-box");
  if (data.recommendation) {
    if (!recBox) {
      recBox = document.createElement("div");
      recBox.id = "recommendation-box";
      recBox.className = "recommendation-box";
      timelineEl.parentNode.insertBefore(recBox, timelineEl);
    }
    recBox.innerHTML = `💡 <b>推荐替代：</b>${data.recommendation}`;
    recBox.style.display = "block";
  } else if (recBox) {
    recBox.style.display = "none";
  }

  // 时间轴
  const timeline = $("timeline");
  timeline.innerHTML = "";
  for (const entry of data.log) {
    const div = document.createElement("div");
    let cls = "timeline-item";
    let label = entry.message;
    if (entry.message.includes("通过") || entry.message.includes("识别")) cls += " success";
    else if (entry.message.includes("不通过") || entry.message.includes("缺货") || entry.message.includes("兜底")) cls += " error";
    else if (entry.message.includes("退回")) cls += " warning";
    div.className = cls;
    div.innerHTML = `
      <div class="label">${AGENT_ICONS[entry.agent] || "⚙️"} ${entry.agent}：${label}</div>
      <div class="time">${entry.ms}ms</div>
    `;
    timeline.appendChild(div);
  }

  // Agent 卡片网格
  const agentGrid = $("agent-grid");
  const agentSet = new Set();
  data.log.forEach((e) => agentSet.add(e.agent));
  for (const agent of agentSet) {
    const entry = data.log.find((e) => e.agent === agent);
    const card = document.createElement("div");
    let cls = "agent-card";
    if (entry.message.includes("通过") || entry.message.includes("识别")) cls += " success";
    else if (entry.message.includes("不通过") || entry.message.includes("缺货") || entry.message.includes("兜底") || entry.message.includes("失败")) cls += " error";
    card.className = cls;
    card.innerHTML = `
      <div class="icon">${AGENT_ICONS[agent] || "⚙️"}</div>
      <div class="name">${agent}</div>
      <div class="status">${entry.ms}ms</div>
    `;
    agentGrid.appendChild(card);
  }

  // 统计行
  const stats = $("stats-row");
  const total = data.log.reduce((s, e) => s + e.ms, 0);
  const items = [
    { label: "菜品", value: data.dish || "—" },
    { label: "份数", value: data.quantity || "—" },
    { label: "质检分", value: data.qc_score ? data.qc_score : "—" },
    { label: "总耗时", value: `${total}ms` },
  ];
  stats.innerHTML = items.map(
    (i) => `<div class="stat-item"><div class="label">${i.label}</div><div class="value">${i.value}</div></div>`
  ).join("");
}

// ============= 库存管理 =============
async function refreshInventory() {
  const tbody = $("inventory-tbody");
  tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;">加载中…</td></tr>';
  try {
    const resp = await fetch("/api/inventory");
    const data = await resp.json();
    renderInventory(data.items);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="alert-error">${e.message}</div></td></tr>`;
  }
}

function renderInventory(items) {
  const tbody = $("inventory-tbody");
  if (items.length === 0) {
    tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;padding:30px;">暂无数据</td></tr>';
    return;
  }
  tbody.innerHTML = items.map((item) => {
    let statusClass = "stock-ok";
    let statusTag = '<span class="tag tag-green">充足</span>';
    if (item.quantity <= 0) {
      statusClass = "stock-low";
      statusTag = '<span class="tag tag-red">缺货</span>';
    } else if (item.quantity < 2) {
      statusClass = "stock-warning";
      statusTag = '<span class="tag tag-orange">紧张</span>';
    }
    return `
      <tr>
        <td><strong>${item.item}</strong></td>
        <td class="${statusClass}">${item.quantity}</td>
        <td>${statusTag}</td>
        <td><span class="tag tag-gray">${item.threshold}</span></td>
        <td><button class="btn btn-default btn-sm restock-one" data-item="${item.item}">+10 进货</button></td>
      </tr>
    `;
  }).join("");

  // 绑定每行进货按钮
  document.querySelectorAll(".restock-one").forEach((btn) => {
    btn.addEventListener("click", () => restockItem(btn.dataset.item, 10));
  });
}

async function restockItem(item, amount) {
  try {
    const resp = await fetch("/api/inventory/restock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item, amount }),
    });
    if (resp.ok) refreshInventory();
  } catch (e) {
    alert("进货失败：" + e.message);
  }
}

async function restockAll() {
  if (!confirm("确定重置所有食材到初始库存？")) return;
  try {
    const resp = await fetch("/api/inventory/restock", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ item: "all" }),
    });
    if (resp.ok) {
      const data = await resp.json();
      renderInventory(data.items);
    }
  } catch (e) {
    alert("重置失败：" + e.message);
  }
}

$("refresh-inventory").addEventListener("click", refreshInventory);
$("restock-all").addEventListener("click", restockAll);

// ============= 订单历史 =============
async function refreshHistory() {
  const tbody = $("history-tbody");
  tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:30px;">加载中…</td></tr>';
  try {
    const resp = await fetch("/api/orders?limit=20");
    const data = await resp.json();
    renderHistory(data.orders);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8"><div class="alert-error">${e.message}</div></td></tr>`;
  }
}

function renderHistory(orders) {
  const tbody = $("history-tbody");
  if (orders.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:30px;">暂无订单</td></tr>';
    return;
  }
  tbody.innerHTML = orders.map((o) => {
    let statusTag = "";
    if (o.status === "served") statusTag = '<span class="tag tag-green">✓ 上菜</span>';
    else if (o.status === "fallback") statusTag = '<span class="tag tag-orange">⚠ 降级</span>';
    else if (o.status === "out_of_stock") statusTag = '<span class="tag tag-red">✗ 缺货</span>';
    else statusTag = '<span class="tag tag-gray">— 未识别</span>';
    const score = o.qc_score ?? "—";
    let scoreClass = "";
    if (o.qc_score >= 7) scoreClass = "score-high";
    else if (o.qc_score >= 6) scoreClass = "score-mid";
    else if (o.qc_score) scoreClass = "score-low";
    return `
      <tr>
        <td>#${o.id}</td>
        <td>${o.user_input}</td>
        <td><strong>${o.dish}</strong></td>
        <td>${o.quantity}</td>
        <td class="${scoreClass}">${score}</td>
        <td>${o.qc_feedback || "—"}</td>
        <td>${statusTag}</td>
        <td>${o.created_at}</td>
      </tr>
    `;
  }).join("");
}

$("refresh-history").addEventListener("click", refreshHistory);

// ============= 系统监控 =============
async function refreshMonitor() {
  try {
    const resp = await fetch("/api/stats");
    const data = await resp.json();
    $("stat-total").textContent = data.total;
    $("stat-success").textContent = data.success;
    $("stat-rate").textContent = data.success_rate + "%";
    $("stat-score").textContent = data.avg_score;

    // Token 统计
    const usage = data.usage || {};
    $("stat-calls").textContent = usage.total_calls ?? 0;
    $("stat-tokens").textContent = usage.total_tokens ?? 0;

    const usageTbody = $("usage-tbody");
    const byAgent = usage.by_agent || [];
    if (byAgent.length === 0) {
      usageTbody.innerHTML = '<tr><td colspan="3" style="text-align:center;padding:20px;color:#909399;">暂无 LLM 调用记录</td></tr>';
    } else {
      usageTbody.innerHTML = byAgent.map((a) => `
        <tr>
          <td><strong>${a.agent}</strong></td>
          <td>${a.calls} 次</td>
          <td>${a.tokens} tokens</td>
        </tr>
      `).join("");
    }
  } catch (e) {
    console.error(e);
  }
}

$("refresh-monitor").addEventListener("click", refreshMonitor);

// 默认加载监控
refreshMonitor();
