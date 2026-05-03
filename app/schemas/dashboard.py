from __future__ import annotations

from pydantic import BaseModel


class SummaryTotals(BaseModel):
    totalIncome: float
    totalExpense: float
    netBalance: float


class MonthlyTotals(BaseModel):
    month: str
    income: float
    expense: float


class CategoryTotals(BaseModel):
    categoryId: str
    categoryName: str
    total: float
