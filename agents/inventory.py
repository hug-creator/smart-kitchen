"""库存 Agent：检查食材库存并真实扣减（SQLite 持久化）。

升级点（相比 Day14 教学版）：
- 从「内存 dict」升级为「SQLite 数据库」，重启不丢数据
- 真实事务扣减，质检失败/降级时可精确回滚
"""

import time

from agents.common import KitchenState, log_step
from db import database


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

    return state
