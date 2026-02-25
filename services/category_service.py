from database.category_dao import CategoryDAO
from models.category import Category


class CategoryService:
    def __init__(self, category_dao: CategoryDAO):
        self._dao = category_dao

    def get_all(self) -> list[Category]:
        return self._dao.get_all()

    def get_expense_categories(self) -> list[Category]:
        return self._dao.get_by_type("expense")

    def create(self, name: str, type_: str, color_hex: str) -> Category:
        name = name.strip()
        if not name:
            raise ValueError("Category name cannot be empty.")
        existing = [c.name.lower() for c in self._dao.get_all()]
        if name.lower() in existing:
            raise ValueError(f"A category named '{name}' already exists.")
        return self._dao.create(name, type_, color_hex)

    def update(self, category_id: int, name: str, type_: str, color_hex: str) -> Category:
        name = name.strip()
        if not name:
            raise ValueError("Category name cannot be empty.")
        existing = [c for c in self._dao.get_all() if c.id != category_id]
        if any(c.name.lower() == name.lower() for c in existing):
            raise ValueError(f"A category named '{name}' already exists.")
        return self._dao.update(category_id, name, type_, color_hex)

    def delete(self, category_id: int):
        cat = self._dao.get_by_id(category_id)
        if cat and cat.is_system:
            raise ValueError("System categories cannot be deleted.")
        self._dao.delete(category_id)
