"""Data-driven validation of remote field mappings using pandas."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

try:
    import pandas as pd

    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False
    pd = None

if TYPE_CHECKING:
    from .async_client import AsyncIPTVPortalClient


class RemoteFieldValidator:
    """
    Валидация маппинга remote полей через сравнение данных с помощью pandas.

    Проверяет соответствие локального field_N и remote-колонки путём:
    - Сравнения sample данных
    - Расчёта match ratio (% совпадающих значений)
    - Определения типа данных через pandas dtype
    - Анализа уникальности, null values, и распределения значений
    """

    def __init__(self, client: "AsyncIPTVPortalClient"):
        """
        Args:
            client: Асинхронный клиент для выполнения запросов
        """
        if not HAS_PANDAS:
            raise ImportError("pandas is required for RemoteFieldValidator. Install with: pip install pandas")
        self.client = client

    async def validate_field_mapping(
        self,
        table_name: str,
        local_position: int,
        remote_column_name: str,
        sample_size: int = 1000,
    ) -> dict[str, Any]:
        """
        Валидация маппинга между локальной позицией поля и remote колонкой.

        Args:
            table_name: Имя таблицы
            local_position: Позиция поля в локальной схеме (0-based)
            remote_column_name: Имя колонки в удалённой схеме
            sample_size: Размер выборки для валидации

        Returns:
            Словарь с метаданными валидации:
            {
                "match_ratio": float,  # Процент совпадающих значений (0.0-1.0)
                "sample_size": int,    # Размер выборки
                "validated_at": str,   # Timestamp валидации (ISO format)
                "dtype": str,          # pandas dtype
                "null_count": int,     # Количество NULL значений
                "unique_count": int,   # Количество уникальных значений
                "min_value": Any,      # Минимальное значение (для числовых/дат)
                "max_value": Any,      # Максимальное значение (для числовых/дат)
                "remote_column": str,  # Имя remote колонки
            }
        """
        from .jsonsql import SQLTranspiler

        transpiler = SQLTranspiler()

        # Получить образец данных с двумя запросами:
        # 1. SELECT * для получения данных по позиции
        sql_all = f"SELECT * FROM {table_name} LIMIT {sample_size}"
        jsonsql_all = transpiler.transpile(sql_all)
        query_all = {"jsonrpc": "2.0", "id": 1, "method": "select", "params": jsonsql_all}

        # 2. SELECT remote_column для сравнения
        sql_remote = f"SELECT {remote_column_name} FROM {table_name} LIMIT {sample_size}"
        jsonsql_remote = transpiler.transpile(sql_remote)
        query_remote = {"jsonrpc": "2.0", "id": 2, "method": "select", "params": jsonsql_remote}

        try:
            # Выполнить запросы
            result_all = await self.client.execute(query_all)
            result_remote = await self.client.execute(query_remote)

            if not result_all or not result_remote:
                raise ValueError(f"Empty result from table '{table_name}'")

            # Извлечь данные по позиции из SELECT *
            local_values = [row[local_position] if len(row) > local_position else None for row in result_all]

            # Извлечь данные из SELECT remote_column
            remote_values = [row[0] if row else None for row in result_remote]

            # Создать pandas Series для анализа
            local_series = pd.Series(local_values, name=f"field_{local_position}")
            remote_series = pd.Series(remote_values, name=remote_column_name)

            # Расчёт match ratio
            # Сравниваем значения, учитывая None/NaN
            matches = 0
            total = min(len(local_values), len(remote_values))

            for i in range(total):
                local_val = local_values[i]
                remote_val = remote_values[i]

                # Считаем совпадением если оба None или значения равны
                if (local_val is None and remote_val is None) or (
                    local_val is not None and remote_val is not None and local_val == remote_val
                ):
                    matches += 1

            match_ratio = matches / total if total > 0 else 0.0

            # Анализ данных через pandas
            dtype_str = str(remote_series.dtype)
            null_count = int(remote_series.isna().sum())
            unique_count = int(remote_series.nunique())

            # Определить min/max для числовых и datetime типов
            min_value = None
            max_value = None

            if pd.api.types.is_numeric_dtype(remote_series):
                min_value = float(remote_series.min()) if not pd.isna(remote_series.min()) else None
                max_value = float(remote_series.max()) if not pd.isna(remote_series.max()) else None
            elif pd.api.types.is_datetime64_any_dtype(remote_series):
                min_value = str(remote_series.min()) if not pd.isna(remote_series.min()) else None
                max_value = str(remote_series.max()) if not pd.isna(remote_series.max()) else None

            return {
                "match_ratio": match_ratio,
                "sample_size": total,
                "validated_at": datetime.now().isoformat(),
                "dtype": dtype_str,
                "null_count": null_count,
                "unique_count": unique_count,
                "min_value": min_value,
                "max_value": max_value,
                "remote_column": remote_column_name,
            }

        except Exception as e:
            raise ValueError(f"Failed to validate field mapping for '{remote_column_name}': {e}") from e

    def infer_field_type_from_dtype(self, dtype_str: str) -> str:
        """
        Определить FieldType из pandas dtype.

        Args:
            dtype_str: Строка с pandas dtype (например, 'int64', 'float64', 'object', 'datetime64[ns]')

        Returns:
            Строковое представление FieldType
        """
        dtype_lower = dtype_str.lower()

        if "int" in dtype_lower:
            return "integer"
        if "float" in dtype_lower or "double" in dtype_lower:
            return "float"
        if "bool" in dtype_lower:
            return "boolean"
        if "datetime" in dtype_lower or "timestamp" in dtype_lower:
            return "datetime"
        if "date" in dtype_lower and "datetime" not in dtype_lower:
            return "date"
        if "object" in dtype_lower or "string" in dtype_lower:
            return "string"
        return "unknown"

    async def validate_table_schema(
        self,
        table_name: str,
        field_mappings: dict[int, str],
        sample_size: int = 1000,
    ) -> dict[int, dict[str, Any]]:
        """
        Валидация всей схемы таблицы (множественные поля).

        Args:
            table_name: Имя таблицы
            field_mappings: Словарь {local_position: remote_column_name}
            sample_size: Размер выборки для валидации

        Returns:
            Словарь {position: validation_metadata}
        """
        results = {}

        for position, remote_col in field_mappings.items():
            try:
                validation_result = await self.validate_field_mapping(
                    table_name=table_name,
                    local_position=position,
                    remote_column_name=remote_col,
                    sample_size=sample_size,
                )
                results[position] = validation_result
            except Exception as e:
                print(f"Warning: Validation failed for position {position} -> {remote_col}: {e}")
                results[position] = {
                    "error": str(e),
                    "validated_at": datetime.now().isoformat(),
                    "remote_column": remote_col,
                }

        return results


__all__ = ["RemoteFieldValidator"]
