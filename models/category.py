from dataclasses import dataclass


@dataclass
class Category:
    id: int
    name: str
    type: str           # 'income' | 'expense' | 'both'
    color_hex: str = "#888888"
    is_system: bool = False
