"""智能餐厅多智能体系统 —— Flask 后端。

技术栈：LangGraph + Flask + SQLite + Element UI 风格前端。
入口：python main.py  →  浏览器打开 http://127.0.0.1:5000
"""

import os
import re
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from agents.common import KitchenState
from agents.accept_order import accept_order
from agents.inventory import check_inventory
from agents.cook import cook
from agents.quality_check import quality_check
from agents.fallback import fallback, serve
from db import database
from langgraph.graph import END, START, StateGraph


# ═══════════════════════════════════════════════════════════
# LangGraph 编排
# ═══════════════════════════════════════════════════════════
def judge_after_order(state):
    return "inventory" if state["dish"] else "end"


def judge_after_inventory(state):
    return "cook" if state["inventory_ok"] else "end"


def judge_after_qc(state):
    if state["qc_pass"]:
        return "serve"
    if state.get("fallback"):
        return "fallback"
    return "cook"


def build_graph():
    g = StateGraph(KitchenState)
    g.add_node("accept_order", accept_order)
    g.add_node("check_inventory", check_inventory)
    g.add_node("cook", cook)
    g.add_node("quality_check", quality_check)
    g.add_node("fallback", fallback)
    g.add_node("serve", serve)
    g.add_edge(START, "accept_order")
    g.add_conditional_edges("accept_order", judge_after_order, {"inventory": "check_inventory", "end": END})
    g.add_conditional_edges("check_inventory", judge_after_inventory, {"cook": "cook", "end": END})
    g.add_edge("cook", "quality_check")
    g.add_conditional_edges("quality_check", judge_after_qc, {"serve": "serve", "fallback": "fallback", "cook": "cook"})
    g.add_edge("fallback", END)
    g.add_edge("serve", END)
    return g.compile()


app = build_graph()


# ═══════════════════════════════════════════════════════════
# 格式化日志（前端可解析）
# ═══════════════════════════════════════════════════════════
LOG_PATTERN = re.compile(r"\[(?P<agent>[^\]]+)\] (?P<message>.+?) \((?P<ms>\d+)ms\)")


def parse_log(raw_log: list[str]) -> list[dict]:
    """解析原始日志：[接单] 识别：蛋炒饭 × 1 (2941ms) → {agent, message, ms}"""
    parsed = []
    for line in raw_log:
        m = LOG_PATTERN.match(line)
        if m:
            parsed.append({
                "agent": m.group("agent"),
                "message": m.group("message"),
                "ms": int(m.group("ms")),
            })
        else:
            parsed.append({"agent": "系统", "message": line, "ms": 0})
    return parsed


# ═══════════════════════════════════════════════════════════
# Flask 应用
# ═══════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

web_app = Flask(__name__, static_folder=str(FRONTEND_DIR / "static"))
CORS(web_app)

# 模块级初始化数据库（gunicorn 部署时 import main 会执行到这里）
database.init_db()


@web_app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR / "templates", "index.html")


@web_app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(FRONTEND_DIR / "static", filename)


@web_app.route("/api/order", methods=["POST"])
def api_order():
    """点餐 API：接收用户输入，运行 4 Agent，返回结构化结果。"""
    data = request.get_json() or {}
    user_input = data.get("user_input", "").strip()
    if not user_input:
        return jsonify({"error": "请输入点餐内容"}), 400

    result = app.invoke({
        "user_input": user_input,
        "dish": "", "quantity": 0,
        "inventory_ok": False,
        "cook_result": "",
        "qc_score": 0, "qc_feedback": "",
        "qc_pass": False, "qc_retries": 0, "fallback": False,
        "recommendation": "",
        "log": [], "timestamps": {},
    })

    # 推断最终状态
    status = "unknown"
    if not result["dish"]:
        status = "未识别"
    elif not result["inventory_ok"]:
        status = "out_of_stock"
    elif result.get("fallback"):
        status = "fallback"
    elif result["qc_pass"]:
        status = "served"

    # 保存订单
    database.save_order(
        user_input=user_input,
        dish=result["dish"] or "未识别",
        quantity=result["quantity"] or 0,
        qc_score=result["qc_score"],
        qc_feedback=result["qc_feedback"],
        status=status,
    )

    return jsonify({
        "status": status,
        "dish": result["dish"],
        "quantity": result["quantity"],
        "qc_score": result["qc_score"],
        "qc_feedback": result["qc_feedback"],
        "recommendation": result.get("recommendation", ""),
        "log": parse_log(result["log"]),
        "total_ms": sum(result["timestamps"].values()),
    })


@web_app.route("/api/inventory")
def api_inventory():
    """库存查询。"""
    stock = database.get_all_stock()
    items = [
        {"item": k, "quantity": v, "threshold": 2}
        for k, v in sorted(stock.items())
    ]
    return jsonify({"items": items})


@web_app.route("/api/inventory/restock", methods=["POST"])
def api_inventory_restock():
    """补货：item="all" 一键补货；item=具体食材 + amount 增加。"""
    data = request.get_json() or {}
    item = (data.get("item") or "").strip()
    amount = float(data.get("amount", 0))

    if item == "all":
        database.reset_stock()
    elif item and amount > 0:
        database.increase_stock(item, amount)
    else:
        return jsonify({"error": "请提供 item 和 amount"}), 400

    stock = database.get_all_stock()
    items = [
        {"item": k, "quantity": v, "threshold": 2}
        for k, v in sorted(stock.items())
    ]
    return jsonify({"items": items, "ok": True})


@web_app.route("/api/orders")
def api_orders():
    """订单历史。"""
    limit = int(request.args.get("limit", 20))
    return jsonify({"orders": database.list_orders(limit)})


@web_app.route("/api/stats")
def api_stats():
    """系统统计：订单统计 + Token 消耗。"""
    stats = database.order_stats()
    usage = database.get_usage_stats()
    stats["usage"] = usage
    return jsonify(stats)


if __name__ == "__main__":
    database.init_db()
    port = int(os.environ.get("PORT", 5000))
    print("🍳 智能餐厅多智能体系统启动")
    print(f"📍 浏览器打开: http://127.0.0.1:{port}", flush=True)
    web_app.run(host="0.0.0.0", port=port, debug=False)
