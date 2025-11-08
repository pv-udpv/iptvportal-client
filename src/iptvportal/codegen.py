"""ORM model generation from YAML schemas."""

from pathlib import Path
from typing import Any

from .schema import FieldType, SchemaLoader, SchemaRegistry, TableSchema


class ORMGenerator:
    """
    Генератор ORM моделей из YAML схем.

    Поддерживает:
    - SQLModel модели с полной типизацией
    - Pydantic BaseModel модели
    - Constraints (unique, nullable, foreign_key, primary_key, index, default)
    - Relationships (one-to-many, many-to-one, many-to-many)
    - Docstrings для моделей и полей
    """

    def __init__(self, schema_registry: SchemaRegistry):
        """
        Args:
            schema_registry: Реестр схем таблиц
        """
        self.registry = schema_registry

    def generate_sqlmodel(self, table_name: str, include_relationships: bool = True) -> str:
        """
        Генерирует SQLModel класс для таблицы.

        Args:
            table_name: Имя таблицы
            include_relationships: Включать ли relationships в модель

        Returns:
            Сгенерированный Python код SQLModel класса
        """
        schema = self.registry.get(table_name)
        if not schema:
            raise ValueError(f"Schema for table '{table_name}' not found in registry")

        lines = []

        # Imports
        lines.append("from datetime import date, datetime")
        lines.append("from typing import Optional")
        lines.append("")
        lines.append("from sqlmodel import Field, SQLModel")

        if include_relationships and self._has_relationships(schema):
            lines.append("from sqlmodel import Relationship")

        lines.append("")
        lines.append("")

        # Class definition
        class_name = self._table_name_to_class_name(table_name)
        lines.append(f"class {class_name}(SQLModel, table=True):")

        # Docstring
        if schema.metadata and schema.metadata.row_count:
            lines.append(f'    """')
            if schema.sync_config and hasattr(schema.sync_config, 'description'):
                lines.append(f"    {schema.sync_config.description}")
                lines.append("")
            lines.append(f"    Table: {table_name}")
            lines.append(f"    Total fields: {schema.total_fields}")
            lines.append(f"    Row count: {schema.metadata.row_count:,}")
            lines.append(f'    """')
        else:
            lines.append(f'    """ORM model for {table_name} table."""')

        lines.append("")
        lines.append(f"    __tablename__ = '{table_name}'")
        lines.append("")

        # Fields
        for position in sorted(schema.fields.keys()):
            field_def = schema.fields[position]
            field_lines = self._generate_sqlmodel_field(field_def, schema)
            lines.extend(field_lines)

        # Relationships
        if include_relationships:
            for position in sorted(schema.fields.keys()):
                field_def = schema.fields[position]
                if field_def.relationships:
                    rel_lines = self._generate_sqlmodel_relationship(field_def)
                    if rel_lines:
                        lines.extend(rel_lines)

        return "\n".join(lines)

    def generate_pydantic(self, table_name: str) -> str:
        """
        Генерирует Pydantic BaseModel класс для таблицы.

        Args:
            table_name: Имя таблицы

        Returns:
            Сгенерированный Python код Pydantic класса
        """
        schema = self.registry.get(table_name)
        if not schema:
            raise ValueError(f"Schema for table '{table_name}' not found in registry")

        lines = []

        # Imports
        lines.append("from datetime import date, datetime")
        lines.append("from typing import Optional")
        lines.append("")
        lines.append("from pydantic import BaseModel, Field")
        lines.append("")
        lines.append("")

        # Class definition
        class_name = self._table_name_to_class_name(table_name)
        lines.append(f"class {class_name}(BaseModel):")

        # Docstring
        lines.append(f'    """Pydantic model for {table_name} table."""')
        lines.append("")

        # Fields
        for position in sorted(schema.fields.keys()):
            field_def = schema.fields[position]
            field_lines = self._generate_pydantic_field(field_def)
            lines.extend(field_lines)

        # Config
        lines.append("")
        lines.append("    class Config:")
        lines.append("        from_attributes = True")

        return "\n".join(lines)

    def generate_all_models(
        self,
        output_format: str = "sqlmodel",
        output_dir: Path | None = None,
        include_relationships: bool = True,
    ) -> dict[str, str]:
        """
        Генерирует модели для всех таблиц в реестре.

        Args:
            output_format: Формат вывода ('sqlmodel' или 'pydantic')
            output_dir: Директория для сохранения файлов (опционально)
            include_relationships: Включать ли relationships (только для sqlmodel)

        Returns:
            Словарь {table_name: generated_code}
        """
        results = {}

        for table_name in self.registry.list_tables():
            if output_format == "sqlmodel":
                code = self.generate_sqlmodel(table_name, include_relationships)
            elif output_format == "pydantic":
                code = self.generate_pydantic(table_name)
            else:
                raise ValueError(f"Unsupported output format: {output_format}")

            results[table_name] = code

            # Сохранить в файл если указана директория
            if output_dir:
                output_dir.mkdir(parents=True, exist_ok=True)
                class_name = self._table_name_to_class_name(table_name)
                file_path = output_dir / f"{class_name.lower()}.py"
                file_path.write_text(code, encoding="utf-8")

        return results

    def _generate_sqlmodel_field(self, field_def, schema: TableSchema) -> list[str]:
        """Генерирует определение поля для SQLModel."""
        lines = []

        # Определить Python тип
        python_type = self._field_type_to_python_type(field_def.field_type)

        # Определить nullable
        nullable = True
        if field_def.constraints:
            nullable = field_def.constraints.get("nullable", True)

        # Primary key
        is_primary = False
        if field_def.constraints:
            is_primary = field_def.constraints.get("primary_key", False)

        # Формировать type hint
        if nullable and not is_primary:
            type_hint = f"Optional[{python_type}]"
        else:
            type_hint = python_type

        # Field arguments
        field_args = []

        # Default value
        if is_primary:
            field_args.append("primary_key=True")
        else:
            field_args.append("default=None" if nullable else "...")

        # Foreign key
        if field_def.constraints and field_def.constraints.get("foreign_key"):
            fk = field_def.constraints["foreign_key"]
            field_args.append(f'foreign_key="{fk}"')

        # Unique
        if field_def.constraints and field_def.constraints.get("unique"):
            field_args.append("unique=True")

        # Index
        if field_def.constraints and field_def.constraints.get("index"):
            field_args.append("index=True")

        # Description
        if field_def.description:
            desc = field_def.description.replace('"', '\\"')
            field_args.append(f'description="{desc}"')

        # Формировать строку поля
        field_name = field_def.python_name or field_def.name
        field_str = f"    {field_name}: {type_hint} = Field("
        field_str += ", ".join(field_args)
        field_str += ")"

        lines.append(field_str)

        return lines

    def _generate_pydantic_field(self, field_def) -> list[str]:
        """Генерирует определение поля для Pydantic."""
        lines = []

        # Определить Python тип
        python_type = self._field_type_to_python_type(field_def.field_type)

        # Определить nullable
        nullable = True
        if field_def.constraints:
            nullable = field_def.constraints.get("nullable", True)

        # Формировать type hint
        type_hint = f"Optional[{python_type}]" if nullable else python_type

        # Field arguments
        field_args = []

        # Default value
        if nullable:
            field_args.append("default=None")

        # Alias
        if field_def.alias:
            field_args.append(f'alias="{field_def.alias}"')

        # Description
        if field_def.description:
            desc = field_def.description.replace('"', '\\"')
            field_args.append(f'description="{desc}"')

        # Формировать строку поля
        field_name = field_def.python_name or field_def.name
        if field_args:
            field_str = f"    {field_name}: {type_hint} = Field("
            field_str += ", ".join(field_args)
            field_str += ")"
        else:
            field_str = f"    {field_name}: {type_hint}"

        lines.append(field_str)

        return lines

    def _generate_sqlmodel_relationship(self, field_def) -> list[str]:
        """Генерирует relationship для SQLModel."""
        if not field_def.relationships:
            return []

        lines = []
        rel_config = field_def.relationships

        rel_type = rel_config.get("type")  # one-to-many, many-to-one, etc.
        target_table = rel_config.get("target_table")
        back_populates = rel_config.get("back_populates")

        if not target_table:
            return []

        target_class = self._table_name_to_class_name(target_table)
        field_name = rel_config.get("field_name", f"{target_table}_rel")

        # Определить тип relationship
        if rel_type == "one-to-many":
            type_hint = f'list["{target_class}"]'
        elif rel_type == "many-to-one":
            type_hint = f'Optional["{target_class}"]'
        else:
            type_hint = f'"{target_class}"'

        # Формировать relationship
        rel_args = []
        if back_populates:
            rel_args.append(f'back_populates="{back_populates}"')

        if rel_args:
            rel_str = f"    {field_name}: {type_hint} = Relationship("
            rel_str += ", ".join(rel_args)
            rel_str += ")"
        else:
            rel_str = f"    {field_name}: {type_hint} = Relationship()"

        lines.append("")
        lines.append(rel_str)

        return lines

    def _field_type_to_python_type(self, field_type: FieldType) -> str:
        """Маппинг FieldType на Python тип."""
        type_map = {
            FieldType.INTEGER: "int",
            FieldType.STRING: "str",
            FieldType.BOOLEAN: "bool",
            FieldType.FLOAT: "float",
            FieldType.DATETIME: "datetime",
            FieldType.DATE: "date",
            FieldType.JSON: "dict",
            FieldType.UNKNOWN: "str",  # Fallback to str
        }
        return type_map.get(field_type, "str")

    def _table_name_to_class_name(self, table_name: str) -> str:
        """Конвертирует имя таблицы в имя класса (CamelCase)."""
        # subscriber -> Subscriber
        # tv_channel -> TvChannel
        parts = table_name.split("_")
        return "".join(word.capitalize() for word in parts)

    def _has_relationships(self, schema: TableSchema) -> bool:
        """Проверить есть ли relationships в схеме."""
        return any(field.relationships for field in schema.fields.values())

    @staticmethod
    def load_and_generate(
        schema_path: Path | str,
        output_format: str = "sqlmodel",
        output_dir: Path | None = None,
        include_relationships: bool = True,
    ) -> dict[str, str]:
        """
        Загрузить схемы из YAML и сгенерировать модели.

        Args:
            schema_path: Путь к YAML файлу со схемами
            output_format: Формат вывода ('sqlmodel' или 'pydantic')
            output_dir: Директория для сохранения файлов (опционально)
            include_relationships: Включать ли relationships

        Returns:
            Словарь {table_name: generated_code}
        """
        # Загрузить схемы
        registry = SchemaLoader.from_yaml(schema_path)

        # Создать генератор
        generator = ORMGenerator(registry)

        # Сгенерировать модели
        return generator.generate_all_models(output_format, output_dir, include_relationships)


__all__ = ["ORMGenerator"]
