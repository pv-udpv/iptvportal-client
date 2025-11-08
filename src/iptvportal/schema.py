"""Schema system for table field definitions and SELECT * expansion."""

import importlib
import json
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Union, get_args, get_origin

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from pydantic import BaseModel

    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    BaseModel = None

try:
    from sqlmodel import SQLModel  # type: ignore

    HAS_SQLMODEL = True
except ImportError:
    HAS_SQLMODEL = False
    SQLModel = None


class FieldType(Enum):
    """Типы полей таблиц."""

    INTEGER = "integer"
    STRING = "string"
    BOOLEAN = "boolean"
    FLOAT = "float"
    DATETIME = "datetime"
    DATE = "date"
    JSON = "json"
    UNKNOWN = "unknown"


@dataclass
class SyncConfig:
    """
    Конфигурация синхронизации таблицы с удалённым источником.

    Определяет ограничения (guardrails) для процесса синхронизации:
    - Фильтрация данных (WHERE, LIMIT)
    - Стратегия кэширования
    - Размер чанков
    - Автоматическая синхронизация
    """

    # Query constraints
    where: str | None = None
    """SQL WHERE clause для фильтрации синхронизируемых данных"""

    limit: int | None = None
    """Максимальное количество записей для синхронизации"""

    order_by: str = "id"
    """Поле для сортировки при синхронизации"""

    # Chunking behavior
    chunk_size: int = 1000
    """Количество записей в одном чанке"""

    enable_chunking: bool = True
    """Использовать ли чанкование при синхронизации"""

    # Cache behavior
    ttl: int | None = None
    """Time-to-live для кэша в секундах (None = использовать глобальный TTL)"""

    cache_strategy: str = "full"
    """Стратегия кэширования: "full", "incremental", "on-demand" """

    # Sync scheduling
    auto_sync: bool = False
    """Автоматически синхронизировать при первом обращении"""

    sync_interval: int | None = None
    """Интервал автоматической пересинхронизации в секундах"""

    disabled: bool = False
    """Отключить синхронизацию для этой таблицы (например, из-за отсутствия доступа)"""

    # Data filtering
    include_fields: list[str] | None = None
    """Синхронизировать только указанные поля"""

    exclude_fields: list[str] | None = None
    """Исключить указанные поля из синхронизации"""

    # Incremental sync
    incremental_field: str | None = None
    """Поле для инкрементальной синхронизации (обычно updated_at)"""

    incremental_mode: bool = False
    """Использовать инкрементальную синхронизацию"""

    # Performance
    prefetch_relationships: bool = False
    """Предзагружать связанные данные"""

    max_concurrent_chunks: int = 3
    """Максимальное количество параллельных загрузок чанков"""

    def validate(self) -> list[str]:
        """Валидация конфигурации синхронизации."""
        errors = []

        if self.chunk_size <= 0:
            errors.append("chunk_size must be positive")

        if self.limit and self.limit < self.chunk_size:
            errors.append("limit should be >= chunk_size")

        if self.cache_strategy not in ("full", "incremental", "on-demand"):
            errors.append(f"Invalid cache_strategy: {self.cache_strategy}")

        if self.incremental_mode and not self.incremental_field:
            errors.append("incremental_field required when incremental_mode=True")

        if self.ttl and self.ttl < 0:
            errors.append("ttl must be non-negative")

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Экспорт конфигурации в словарь."""
        result = {}

        if self.where:
            result["where"] = self.where
        if self.limit:
            result["limit"] = self.limit
        if self.order_by != "id":
            result["order_by"] = self.order_by
        if self.chunk_size != 1000:
            result["chunk_size"] = self.chunk_size
        if not self.enable_chunking:
            result["enable_chunking"] = self.enable_chunking
        if self.ttl:
            result["ttl"] = self.ttl
        if self.cache_strategy != "full":
            result["cache_strategy"] = self.cache_strategy
        if self.auto_sync:
            result["auto_sync"] = self.auto_sync
        if self.sync_interval:
            result["sync_interval"] = self.sync_interval
        if self.include_fields:
            result["include_fields"] = self.include_fields
        if self.exclude_fields:
            result["exclude_fields"] = self.exclude_fields
        if self.incremental_field:
            result["incremental_field"] = self.incremental_field
        if self.incremental_mode:
            result["incremental_mode"] = self.incremental_mode
        if self.prefetch_relationships:
            result["prefetch_relationships"] = self.prefetch_relationships
        if self.max_concurrent_chunks != 3:
            result["max_concurrent_chunks"] = self.max_concurrent_chunks
        if self.disabled:
            result["disabled"] = self.disabled

        return result


@dataclass
class TableMetadata:
    """Метаданные таблицы, собранные при интроспекции."""

    row_count: int = 0
    """Общее количество строк в таблице"""

    max_id: int | None = None
    """Максимальное значение ID"""

    min_id: int | None = None
    """Минимальное значение ID"""

    analyzed_at: str | None = None
    """Timestamp последнего анализа (ISO format)"""

    timestamp_ranges: dict[str, dict[str, Any]] = field(default_factory=dict)
    """Диапазоны значений для timestamp полей: {field_name: {min: ..., max: ...}}"""

    estimated_size_mb: float | None = None
    """Примерный размер таблицы в MB"""

    def to_dict(self) -> dict[str, Any]:
        """Экспорт метаданных в словарь."""
        result = {
            "row_count": self.row_count,
            "analyzed_at": self.analyzed_at or datetime.now().isoformat(),
        }

        if self.max_id is not None:
            result["max_id"] = self.max_id
        if self.min_id is not None:
            result["min_id"] = self.min_id
        if self.estimated_size_mb:
            result["estimated_size_mb"] = self.estimated_size_mb

        # Добавить диапазоны timestamp полей
        for field_name, ranges in self.timestamp_ranges.items():
            if ranges.get("min"):
                result[f"{field_name}_min"] = ranges["min"]
            if ranges.get("max"):
                result[f"{field_name}_max"] = ranges["max"]

        return result


@dataclass
class FieldDefinition:
    """
    Описание поля таблицы.

    Attributes:
        name: Имя поля в БД
        position: Позиция поля в порядке SELECT * (начиная с 0)
        alias: Алиас для маппинга (как в Pydantic Field(alias=...))
        python_name: Имя для Python (для snake_case преобразования)
        remote_name: Имя поля в удалённой схеме (для column-based extraction)
        field_type: Тип поля
        description: Описание поля
        validator: Функция валидации
        transformer: Функция преобразования значения при маппинге
    """

    name: str
    position: int
    alias: str | None = None
    python_name: str | None = None
    remote_name: str | None = None
    field_type: FieldType = FieldType.UNKNOWN
    description: str | None = None
    validator: Callable | None = None
    transformer: Callable | None = None

    @property
    def mapped_name(self) -> str:
        """Имя для маппинга (приоритет: python_name > alias > name)."""
        return self.python_name or self.alias or self.name


class TableSchema:
    """
    Схема таблицы с частичным описанием полей.

    Attributes:
        table_name: Имя таблицы
        fields: Словарь {position: FieldDefinition} для описанных полей
        total_fields: Общее количество полей в таблице (опционально)
        pydantic_model: Связанная Pydantic/SQLModel модель (опционально)
        sync_config: Конфигурация синхронизации таблицы
        metadata: Метаданные таблицы (row_count, max_id, etc.)
    """

    def __init__(
        self,
        table_name: str,
        fields: dict[int, FieldDefinition],
        total_fields: int | None = None,
        pydantic_model: type | None = None,
        sync_config: SyncConfig | None = None,
        metadata: TableMetadata | None = None,
    ):
        self.table_name = table_name
        self.fields = fields
        self.total_fields = total_fields
        self.pydantic_model = pydantic_model
        self.sync_config = sync_config or SyncConfig()
        self.metadata = metadata

    @staticmethod
    def auto_generate(
        table_name: str, sample_row: list[Any], field_name_overrides: dict[int, str] | None = None
    ) -> "TableSchema":
        """
        Автоматически генерирует схему на основе образца строки результата.

        Args:
            table_name: Имя таблицы
            sample_row: Строка данных для определения структуры
            field_name_overrides: Словарь {position: name} для ручного задания имен полей

        Returns:
            Автоматически сгенерированная TableSchema
        """
        fields = {}
        total_fields = len(sample_row)
        field_name_overrides = field_name_overrides or {}

        for position, value in enumerate(sample_row):
            # Определить тип поля по значению
            field_type = TableSchema._infer_field_type(value)

            # Проверить есть ли ручное переопределение имени
            if position in field_name_overrides:
                field_name = field_name_overrides[position]
            else:
                # Умное определение имени поля
                field_name = TableSchema._infer_field_name(position, value, field_type)

            # Создать автоматическое определение поля
            field_def = FieldDefinition(
                name=field_name,
                position=position,
                field_type=field_type,
                description="Auto-generated field"
                if position not in field_name_overrides
                else "Manually specified field",
            )

            fields[position] = field_def

        return TableSchema(table_name=table_name, fields=fields, total_fields=total_fields)

    @staticmethod
    def _infer_field_name(position: int, value: Any, field_type: FieldType) -> str:
        """
        Умное определение имени поля на основе позиции, значения и типа.

        Args:
            position: Позиция поля (0-based)
            value: Значение для анализа
            field_type: Определенный тип поля

        Returns:
            Предполагаемое имя поля
        """
        import re

        # Position 0 is almost always an ID field
        if position == 0 and field_type == FieldType.INTEGER:
            return "id"

        # If value is None or not a string, can't do pattern matching
        if value is None or not isinstance(value, str):
            return f"Field_{position}"

        # Pattern detection for string values
        value_str = str(value).strip()

        # Email pattern
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if re.match(email_pattern, value_str):
            return "email"

        # URL pattern
        url_pattern = r"^https?://[^\s]+$"
        if re.match(url_pattern, value_str):
            return "url"

        # UUID pattern
        uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
        if re.match(uuid_pattern, value_str.lower()):
            return "uuid"

        # Phone pattern (basic international format)
        phone_pattern = r"^\+?[1-9]\d{1,14}$"
        if re.match(phone_pattern, value_str.replace(" ", "").replace("-", "")):
            return "phone"

        # If it's a datetime type, use appropriate name
        if field_type == FieldType.DATETIME:
            # Common datetime field names based on position
            if position == 1:
                return "created_at"
            if position == 2:
                return "updated_at"
            return f"timestamp_{position}"

        if field_type == FieldType.DATE:
            return f"date_{position}"

        # Default fallback
        return f"Field_{position}"

    @staticmethod
    def _infer_field_type(value: Any) -> FieldType:
        """Определить тип поля по значению."""
        if value is None:
            return FieldType.UNKNOWN

        value_type = type(value)

        if value_type is int:
            return FieldType.INTEGER
        if value_type is float:
            return FieldType.FLOAT
        if value_type is bool:
            return FieldType.BOOLEAN
        if value_type is str:
            # Попробовать распознать datetime
            try:
                datetime.fromisoformat(value)
                return FieldType.DATETIME
            except (ValueError, AttributeError):
                return FieldType.STRING
        elif value_type in (dict, list):
            return FieldType.JSON
        else:
            return FieldType.UNKNOWN

    def resolve_select_star(self, use_aliases: bool = False) -> list[str]:
        """
        Разворачивает SELECT * в список имён полей.

        Args:
            use_aliases: Использовать алиасы вместо имён БД

        Returns:
            Список имён полей с автогенерацией Field_{n} для неописанных
        """
        if not self.total_fields and not self.fields:
            return ["*"]

        max_position = self.total_fields or (max(self.fields.keys()) + 1 if self.fields else 0)
        result = []

        for pos in range(max_position):
            if pos in self.fields:
                field_def = self.fields[pos]
                if use_aliases:
                    result.append(field_def.mapped_name)
                else:
                    result.append(field_def.name)
            else:
                result.append(f"Field_{pos}")

        return result

    def get_field_by_name(self, name: str) -> FieldDefinition | None:
        """Получить определение поля по имени (ищет по name, alias, python_name)."""
        for field_def in self.fields.values():
            if name in (field_def.name, field_def.alias, field_def.python_name):
                return field_def
        return None

    def get_field_by_position(self, position: int) -> FieldDefinition | None:
        """Получить определение поля по позиции."""
        return self.fields.get(position)

    def map_row_to_dict(self, row: list[Any]) -> dict[str, Any]:
        """
        Маппинг строки результата на словарь с учётом алиасов.
        Применяет трансформеры если они заданы.

        Args:
            row: Строка данных из результата запроса

        Returns:
            Словарь с данными, где ключи - mapped_name полей
        """
        result = {}
        for pos, value in enumerate(row):
            if pos in self.fields:
                field_def = self.fields[pos]
                mapped_name = field_def.mapped_name

                # Применить трансформер если есть и значение не NULL
                if field_def.transformer and value is not None:
                    with suppress(Exception):
                        value = field_def.transformer(value)
                        # Оставить исходное значение при ошибке

                result[mapped_name] = value
            else:
                result[f"Field_{pos}"] = value

        return result

    def map_rows_to_model(self, rows: list[list[Any]]) -> list[Any]:
        """
        Маппинг списка строк на Pydantic/SQLModel модели.

        Args:
            rows: Список строк данных

        Returns:
            Список экземпляров модели или словарей (если модель не задана)
        """
        if not self.pydantic_model:
            return [self.map_row_to_dict(row) for row in rows]

        result = []
        for row in rows:
            data = self.map_row_to_dict(row)
            try:
                model_instance = self.pydantic_model(**data)
                result.append(model_instance)
            except Exception:
                # Fallback к словарю при ошибке создания модели
                result.append(data)

        return result

    def to_dict(self) -> dict[str, Any]:
        """Экспорт схемы в словарь (для сохранения в YAML/JSON)."""
        result = {
            "total_fields": self.total_fields,
            "fields": {
                str(pos): {
                    "name": field.name,
                    "type": field.field_type.value,
                    **({"alias": field.alias} if field.alias else {}),
                    **({"python_name": field.python_name} if field.python_name else {}),
                    **({"description": field.description} if field.description else {}),
                }
                for pos, field in self.fields.items()
            },
        }

        # Добавить sync_config если есть непустые значения
        sync_dict = self.sync_config.to_dict()
        if sync_dict:
            result["sync_config"] = sync_dict

        # Добавить metadata если есть
        if self.metadata:
            result["metadata"] = self.metadata.to_dict()

        return result


class SchemaRegistry:
    """Реестр схем таблиц."""

    def __init__(self):
        self._schemas: dict[str, TableSchema] = {}

    def register(self, schema: TableSchema):
        """Зарегистрировать схему таблицы."""
        self._schemas[schema.table_name] = schema

    def get(self, table_name: str) -> TableSchema | None:
        """Получить схему таблицы."""
        return self._schemas.get(table_name)

    def has(self, table_name: str) -> bool:
        """Проверить наличие схемы."""
        return table_name in self._schemas

    def list_tables(self) -> list[str]:
        """Получить список всех зарегистрированных таблиц."""
        return list(self._schemas.keys())


class SchemaBuilder:
    """Билдер для удобного создания схем таблиц (fluent API)."""

    def __init__(self, table_name: str):
        self.table_name = table_name
        self.fields: dict[int, FieldDefinition] = {}
        self.total_fields: int | None = None
        self.pydantic_model: type | None = None

    def field(
        self,
        position: int,
        name: str,
        *,
        alias: str | None = None,
        python_name: str | None = None,
        field_type: FieldType = FieldType.UNKNOWN,
        description: str | None = None,
        transformer: Callable | None = None,
        validator: Callable | None = None,
    ) -> "SchemaBuilder":
        """Добавить описание поля."""
        self.fields[position] = FieldDefinition(
            name=name,
            position=position,
            alias=alias,
            python_name=python_name,
            field_type=field_type,
            description=description,
            transformer=transformer,
            validator=validator,
        )
        return self

    def set_total_fields(self, count: int) -> "SchemaBuilder":
        """Задать общее количество полей."""
        self.total_fields = count
        return self

    def set_pydantic_model(self, model: type) -> "SchemaBuilder":
        """Связать с Pydantic/SQLModel моделью."""
        self.pydantic_model = model
        return self

    def build(self) -> TableSchema:
        """Построить схему."""
        return TableSchema(
            table_name=self.table_name,
            fields=self.fields,
            total_fields=self.total_fields,
            pydantic_model=self.pydantic_model,
        )


class SchemaLoader:
    """Загрузчик схем из YAML/JSON конфигов."""

    # Встроенные трансформеры
    BUILTIN_TRANSFORMERS = {
        "datetime": lambda x: datetime.fromisoformat(x) if isinstance(x, str) else x,
        "date": lambda x: datetime.fromisoformat(x).date() if isinstance(x, str) else x,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "json": lambda x: json.loads(x) if isinstance(x, str) else x,
    }

    @staticmethod
    def from_yaml(path: str | Path) -> SchemaRegistry:
        """
        Загрузить схемы из YAML файла.

        Args:
            path: Путь к YAML файлу

        Returns:
            SchemaRegistry с загруженными схемами
        """
        if not HAS_YAML:
            raise ImportError("PyYAML is not installed. Install it with: pip install pyyaml")

        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return SchemaLoader._parse_config(data)

    @staticmethod
    def from_json(path: str | Path) -> SchemaRegistry:
        """
        Загрузить схемы из JSON файла.

        Args:
            path: Путь к JSON файлу

        Returns:
            SchemaRegistry с загруженными схемами
        """
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        return SchemaLoader._parse_config(data)

    @staticmethod
    def from_dict(config: dict[str, Any]) -> SchemaRegistry:
        """Загрузить схемы из словаря."""
        return SchemaLoader._parse_config(config)

    @staticmethod
    def _parse_config(config: dict[str, Any]) -> SchemaRegistry:
        """Парсинг конфигурации схем."""
        registry = SchemaRegistry()

        schemas_config = config.get("schemas", {})

        for table_name, table_config in schemas_config.items():
            schema = SchemaLoader._parse_table_schema(table_name, table_config)
            registry.register(schema)

        return registry

    @staticmethod
    def _parse_table_schema(table_name: str, config: dict[str, Any]) -> TableSchema:
        """Парсинг схемы одной таблицы."""
        # Проверить есть ли from_model для автоматической загрузки из Pydantic/SQLModel
        if "from_model" in config:
            return SchemaLoader._load_from_model(table_name, config)

        fields = {}
        total_fields = config.get("total_fields")

        fields_config = config.get("fields", {})
        for pos_str, field_config in fields_config.items():
            position = int(pos_str)

            # Получить тип поля
            field_type_str = field_config.get("type", "unknown")
            try:
                field_type = FieldType(field_type_str)
            except ValueError:
                field_type = FieldType.UNKNOWN

            # Получить трансформер
            transformer = None
            transformer_name = field_config.get("transformer")
            if transformer_name and transformer_name in SchemaLoader.BUILTIN_TRANSFORMERS:
                transformer = SchemaLoader.BUILTIN_TRANSFORMERS[transformer_name]

            # Создать описание поля
            # Use name if provided, otherwise use alias or generate default name
            field_name = field_config.get("name")
            if not field_name:
                # If no name, use alias or generate Field_{position}
                field_name = field_config.get("alias") or f"Field_{position}"

            field_def = FieldDefinition(
                name=field_name,
                position=position,
                alias=field_config.get("alias"),
                python_name=field_config.get("python_name"),
                remote_name=field_config.get("remote_name"),
                field_type=field_type,
                description=field_config.get("description"),
                transformer=transformer,
            )

            fields[position] = field_def

        # Парсинг sync_config
        sync_config = None
        if "sync_config" in config:
            sync_config = SchemaLoader._parse_sync_config(config["sync_config"])

        # Парсинг metadata
        metadata = None
        if "metadata" in config:
            metadata = SchemaLoader._parse_metadata(config["metadata"])

        return TableSchema(
            table_name=table_name,
            fields=fields,
            total_fields=total_fields,
            sync_config=sync_config,
            metadata=metadata,
        )

    @staticmethod
    def _parse_sync_config(config: dict[str, Any]) -> SyncConfig:
        """Парсинг конфигурации синхронизации из YAML."""
        return SyncConfig(
            where=config.get("where"),
            limit=config.get("limit"),
            order_by=config.get("order_by", "id"),
            chunk_size=config.get("chunk_size", 1000),
            enable_chunking=config.get("enable_chunking", True),
            ttl=config.get("ttl"),
            cache_strategy=config.get("cache_strategy", "full"),
            auto_sync=config.get("auto_sync", False),
            sync_interval=config.get("sync_interval"),
            disabled=config.get("disabled", False),
            include_fields=config.get("include_fields"),
            exclude_fields=config.get("exclude_fields"),
            incremental_field=config.get("incremental_field"),
            incremental_mode=config.get("incremental_mode", False),
            prefetch_relationships=config.get("prefetch_relationships", False),
            max_concurrent_chunks=config.get("max_concurrent_chunks", 3),
        )

    @staticmethod
    def _parse_metadata(config: dict[str, Any]) -> TableMetadata:
        """Парсинг метаданных таблицы из YAML."""
        metadata = TableMetadata(
            row_count=config.get("row_count", 0),
            max_id=config.get("max_id"),
            min_id=config.get("min_id"),
            analyzed_at=config.get("analyzed_at"),
            estimated_size_mb=config.get("estimated_size_mb"),
        )

        # Парсинг диапазонов timestamp полей
        for key, value in config.items():
            if key.endswith("_min") or key.endswith("_max"):
                # Извлечь имя поля (убрать _min/_max)
                if key.endswith("_min"):
                    field_name = key[:-4]
                    if field_name not in metadata.timestamp_ranges:
                        metadata.timestamp_ranges[field_name] = {}
                    metadata.timestamp_ranges[field_name]["min"] = value
                elif key.endswith("_max"):
                    field_name = key[:-4]
                    if field_name not in metadata.timestamp_ranges:
                        metadata.timestamp_ranges[field_name] = {}
                    metadata.timestamp_ranges[field_name]["max"] = value

        return metadata

    @staticmethod
    def _load_from_model(table_name: str, config: dict[str, Any]) -> TableSchema:
        """Загрузка схемы из Pydantic/SQLModel модели."""
        model_path = config["from_model"]
        module_path, class_name = model_path.rsplit(".", 1)

        try:
            module = importlib.import_module(module_path)
            model_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            raise ImportError(f"Cannot import model {model_path}: {e}")

        # Получить позиции полей
        if hasattr(model_class, "__field_positions__"):
            positions = model_class.__field_positions__
        else:
            # Позиции из конфига
            fields_config = config.get("fields", {})
            positions = {
                field_config["name"]: int(pos) for pos, field_config in fields_config.items()
            }

        return SchemaExtractor.from_model(
            model=model_class,
            table_name=table_name,
            field_positions=positions,
            total_fields=config.get("total_fields"),
        )


class SchemaExtractor:
    """Извлечение схем из Pydantic/SQLModel моделей."""

    @staticmethod
    def from_pydantic(
        model: type,
        table_name: str,
        field_positions: dict[str, int],
        total_fields: int | None = None,
    ) -> TableSchema:
        """
        Создать схему из Pydantic модели.

        Args:
            model: Pydantic класс
            table_name: Имя таблицы в БД
            field_positions: Словарь {field_name: position}
            total_fields: Общее количество полей в БД

        Returns:
            TableSchema созданная из модели
        """
        if not HAS_PYDANTIC:
            raise ImportError("pydantic is not installed")

        fields = {}

        # Получить информацию о полях модели
        model_fields = model.model_fields

        for field_name, field_info in model_fields.items():
            if field_name not in field_positions:
                continue

            position = field_positions[field_name]

            # Получить алиас из Pydantic Field
            alias = getattr(field_info, "alias", None)

            # Определить тип поля
            field_type = SchemaExtractor._map_python_type_to_field_type(field_info.annotation)

            # Создать описание поля
            field_def = FieldDefinition(
                name=alias or field_name,
                position=position,
                alias=alias,
                python_name=field_name,
                field_type=field_type,
                description=getattr(field_info, "description", None),
            )

            fields[position] = field_def

        return TableSchema(
            table_name=table_name, fields=fields, total_fields=total_fields, pydantic_model=model
        )

    @staticmethod
    def from_sqlmodel(
        model: type, field_positions: dict[str, int], total_fields: int | None = None
    ) -> TableSchema:
        """
        Создать схему из SQLModel модели.

        Args:
            model: SQLModel класс
            field_positions: Словарь {field_name: position}
            total_fields: Общее количество полей

        Returns:
            TableSchema
        """
        if not HAS_SQLMODEL:
            raise ImportError("sqlmodel is not installed")

        table_name = getattr(model, "__tablename__", model.__name__.lower())

        return SchemaExtractor.from_pydantic(
            model=model,
            table_name=table_name,
            field_positions=field_positions,
            total_fields=total_fields,
        )

    @staticmethod
    def from_model(
        model: type,
        table_name: str | None = None,
        field_positions: dict[str, int] | None = None,
        total_fields: int | None = None,
    ) -> TableSchema:
        """
        Универсальный метод для создания схемы из любой модели.
        Автоматически определяет тип модели (SQLModel или Pydantic).
        """
        # Определить тип модели
        if HAS_SQLMODEL and hasattr(model, "__tablename__"):
            return SchemaExtractor.from_sqlmodel(
                model=model, field_positions=field_positions or {}, total_fields=total_fields
            )
        if HAS_PYDANTIC:
            resolved_table_name = table_name or getattr(
                model, "__tablename__", model.__name__.lower()
            )
            return SchemaExtractor.from_pydantic(
                model=model,
                table_name=resolved_table_name,
                field_positions=field_positions or {},
                total_fields=total_fields,
            )
        raise ImportError("Neither pydantic nor sqlmodel is installed")

    @staticmethod
    def _map_python_type_to_field_type(python_type) -> FieldType:
        """Маппинг Python типов на FieldType."""
        # Обработка Optional[X] -> X
        origin = get_origin(python_type)
        if origin is Union:
            args = get_args(python_type)
            # Убрать None из Union (Optional)
            non_none_args = [arg for arg in args if arg is not type(None)]
            if non_none_args:
                python_type = non_none_args[0]

        # Маппинг типов
        type_map = {
            int: FieldType.INTEGER,
            str: FieldType.STRING,
            bool: FieldType.BOOLEAN,
            float: FieldType.FLOAT,
            datetime: FieldType.DATETIME,
            dict: FieldType.JSON,
            list: FieldType.JSON,
        }

        return type_map.get(python_type, FieldType.UNKNOWN)


def schema_config(
    positions: dict[str, int], total_fields: int, registry: SchemaRegistry | None = None
):
    """
    Декоратор для автоматической регистрации схемы из модели.

    Usage:
        @schema_config(
            positions={"id": 0, "name": 1, "email": 2},
            total_fields=10
        )
        class Subscriber(SQLModel, table=True):
            id: int
            name: str
            email: str
    """

    def decorator(model_class):
        # Извлечь схему из модели
        schema = SchemaExtractor.from_model(
            model=model_class, field_positions=positions, total_fields=total_fields
        )

        # Сохранить схему в атрибуте класса
        model_class.__iptvportal_schema__ = schema

        # Автоматически зарегистрировать если указан registry
        if registry:
            registry.register(schema)

        return model_class

    return decorator


# Экспорт публичного API
__all__ = [
    "FieldType",
    "FieldDefinition",
    "TableSchema",
    "SchemaRegistry",
    "SchemaBuilder",
    "SchemaLoader",
    "SchemaExtractor",
    "schema_config",
]
