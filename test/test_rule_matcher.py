import pytest
import datetime
from beancount_helper.transformer.rule import Bill, match_rule


# ---------- 辅助构建 Bill ----------
def make_bill(**kwargs) -> Bill:
    default = {
        "is_balance_in": True,
        "date": datetime.datetime.now(),
        "amount": 100.0,
        "currency_type": "CNY",
        "opposite": "哈基米",
        "note": "午餐",
        "product": "餐饮",
    }
    default.update(kwargs)
    return Bill(**default)  # type: ignore


# ---------- 测试 direct 操作符 ----------
def test_direct_in():
    bill = make_bill(is_balance_in=True)
    rule = "direct=in=>Expenses::Food"
    assert match_rule(bill, rule) == "Expenses::Food"


def test_direct_out():
    bill = make_bill(is_balance_in=False)
    rule = "direct=out=>Income::Salary"
    assert match_rule(bill, rule) == "Income::Salary"


def test_direct_mismatch():
    bill = make_bill(is_balance_in=True)
    rule = "direct=out=>Ignore"
    assert match_rule(bill, rule) is None


def test_direct_missing_field():
    bill = make_bill()  # 默认有 is_balance_in
    # 故意删除该字段
    del bill["is_balance_in"]  # type: ignore
    rule = "direct=in=>Target"
    assert match_rule(bill, rule) is None


# ---------- 测试 property 操作符 ----------
def test_property_eq():
    bill = make_bill(opposite="哈基米")
    rule = "p=opposite:eq:哈基米=>Matched"
    assert match_rule(bill, rule) == "Matched"


def test_property_eq_fail():
    bill = make_bill(opposite="daisy")
    rule = "p=opposite:eq:哈基米=>No"
    assert match_rule(bill, rule) is None


def test_property_in():
    bill = make_bill(note="午餐吃面")
    rule = "p=note:in:午餐=>Found"
    assert match_rule(bill, rule) == "Found"


def test_property_in_fail():
    bill = make_bill(note="晚餐")
    rule = "p=note:in:午餐=>NotFound"
    assert match_rule(bill, rule) is None


def test_property_re():
    bill = make_bill(product="水果-苹果")
    rule = "p=product:re:水果=>Found"
    assert match_rule(bill, rule) == "Found"


def test_property_re_fail():
    bill = make_bill(product="蔬菜")
    rule = "p=product:re:水果=>NotFound"
    assert match_rule(bill, rule) is None


def test_property_missing_key():
    bill = make_bill()
    rule = "p=unknown:eq:xxx=>No"
    assert match_rule(bill, rule) is None  # 键不存在返回 False


# ---------- 测试比较操作符 ----------
def test_comparison_lt():
    bill = make_bill(amount=15.0)
    rule = "lt=20.0=>Less"
    assert match_rule(bill, rule) == "Less"


def test_comparison_lt_fail():
    bill = make_bill(amount=25.0)
    rule = "lt=20.0=>NotLess"
    assert match_rule(bill, rule) is None


def test_comparison_gt():
    bill = make_bill(amount=30.0)
    rule = "gt=20.0=>Greater"
    assert match_rule(bill, rule) == "Greater"


def test_comparison_eq():
    bill = make_bill(amount=50.0)
    rule = "eq=50.0=>Equal"
    assert match_rule(bill, rule) == "Equal"


def test_comparison_le():
    bill = make_bill(amount=20.0)
    rule = "le=20.0=>LePass"
    assert match_rule(bill, rule) == "LePass"


def test_comparison_le_fail():
    bill = make_bill(amount=25.0)
    rule = "le=20.0=>LeFail"
    assert match_rule(bill, rule) is None


def test_comparison_ge():
    bill = make_bill(amount=20.0)
    rule = "ge=20.0=>GePass"
    assert match_rule(bill, rule) == "GePass"


def test_comparison_ge_fail():
    bill = make_bill(amount=15.0)
    rule = "ge=20.0=>GeFail"
    assert match_rule(bill, rule) is None


def test_comparison_invalid_amount():
    bill = make_bill(amount="abc")  # 类型错误，但在 Bill 中声明为 float，这里模拟异常
    # 实际传入时不会通过类型检查，我们可以用 dict 绕过
    bill = {"amount": "abc"}  # type: ignore
    rule = "lt=10.0=>Fail"
    assert match_rule(bill, rule) is None  # 转换失败返回 False


# ---------- 测试组合规则 ----------
def test_combined_rule_all_true():
    bill = make_bill(is_balance_in=True, amount=15.0, opposite="哈基米")
    rule = "direct=in;;lt=20.0;;p=opposite:eq:哈基米=>Combined"
    assert match_rule(bill, rule) == "Combined"


def test_combined_rule_one_false():
    bill = make_bill(is_balance_in=True, amount=25.0, opposite="哈基米")
    rule = "direct=in;;lt=20.0;;p=opposite:eq:哈基米=>Fail"
    assert match_rule(bill, rule) is None


def test_combined_with_unknown_operator():
    # 未知操作符被忽略，但其他条件满足则返回目标
    bill = make_bill(is_balance_in=True)
    rule = "direct=in;;unknown=xxx=>Target"
    assert match_rule(bill, rule) == "Target"


def test_all_operators_unknown():
    # 所有段都是未知操作符，最终返回 target（因为没有返回 None）
    bill = make_bill()
    rule = "foo=bar;;baz=qux=>Default"
    assert match_rule(bill, rule) == "Default"


# ---------- 测试规则解析 ----------
def test_missing_arrow():
    bill = make_bill()
    rule = "direct=in"  # 没有 =>
    with pytest.raises(ValueError, match="Can't resolve rule"):
        match_rule(bill, rule)


def test_empty_segment():
    bill = make_bill(is_balance_in=True)
    rule = ";;direct=in;;=>Target"  # 前后有空段
    assert match_rule(bill, rule) == "Target"  # 应忽略空段，匹配成功


def test_all_empty_segments():
    bill = make_bill()
    rule = ";;;;=>NoCondition"  # 所有段都为空
    assert match_rule(bill, rule) == "NoCondition"  # 无任何条件，直接返回目标


# ---------- 测试 property 操作符的不同方法名 ----------
def test_property_operator_alias():
    # 支持 "property" 别名
    bill = make_bill(opposite="daisy")
    rule = "property=opposite:eq:daisy=>Found"
    assert match_rule(bill, rule) == "Found"


# ---------- 测试 direct 操作符别名 ----------
def test_direction_alias():
    bill = make_bill(is_balance_in=False)
    rule = "direction=out=>Found"
    assert match_rule(bill, rule) == "Found"


# ---------- 测试无规则直接命中 ----------
def test_no_match_condition_returns_target():
    # 没有任何 = 的规则直接返回 target
    bill = make_bill()
    rule = "=>DirectTarget"
    assert match_rule(bill, rule) == "DirectTarget"


def test_only_text_before_arrow():
    # 普通文本（无操作符）直接命中
    bill = make_bill()
    rule = "some-text-without-equals=>Target"
    assert match_rule(bill, rule) == "Target"
