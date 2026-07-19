"""Convert bank statement Excel files into Beancount format with rule-based account matching."""

import argparse
import enum
import sys
from pathlib import Path

from beancount_helper.bill_resolver.ccb import resolve_from_excel as ccb_resolve
from beancount_helper.bill_resolver.wechat import resolve_from_excel as wechat_resolve
from beancount_helper.beancount.core import BeanCount, dump_beancounts
from beancount_helper.transformer.rule import Bill, match_rule


# ---------------------------------------------------------------------------
# Parser registry
# ---------------------------------------------------------------------------


class Parser(enum.Enum):
    CCB = "ccb"
    WECHAT = "wechat"


# ---------------------------------------------------------------------------
# Rule file loading
# ---------------------------------------------------------------------------


def load_rules(path: str) -> list[str]:
    """Load rules from a file, one per line. Blank lines and #-comments are ignored."""
    rules = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            rules.append(line)
    return rules


# ---------------------------------------------------------------------------
# Bill -> BeanCount conversion
# ---------------------------------------------------------------------------


def bill_dict(parser: Parser, raw_bill) -> Bill:
    """Convert a parser-specific Bill dataclass into a dict for the rule engine."""
    if parser == Parser.CCB:
        return Bill(
            is_balance_in=raw_bill.is_balance_in,
            date=raw_bill.date,
            amount=raw_bill.amount,
            currency_type=raw_bill.currency_type,
            opposite=raw_bill.opposite,
            raw_opposite=raw_bill.raw_opposite,
            note=raw_bill.note,
            raw_note=raw_bill.raw_note,
        )
    elif parser == Parser.WECHAT:
        return Bill(
            is_balance_in=raw_bill.is_balance_in,
            date=raw_bill.date,
            amount=raw_bill.amount,
            currency_type=raw_bill.currency_type,
            opposite=raw_bill.opposite,
            note=raw_bill.note,
            product=raw_bill.product,
        )


def apply_rules(bill: Bill, rules: list[str]) -> str | None:
    """Apply rules in order; return the target account of the first match, or None."""
    for rule in rules:
        result = match_rule(bill, rule)
        if result is not None:
            return result
    return None


def convert_to_beancount(
    parser: Parser,
    raw_bill,
    rules: list[str],
    asset_account: str,
    default_account: str,
) -> BeanCount:
    """Convert a raw bill record into a BeanCount transaction.

    Beancount double-entry conventions:
      - Expense (money out): debit = expense/fallback account, credit = asset
      - Income  (money in):  debit = asset, credit = income/fallback account
    """
    b = bill_dict(parser, raw_bill)
    matched = apply_rules(b, rules)

    if parser == Parser.CCB:
        receiver = raw_bill.opposite
        digest = raw_bill.note or ""
    elif parser == Parser.WECHAT:
        receiver = raw_bill.opposite
        digest = (
            f"Product: {raw_bill.product}; "
            f"Payment: {raw_bill.payment_method}; "
            f"Note: {raw_bill.note}"
        )

    if raw_bill.is_balance_in:
        # Income: asset <- income source
        in_account = asset_account
        out_account = matched or default_account
    else:
        # Expense: expense category <- asset
        in_account = matched or default_account
        out_account = asset_account

    return BeanCount(
        datetime=raw_bill.date,
        receiver=receiver,
        digest=digest,
        in_account=in_account,
        out_account=out_account,
        amount=raw_bill.amount,
        currency_type=raw_bill.currency_type,
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="Convert bank statement Excel files to Beancount format.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  beancount-helper ccb.xls -p ccb -o output.beancount
  beancount-helper wechat.xlsx -p wechat -r rules.txt -o output.beancount
  beancount-helper ccb.xls -p ccb -r food.txt -r transport.txt --asset Assets:CCB:Savings
        """,
    )

    parser.add_argument(
        "input",
        type=str,
        help="Path to the input file (.xls / .xlsx).",
    )
    parser.add_argument(
        "-p",
        "--parser",
        type=Parser,
        required=True,
        choices=list(Parser),
        help="Statement type: 'ccb' (China Construction Bank) or 'wechat' (WeChat).",
    )
    parser.add_argument(
        "-r",
        "--rules",
        type=str,
        action="append",
        default=None,
        help="Optional path to a rules file. Can be specified multiple times.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="output.beancount",
        help="Output file path (default: output.beancount).",
    )
    parser.add_argument(
        "--asset",
        type=str,
        default=None,
        help="Asset account name (default: Assets:CCB for ccb, Assets:WeChat for wechat).",
    )
    parser.add_argument(
        "--default-account",
        type=str,
        default="Equity:Opening-Balances",
        help="Fallback account when no rule matches (default: Equity:Opening-Balances).",
    )

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Load rules (optional)
    rules = []
    if args.rules:
        for rules_path_str in args.rules:
            rules_path = Path(rules_path_str)
            if not rules_path.exists():
                print(f"Error: rules file not found: {rules_path_str}", file=sys.stderr)
                sys.exit(1)
            print(f"Loading rules: {rules_path_str}")
            loaded = load_rules(str(rules_path))
            rules.extend(loaded)
            print(f"  Loaded {len(loaded)} rule(s)")
        print(f"  Total: {len(rules)} rule(s)")
    else:
        print("No rules file provided; all records will use the default account.")

    # Determine asset account
    if args.asset:
        asset_account = args.asset
    elif args.parser == Parser.CCB:
        asset_account = "Assets:CCB"
    else:
        asset_account = "Assets:WeChat"

    default_account = args.default_account

    # Parse statement
    print(f"Parsing: {args.input} (parser={args.parser.value})")
    if args.parser == Parser.CCB:
        raw_bills = ccb_resolve(str(input_path))
    else:
        raw_bills = wechat_resolve(str(input_path))
    print(f"  Parsed {len(raw_bills)} record(s)")

    # Convert
    beancounts = []
    matched_count = 0
    for raw in raw_bills:
        bc = convert_to_beancount(
            args.parser, raw, rules, asset_account, default_account
        )
        beancounts.append(bc)
        if bc.in_account != default_account and bc.out_account != default_account:
            matched_count += 1

    if rules:
        print(f"  Rules matched: {matched_count}/{len(raw_bills)} record(s)")

    # Write output
    output = dump_beancounts(beancounts)
    output_path = Path(args.output)
    output_path.write_text(output, encoding="utf-8")
    print(f"Output written to: {args.output}")


if __name__ == "__main__":
    main()
