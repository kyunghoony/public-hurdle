from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Final, Protocol


class Metric(str, Enum):
    REVENUE = "revenue"
    OPERATING_INCOME = "operating_income"
    PRETAX_INCOME = "pretax_income"
    TAX_EXPENSE = "tax_expense"
    OCF = "ocf"
    CAPEX = "capex"
    DEPRECIATION = "depreciation"
    EQUITY = "equity"
    CASH = "cash"
    DEBT = "debt"


class AccountLine(Protocol):
    @property
    def statement(self) -> str:
        ...

    @property
    def account_id(self) -> str:
        ...

    @property
    def account_name(self) -> str:
        ...

    @property
    def amount(self) -> float:
        ...


@dataclass(frozen=True, slots=True)
class AccountSpec:
    statements: tuple[str, ...]
    account_ids: tuple[str, ...]
    names: tuple[str, ...]


ACCOUNT_SPECS: Final[Mapping[Metric, AccountSpec]] = {
    Metric.REVENUE: AccountSpec(
        ("IS", "CIS"),
        ("ifrs-full_Revenue", "ifrs-full_RevenueFromContractsWithCustomers"),
        ("매출액", "수익매출액", "영업수익"),
    ),
    Metric.OPERATING_INCOME: AccountSpec(
        ("IS", "CIS"),
        ("dart_OperatingIncomeLoss",),
        ("영업이익", "영업이익손실"),
    ),
    Metric.PRETAX_INCOME: AccountSpec(
        ("IS", "CIS"),
        ("ifrs-full_ProfitLossBeforeTax",),
        ("법인세비용차감전순이익", "법인세비용차감전순이익손실"),
    ),
    Metric.TAX_EXPENSE: AccountSpec(
        ("IS", "CIS"),
        ("ifrs-full_IncomeTaxExpenseContinuingOperations",),
        ("법인세비용",),
    ),
    Metric.OCF: AccountSpec(
        ("CF",),
        ("ifrs-full_CashFlowsFromUsedInOperatingActivities",),
        ("영업활동현금흐름", "영업활동으로인한현금흐름"),
    ),
    Metric.CAPEX: AccountSpec(
        ("CF",),
        ("ifrs-full_PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities",),
        ("유형자산의취득", "유형자산취득"),
    ),
    Metric.DEPRECIATION: AccountSpec(
        ("CF", "IS", "CIS"),
        ("ifrs-full_DepreciationAndAmortisationExpense", "ifrs-full_DepreciationAndAmortizationExpense"),
        ("감가상각비", "감가상각비및무형자산상각비", "감가상각비와기타상각비"),
    ),
    Metric.EQUITY: AccountSpec(
        ("BS",),
        ("ifrs-full_Equity",),
        ("자본총계",),
    ),
    Metric.CASH: AccountSpec(
        ("BS",),
        ("ifrs-full_CashAndCashEquivalents",),
        ("현금및현금성자산",),
    ),
    Metric.DEBT: AccountSpec(
        ("BS",),
        (
            "ifrs-full_ShorttermBorrowings",
            "ifrs-full_CurrentBorrowings",
            "ifrs-full_CurrentPortionOfLongtermBorrowings",
            "ifrs-full_LongtermBorrowings",
            "ifrs-full_NoncurrentBorrowings",
            "ifrs-full_Debentures",
            "ifrs-full_BondsIssued",
        ),
        ("단기차입금", "유동성장기부채", "유동성장기차입금", "장기차입금", "사채"),
    ),
}


def first_amount(lines: Sequence[AccountLine], metric: Metric) -> float:
    for line in lines:
        if _matches(line, ACCOUNT_SPECS[metric]) and line.amount != 0:
            return line.amount
    return 0.0


def sum_amount(lines: Sequence[AccountLine], metric: Metric) -> float:
    return sum(line.amount for line in lines if _matches(line, ACCOUNT_SPECS[metric]))


def _matches(line: AccountLine, spec: AccountSpec) -> bool:
    if spec.statements and line.statement not in spec.statements:
        return False
    if line.account_id in spec.account_ids:
        return True
    return line.account_name in spec.names
