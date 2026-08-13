"""库存 Agent：检查食材库存并真实扣减（SQLite 持久化）。

升级点（相比 Day14 教学版）：
- 从「内存 dict」升级为「SQLite 数据库」，重启不丢数据
- 真实事务扣减，质检失败/降级时可精确回滚
- 缺货时 LLM 推荐替代菜品（不是冷冰冰的"缺货"）
"""

import time

from agents.common import KitchenState, get_client, log_step, record_token, MODEL
from db import database


def _recommend(unavailable_dish: str) -> str:
    """缺货时，LLM 根据现有库存推荐能做的菜品。"""
    # 找出当前还能做的菜品
    available = [
        d for d in database.list_dishes() if database.check_stock(d)["ok"]
    ]
    if not available:
        return "今天食材都用完了，建议您明天再来～"

    prompt = (
        f"你是餐厅服务员。客人想点「{unavailable_dish}」但缺货了。\n"
        f"当前还能做的菜品：{'、'.join(available)}\n\n"
        f"请用一句话推荐一个替代菜品，语气友好自然，30 字以内，直接输出推荐语。"
    )
    resp = get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    record_token("推荐", resp.usage)
    return resp.choices[0].message.content.strip()


def check_inventory(state: KitchenState) -> KitchenState:
    t0 = time.time()

    if not state["dish"]:
        state["inventory_ok"] = False
        log_step(state, "库存", "跳过：无效订单", t0)
        return state

    result = database.check_stock(state["dish"], state["quantity"])

    if result["ok"]:
        # 真实扣减（事务）
        database.deduct_stock(state["dish"], state["quantity"])
        state["inventory_ok"] = True
        log_step(state, "库存", f"{state['dish']} 食材充足，已扣减库存", t0)
    else:
        missing_desc = "、".join(
            f"{m['item']}(缺{m['need'] - m['have']:.1f})" for m in result["missing"]
        )
        state["inventory_ok"] = False
        log_step(state, "库存", f"缺货：{missing_desc}", t0)
        # 缺货推荐（LLM 兜底，失败则静默）
        try:
            state["recommendation"] = _recommend(state["dish"])
            log_step(state, "推荐", state["recommendation"], t0)
        except Exception:
            state["recommendation"] = ""

    return state
