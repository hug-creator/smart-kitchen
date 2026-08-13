"""pytest 共享 fixture。

关键：把数据库隔离到临时文件，避免测试污染真实数据。
"""

import threading

import pytest

from db import database


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch):
    """每个测试用独立的临时数据库。"""
    test_db = tmp_path / "test_kitchen.db"
    monkeypatch.setattr(database, "DB_PATH", test_db)
    # 重置线程缓存的连接，让 get_conn 用新路径建连接
    database._local = threading.local()
    database.init_db()
    yield database
    # 清理连接
    conn = getattr(database._local, "conn", None)
    if conn:
        conn.close()
        database._local = threading.local()
