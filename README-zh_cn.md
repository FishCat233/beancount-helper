# beancount-helper

将银行账单 Excel 转换为 [Beancount](https://beancount.github.io/) 交易记录，支持基于规则的账户自动匹配。

```
2025-01-15 * "瑞幸咖啡" "生椰拿铁"
  Expenses:Food:Coffee  9.90 CNY
  Assets:WeChat
```

## 支持的银行

| 解析器   | 来源                 |
| -------- | -------------------- |
| `ccb`    | 建设银行账单 `.xls`  |
| `wechat` | 微信支付账单 `.xlsx` |

## 安装

```bash
pip install beancount-helper
```

开发模式：

```bash
git clone https://github.com/FishCat233/beancount-helper.git
cd beancount-helper
uv sync
```

## 快速上手

**第一步** — 从银行 App 导出账单，保存到本地。

**第二步** —（可选）创建规则文件：

```
# rules.txt
p=opposite:eq:瑞幸咖啡;;direct=out=>Expenses:Food:Coffee
direct=in=>Income:Misc
```

**第三步** — 运行：

```bash
beancount-helper ccb.xls -p ccb -r rules.txt -o ledger.beancount
```

搞定。每条记录都会落入一个 Beancount 账户 — 命中规则的走指定账户，未命中的默认归入 `Equity:Opening-Balances`。

## CLI 参考

```
beancount-helper INPUT -p PARSER [-r RULES] [-o OUTPUT] [--asset ASSET] [--default-account ACCOUNT]
```

| 参数                | 必填 | 默认值                         | 说明                                         |
| ------------------- | ---- | ------------------------------ | -------------------------------------------- |
| `INPUT`             | 是   | —                              | 账单文件路径（`.xls` / `.xlsx`）。           |
| `-p`, `--parser`    | 是   | —                              | `ccb` 或 `wechat`。                          |
| `-r`, `--rules`     | 否   | —                              | 规则文件路径。不提供时所有记录使用默认账户。 |
| `-o`, `--output`    | 否   | `output.beancount`             | 输出文件路径。                               |
| `--asset`           | 否   | `Assets:CCB` / `Assets:WeChat` | 资金所属的资产账户。                         |
| `--default-account` | 否   | `Equity:Opening-Balances`      | 未命中规则时的兜底账户。                     |

### 示例

```bash
# 最简用法 — 全部归入 Equity:Opening-Balances
beancount-helper ccb.xls -p ccb

# 带规则
beancount-helper wechat.xlsx -p wechat -r rules.txt

# 自定义账户
beancount-helper ccb.xls -p ccb -r rules.txt \
  --asset Assets:CCB:Savings \
  --default-account Expenses:Pending
```

## 规则系统

规则告诉工具每条账单应该归入哪个 Beancount 账户。每条规则的格式：

```
条件1;;条件2;;...=>目标账户
```

条件是 AND 关系：一条账单必须满足**全部**条件规则才会命中。规则按顺序匹配，命中第一条即停止。

### 条件参考

#### 收支方向（`direct` / `direction`）

匹配资金流向。

```
direct=in       # 收入
direct=out      # 支出
```

#### 属性匹配（`p` / `property`）

匹配账单上的字段。

| 方式 | 语法             | 示例                     |
| ---- | ---------------- | ------------------------ |
| 精确 | `p=字段:eq:值`   | `p=opposite:eq:瑞幸咖啡` |
| 包含 | `p=字段:in:子串` | `p=note:in:午餐`         |
| 正则 | `p=字段:re:模式` | `p=product:re:^美团外卖` |

可用字段：`opposite`、`note`、`product`（仅微信）。

#### 金额比较

| 操作符 | 含义     |
| ------ | -------- |
| `lt=N` | 金额 < N |
| `le=N` | 金额 ≤ N |
| `gt=N` | 金额 > N |
| `ge=N` | 金额 ≥ N |
| `eq=N` | 金额 = N |

负数为支出，正数为收入（银行视角）。

### 组合条件

用 `;;` 分隔多个条件：

```
# 某家餐厅的小额午餐支出
direct=out;;p=opposite:in:餐厅;;lt=50.0=>Expenses:Food:Lunch

# 所有收入
direct=in=>Income:Misc
```

### 规则文件格式

每行一条规则，空行和 `#` 注释会被忽略。

```
# 餐饮
p=opposite:eq:瑞幸咖啡=>Expenses:Food:Coffee
p=opposite:eq:美团外卖=>Expenses:Food:Takeout
p=opposite:eq:饿了么=>Expenses:Food:Takeout
p=opposite:in:餐厅;;lt=100.0=>Expenses:Food:Dining

# 出行
p=opposite:eq:滴滴出行=>Expenses:Transport:Ride
p=opposite:eq:一车一人=>Expenses:Transport:Bike
p=opposite:in:地铁=>Expenses:Transport:Transit

# 购物
p=opposite:eq:淘宝=>Expenses:Shopping:Online
p=opposite:eq:京东=>Expenses:Shopping:Online

# 收入
direct=in;;gt=5000.0=>Income:Salary
direct=in=>Income:Misc
```

## 工作原理

```
银行 Excel (.xls/.xlsx)
        │
        ▼
  bill_resolver       ← 解析银行特定格式，生成 Bill 对象
        │
        ▼
  transformer.rule    ← 将每条 Bill 与规则集匹配
        │
        ▼
  beancount.core      ← 组装 BeanCount 交易，输出为文本
        │
        ▼
  output.beancount
```

## 项目结构

```
beancount-helper/
├── src/beancount_helper/
│   ├── cli.py                    CLI 入口
│   ├── beancount/core.py         BeanCount 模型与序列化
│   ├── bill_resolver/
│   │   ├── ccb.py                建行 Excel 解析器
│   │   └── wechat.py             微信 Excel 解析器
│   └── transformer/rule.py       规则匹配引擎
├── rules.example.txt             示例规则集
└── test/
    ├── test_beancount_core.py
    └── test_rule_matcher.py
```

## 开发

```bash
# 克隆并以可编辑模式安装
git clone https://github.com/FishCat233/beancount-helper.git
cd beancount-helper
uv sync

# 运行测试
uv run pytest

# 代码检查
uv run ruff check .
```

## License

MIT
