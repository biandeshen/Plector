import logging

import pytest

from core.governance import Color, Governance


class MockSkillRegistry:
    """模拟 SkillRegistry，提供 .skills 字典供 Governance 操作。"""

    def __init__(self, skills: dict | None = None):
        self.skills = skills or {}


def make_skill(name: str, deps: list[str] | None = None) -> dict:
    return {"meta": {"name": name, "dependencies": deps or []}, "path": None, "module": None}


@pytest.fixture
def registry():
    return MockSkillRegistry()


@pytest.fixture
def gov(registry):
    return Governance(registry)


# ─── 循环检测 ───────────────────────────────────────────


def test_empty_graph_no_cycles(gov):
    assert gov._detect_cycles({}) == []


def test_dag_no_cycles(gov):
    graph = {"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}
    assert gov._detect_cycles(graph) == []


def test_simple_cycle(gov):
    graph = {"A": ["B"], "B": ["A"]}
    cycles = gov._detect_cycles(graph)
    assert ["A", "B", "A"] in cycles


def test_self_loop(gov):
    graph = {"A": ["A"]}
    cycles = gov._detect_cycles(graph)
    assert ["A", "A"] in cycles


def test_three_node_cycle(gov):
    graph = {"A": ["B"], "B": ["C"], "C": ["A"]}
    cycles = gov._detect_cycles(graph)
    assert len(cycles) >= 1
    assert any(len(c) == 4 and c[0] == c[-1] for c in cycles)


def test_shared_node_at_least_one_cycle(gov):
    """共享节点图中至少检测到一个环（枚举全部简单环是 NP-hard）"""
    graph = {"A": ["B", "C"], "B": ["A"], "C": ["B"]}
    cycles = gov._detect_cycles(graph)
    assert len(cycles) >= 1
    assert ["A", "B", "A"] in cycles


def test_separate_components_each_detected(gov):
    """独立连通分量各自检测环"""
    graph = {"A": ["B"], "B": ["A"], "C": ["D"], "D": ["C"]}
    cycles = gov._detect_cycles(graph)
    assert len(cycles) == 2


def test_disconnected_nodes_no_cycles(gov):
    graph = {"A": [], "B": [], "C": []}
    assert gov._detect_cycles(graph) == []


def test_missing_neighbor_logs_warning(gov, caplog):
    graph = {"A": ["NONEXISTENT"]}
    with caplog.at_level(logging.WARNING):
        cycles = gov._detect_cycles(graph)
    assert cycles == []
    assert "未知技能" in caplog.text
    assert "NONEXISTENT" in caplog.text


def test_unknown_node_not_in_graph_keys(gov):
    """不在 graph 键中的节点被跳过，不报错也不产生环"""
    graph = {"A": ["B"]}  # B 不是 graph 的键
    cycles = gov._detect_cycles(graph)
    assert cycles == []


# ─── check_dependencies ──────────────────────────────────


def test_check_dependencies_no_cycles(gov, registry):
    registry.skills = {
        "A": make_skill("A", ["B"]),
        "B": make_skill("B", []),
    }
    assert gov.check_dependencies() == []


def test_check_dependencies_with_cycle(gov, registry):
    registry.skills = {
        "A": make_skill("A", ["B"]),
        "B": make_skill("B", ["A"]),
    }
    cycles = gov.check_dependencies()
    assert len(cycles) >= 1


# ─── 健康分 ──────────────────────────────────────────────


def test_update_health_score_success(gov):
    gov.update_health_score("test_skill", True, 100)
    # 初始值 1.0，成功且快速 → 新分 = 0.9*1.0 + 0.1*(0.7*1 + 0.3*0.99) ≈ 0.9997
    assert gov.health_scores["test_skill"] > 0.99


def test_update_health_score_failure(gov):
    gov.update_health_score("test_skill", False, 5000)
    # 初始值 1.0，失败且中等耗时 → 新分下降
    assert gov.health_scores["test_skill"] < 1.0


def test_update_health_score_repeated_failures(gov):
    for _ in range(10):
        gov.update_health_score("test_skill", False, 15000)
    assert gov.health_scores["test_skill"] < 0.5


# ─── 自动淘汰 ────────────────────────────────────────────


def test_auto_eliminate_none_below_threshold(gov):
    gov.health_scores["A"] = 0.9
    gov.health_scores["B"] = 0.5
    eliminated = gov.auto_eliminate()
    assert eliminated == []
    assert "A" in gov.health_scores
    assert "B" in gov.health_scores


def test_auto_eliminate_threshold_boundary(gov):
    """恰好 0.4 不应被淘汰（< 0.4 才淘汰）"""
    gov.health_scores["A"] = 0.4
    eliminated = gov.auto_eliminate()
    assert eliminated == []
    assert "A" in gov.health_scores


def test_auto_eliminate_below_threshold(gov, registry):
    gov.health_scores["A"] = 0.3
    registry.skills = {"A": make_skill("A")}
    eliminated = gov.auto_eliminate()
    assert eliminated == ["A"]
    assert "A" not in gov.health_scores
    assert "A" not in registry.skills
    assert len(gov.eliminations) == 1
    assert gov.eliminations[0]["skill"] == "A"
    assert gov.eliminations[0]["score"] == 0.3
    assert gov.eliminations[0]["reason"] == "health_score_below_threshold"


def test_auto_eliminate_multiple(gov, registry):
    gov.health_scores["A"] = 0.1
    gov.health_scores["B"] = 0.3
    gov.health_scores["C"] = 0.8
    registry.skills = {"A": make_skill("A"), "B": make_skill("B"), "C": make_skill("C")}
    eliminated = gov.auto_eliminate()
    assert set(eliminated) == {"A", "B"}
    assert "C" in gov.health_scores
    assert "C" in registry.skills
    assert len(gov.eliminations) == 2


def test_auto_eliminate_empty_scores(gov):
    eliminated = gov.auto_eliminate()
    assert eliminated == []


# ─── Color 枚举 ──────────────────────────────────────────


def test_color_enum_distinct():
    assert Color.WHITE != Color.GRAY
    assert Color.GRAY != Color.BLACK
    assert Color.BLACK != Color.WHITE
