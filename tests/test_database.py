"""数据库层测试：库存扣减、回滚、订单记录、统计。"""

from db import database


class TestInventory:
    def test_initial_stock(self):
        """初始化后库存应为默认值。"""
        stock = database.get_all_stock()
        assert stock["鸡蛋"] == 6
        assert stock["米饭"] == 1000
        assert stock["牛排"] == 2

    def test_check_stock_sufficient(self):
        """1 份番茄炒蛋（需鸡蛋2、番茄2），库存充足。"""
        result = database.check_stock("番茄炒蛋", 1)
        assert result["ok"] is True
        assert result["missing"] == []

    def test_check_stock_insufficient(self):
        """4 份番茄炒蛋需鸡蛋 8 个，库存只有 6 个 → 不足。"""
        result = database.check_stock("番茄炒蛋", 4)
        assert result["ok"] is False
        missing_items = [m["item"] for m in result["missing"]]
        assert "鸡蛋" in missing_items

    def test_check_stock_unknown_dish(self):
        """未知菜品应返回失败。"""
        result = database.check_stock("不存在的菜")
        assert result["ok"] is False

    def test_deduct_and_restore(self):
        """扣减后库存减少，回滚后恢复。"""
        before = database.get_all_stock()["鸡蛋"]

        database.deduct_stock("番茄炒蛋", 1)  # 扣 2 个鸡蛋
        after_deduct = database.get_all_stock()["鸡蛋"]
        assert after_deduct == before - 2

        database.restore_stock("番茄炒蛋", 1)  # 回滚
        after_restore = database.get_all_stock()["鸡蛋"]
        assert after_restore == before

    def test_deduct_multiple_quantity(self):
        """多份订单按比例扣减。"""
        before = database.get_all_stock()["牛排"]
        database.deduct_stock("煎牛排", 2)  # 每份 1 个牛排，2 份扣 2 个
        after = database.get_all_stock()["牛排"]
        assert after == before - 2


class TestOrders:
    def test_save_and_list(self):
        """保存订单后能查回。"""
        oid = database.save_order("来一份番茄炒蛋", "番茄炒蛋", 1, 8, "好吃", "served")
        assert oid == 1

        orders = database.list_orders()
        assert len(orders) == 1
        assert orders[0]["dish"] == "番茄炒蛋"
        assert orders[0]["status"] == "served"
        assert orders[0]["qc_score"] == 8

    def test_list_orders_limit(self):
        """limit 参数生效。"""
        for i in range(5):
            database.save_order(f"订单{i}", "番茄炒蛋", 1, 8, "", "served")
        orders = database.list_orders(limit=3)
        assert len(orders) == 3

    def test_order_stats(self):
        """统计：总数、成功率、平均分。"""
        database.save_order("a", "番茄炒蛋", 1, 8, "", "served")
        database.save_order("b", "番茄炒蛋", 1, None, "", "out_of_stock")
        database.save_order("c", "番茄炒蛋", 1, 6, "", "served")

        stats = database.order_stats()
        assert stats["total"] == 3
        assert stats["success"] == 2
        assert stats["success_rate"] == 66.7
        assert stats["avg_score"] == 7.0
