"""降级 Agent：兜底方案。

当质检连续失败时触发——不是让系统崩溃，而是优雅降级：
1. 回滚已扣减的库存（SQLite 事务）
2. 给出友好提示
3. 记录故障（可观测性）
"""

import time

from agents.common import KitchenState, log_step
from db import database


def fallback(state: KitchenState) -> KitchenState:
    t0 = time.time()

    log_step(state, "降级", "启动兜底方案：回滚库存", t0)

    # 回滚库存（只回滚本单的食材）
    if state["dish"]:
        database.restore_stock(state["dish"], state["quantity"])

    log_step(state, "降级", "库存已恢复，建议客人换一道菜或稍后再试", t0)
    return state


def serve(state: KitchenState) -> KitchenState:
    t0 = time.time()
    log_step(state, "上菜", f"{state['dish']} 请慢用！", t0)
    return state
