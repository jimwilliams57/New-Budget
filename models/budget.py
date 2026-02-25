from dataclasses import dataclass


@dataclass
class Budget:
    id: int
    category_id: int
    category_name: str
    month: str          # 'YYYY-MM'
    limit_amount: float
    spent_amount: float = 0.0
    color_hex: str = "#888888"

    @property
    def percentage(self) -> float:
        if self.limit_amount <= 0:
            return 0.0
        return self.spent_amount / self.limit_amount

    @property
    def remaining(self) -> float:
        return max(0.0, self.limit_amount - self.spent_amount)
