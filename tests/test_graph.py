"""图结构与条件判断测试：LangGraph 编排逻辑。"""

from main import (
    build_graph,
    judge_after_order,
    judge_after_inventory,
    judge_after_qc,
)


class TestJudges:
    """条件判断函数——决定图走哪条边。"""

    def test_judge_after_order_valid(self):
        """识别出菜品 → 走库存。"""
        assert judge_after_order({"dish": "番茄炒蛋"}) == "inventory"

    def test_judge_after_order_invalid(self):
        """没识别出菜品 → 结束。"""
        assert judge_after_order({"dish": ""}) == "end"

    def test_judge_after_inventory_ok(self):
        """库存充足 → 走烹饪。"""
        assert judge_after_inventory({"inventory_ok": True}) == "cook"

    def test_judge_after_inventory_missing(self):
        """缺货 → 结束。"""
        assert judge_after_inventory({"inventory_ok": False}) == "end"

    def test_judge_after_qc_pass(self):
        """质检通过 → 上菜。"""
        assert judge_after_qc({"qc_pass": True}) == "serve"

    def test_judge_after_qc_fallback(self):
        """连续失败触发降级。"""
        assert judge_after_qc({"qc_pass": False, "fallback": True}) == "fallback"

    def test_judge_after_qc_retry(self):
        """不通过且未达上限 → 回路退回烹饪。"""
        assert judge_after_qc({"qc_pass": False, "fallback": False}) == "cook"


class TestGraph:
    def test_graph_builds(self):
        """图能成功编译。"""
        app = build_graph()
        assert app is not None

    def test_graph_nodes(self):
        """图包含 6 个节点。"""
        app = build_graph()
        nodes = app.get_graph().nodes
        for name in ["accept_order", "check_inventory", "cook", "quality_check", "fallback", "serve"]:
            assert name in nodes
