# beancount-helper

Convert bank statement Excel files into [Beancount](https://beancount.github.io/) transactions with a rule-based account matching engine.

```
2025-01-15 * "Coffee Shop" "Latte"
  Expenses:Food:Coffee  25.00 CNY
  Assets:CCB
```

## Supported banks

| Parser | Source |
|--------|--------|
| `ccb` | China Construction Bank (建设银行) statement `.xls` |
| `wechat` | WeChat Pay (微信支付) statement `.xlsx` |

## Installation

```bash
pip install beancount-helper
```

For development:

```bash
git clone https://github.com/FishCat233/beancount-helper.git
cd beancount-helper
uv sync
```

## Quick start

**Step 1** — Export your statement from the bank app and save it locally.

**Step 2** — (Optional) Create a rules file:

```
# rules.txt
p=opposite:eq:Coffee Shop;;direct=out=>Expenses:Food:Coffee
direct=in=>Income:Misc
```

**Step 3** — Run:

```bash
beancount-helper ccb.xls -p ccb -r rules.txt -o ledger.beancount
```

That's it. Every record falls into a Beancount account — either matched by your rules, or placed in `Equity:Opening-Balances` as a fallback.

## CLI reference

```
beancount-helper INPUT -p PARSER [-r RULES] [-o OUTPUT] [--asset ASSET] [--default-account ACCOUNT]
```

| Argument | Required | Default | Description |
|----------|----------|---------|-------------|
| `INPUT` | yes | — | Path to the bank statement file (`.xls` / `.xlsx`). |
| `-p`, `--parser` | yes | — | `ccb` or `wechat`. |
| `-r`, `--rules` | no | — | Path to a rules file. Without it, all records use the default account. |
| `-o`, `--output` | no | `output.beancount` | Output file path. |
| `--asset` | no | `Assets:CCB` / `Assets:WeChat` | Asset account for the source of funds. |
| `--default-account` | no | `Equity:Opening-Balances` | Fallback account when no rule matches. |

### Examples

```bash
# Bare minimum — everything goes to Equity:Opening-Balances
beancount-helper ccb.xls -p ccb

# With rules
beancount-helper wechat.xlsx -p wechat -r rules.txt

# Custom accounts
beancount-helper ccb.xls -p ccb -r rules.txt \
  --asset Assets:CCB:Savings \
  --default-account Expenses:Pending
```

## Rule system

Rules tell the tool which Beancount account a bill should be posted to. Each rule has this shape:

```
condition1;;condition2;;...=>TargetAccount
```

Conditions are AND-ed: a bill must satisfy **all** of them for the rule to fire. Rules are tried in order; the first match wins.

### Condition reference

#### Direction (`direct` / `direction`)

Matches whether money flows in or out.

```
direct=in       # income
direct=out      # expense
```

#### Property (`p` / `property`)

Matches a field on the bill record.

| Method | Syntax | Example |
|--------|--------|---------|
| exact | `p=field:eq:value` | `p=opposite:eq:Coffee Shop` |
| contains | `p=field:in:substring` | `p=note:in:lunch` |
| regex | `p=field:re:pattern` | `p=product:re:^ATMS$` |

Available fields: `opposite`, `note`, `product` (wechat only).

#### Amount comparisons

| Operator | Meaning |
|----------|---------|
| `lt=N` | amount < N |
| `le=N` | amount ≤ N |
| `gt=N` | amount > N |
| `ge=N` | amount ≥ N |
| `eq=N` | amount = N |

Negative amounts are expenses, positive are income (from the bank's perspective).

### Combining conditions

Separate conditions with `;;`:

```
# Small lunch expenses from a specific vendor
direct=out;;p=opposite:in:Restaurant;;lt=50.0=>Expenses:Food:Lunch

# Any income
direct=in=>Income:Misc
```

### Rule file format

One rule per line. Blank lines and `#`-comments are ignored.

```
# Food & drinks
p=opposite:eq:Starbucks=>Expenses:Food:Coffee
p=opposite:in:Pizza;;lt=80.0=>Expenses:Food:Takeout

# Transport
p=opposite:eq:DiDi=>Expenses:Transport:Ride
p=note:re:metro|subway=>Expenses:Transport:Transit

# Income
direct=in;;gt=5000.0=>Income:Salary
direct=in=>Income:Misc
```

## How it works

```
Bank Excel (.xls/.xlsx)
        │
        ▼
  bill_resolver       ← parses bank-specific formats into Bill objects
        │
        ▼
  transformer.rule    ← matches each Bill against the rule set
        │
        ▼
  beancount.core      ← assembles BeanCount transactions, dumps to text
        │
        ▼
  output.beancount
```

## Project structure

```
beancount-helper/
├── src/beancount_helper/
│   ├── cli.py                    CLI entry point
│   ├── beancount/core.py         BeanCount model + serialization
│   ├── bill_resolver/
│   │   ├── ccb.py                CCB Excel parser
│   │   └── wechat.py             WeChat Excel parser
│   └── transformer/rule.py       Rule matching engine
├── rules.example.txt             Sample rule set
└── test/
    ├── test_beancount_core.py
    └── test_rule_matcher.py
```

## Development

```bash
# Install dev dependencies
uv sync

# Run tests
uv run pytest

# Lint
uv run ruff check .
```

## License

MIT
