"""SQLite 库存持久化层。

职责：管理食材库存 + 菜品-食材映射。
- 每次下单真实扣减库存
- 质检失败/降级时真实回滚
- 库存不足时给出精确缺口

设计：单例数据库连接，线程安全（每线程独立连接）。
"""

import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "kitchen.db"

# 菜品 → 所需食材（每份用量）
MENU = {
    "番茄炒蛋": {"鸡蛋": 2, "番茄": 2, "油": 0.1, "盐": 0.05},
    "蛋炒饭":   {"鸡蛋": 2, "米饭": 300, "油": 0.1, "盐": 0.05},
    "煎牛排":   {"牛排": 1, "油": 0.1, "黑胡椒": 0.02, "盐": 0.05},
    "蔬菜沙拉": {"生菜": 200, "番茄": 1, "沙拉酱": 20},
}

# 初始库存
INITIAL_STOCK = {
    "鸡蛋": 6, "番茄": 4, "油": 2.0, "盐": 2.0,
    "米饭": 1000, "牛排": 2, "黑胡椒": 0.5,
    "生菜": 400, "沙拉酱": 100,
}

_local = threading.local()


def get_conn() -> sqlite3.Connection:
    """获取当前线程的数据库连接（线程安全）。"""
    if not hasattr(_local, "conn"):
        _local.conn = sqlite3.connect(DB_PATH)
        _local.conn.row_factory = sqlite3.Row
    return _local.conn


def init_db() -> None:
    """初始化数据库（幂等，可重复调用）。"""
    conn = get_conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            item TEXT PRIMARY KEY,
            quantity REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_input TEXT NOT NULL,
            dish TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            qc_score INTEGER,
            qc_feedback TEXT,
            status TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # 首次初始化时填充默认库存
    count = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
    if count == 0:
        conn.executemany(
            "INSERT INTO inventory (item, quantity) VALUES (?, ?)",
            INITIAL_STOCK.items(),
        )
    conn.commit()


def save_order(user_input: str, dish: str, quantity: int,
               qc_score: int, qc_feedback: str, status: str) -> int:
    """保存订单记录，返回订单 ID。"""
    conn = get_conn()
    cur = conn.execute(
        """INSERT INTO orders (user_input, dish, quantity, qc_score, qc_feedback, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (user_input, dish, quantity, qc_score, qc_feedback, status),
    )
    conn.commit()
    return cur.lastrowid


def list_orders(limit: int = 20) -> list[dict]:
    """查询最近订单。"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM orders ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def order_stats() -> dict:
    """订单统计：总数、成功率、平均质检分。"""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    success = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE status='served'"
    ).fetchone()[0]
    avg_score = conn.execute(
        "SELECT AVG(qc_score) FROM orders WHERE qc_score IS NOT NULL"
    ).fetchone()[0] or 0
    return {
        "total": total,
        "success": success,
        "success_rate": round(success / total * 100, 1) if total else 0,
        "avg_score": round(avg_score, 1),
    }


def check_stock(dish: str, quantity: int = 1) -> dict:
    """检查某菜品按份数是否库存充足。

    返回: {"ok": bool, "missing": [{"item": str, "need": float, "have": float}]}
    """
    conn = get_conn()
    recipe = MENU.get(dish)
    if not recipe:
        return {"ok": False, "missing": [{"item": "菜品", "need": dish, "have": "未知"}]}

    missing = []
    for item, per_unit in recipe.items():
        need = per_unit * quantity
        row = conn.execute(
            "SELECT quantity FROM inventory WHERE item = ?", (item,)
        ).fetchone()
        have = row["quantity"] if row else 0
        if have < need:
            missing.append({"item": item, "need": need, "have": have})

    return {"ok": len(missing) == 0, "missing": missing}


def deduct_stock(dish: str, quantity: int = 1) -> None:
    """真实扣减库存（事务）。"""
    conn = get_conn()
    recipe = MENU[dish]
    try:
        for item, per_unit in recipe.items():
            conn.execute(
                "UPDATE inventory SET quantity = quantity - ? WHERE item = ?",
                (per_unit * quantity, item),
            )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def restore_stock(dish: str, quantity: int = 1) -> None:
    """回滚库存（质检失败/降级时调用）。"""
    conn = get_conn()
    recipe = MENU[dish]
    for item, per_unit in recipe.items():
        conn.execute(
            "UPDATE inventory SET quantity = quantity + ? WHERE item = ?",
            (per_unit * quantity, item),
        )
    conn.commit()


def get_all_stock() -> dict:
    """读取全量库存快照（用于界面展示）。"""
    conn = get_conn()
    rows = conn.execute("SELECT item, quantity FROM inventory ORDER BY item").fetchall()
    return {r["item"]: r["quantity"] for r in rows}


def list_dishes() -> list[str]:
    """返回所有可售菜品名。"""
    return list(MENU.keys())
