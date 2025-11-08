"""Schema introspection from remote tables with automatic metadata gathering."""

from typing import Optional, Dict, Any, List, TYPE_CHECKING
from datetime import datetime
import asyncio

from .schema import (
    TableSchema,
    FieldDefinition,
    FieldType,
    SyncConfig,
    TableMetadata
)

if TYPE_CHECKING:
    from .async_client import AsyncIPTVPortalClient


class SchemaIntrospector:
    """
    Интроспекция удалённых таблиц с автоматическим сбором метаданных.
    
    Возможности:
    - Определение структуры таблицы через SELECT * LIMIT 1
    - Подсчёт количества строк (COUNT(*))
    - Определение MAX(id), MIN(id)
    - Диапазоны timestamp полей
    - Умная генерация sync_config на основе метаданных
    """
    
    def __init__(self, client: 'AsyncIPTVPortalClient'):
        """
        Args:
            client: Асинхронный клиент для выполнения запросов
        """
        self.client = client
    
    async def introspect_table(
        self,
        table_name: str,
        gather_metadata: bool = True,
        field_name_overrides: Optional[Dict[int, str]] = None
    ) -> TableSchema:
        """
        Интроспекция таблицы с автоматической генерацией схемы.
        
        Args:
            table_name: Имя таблицы для анализа
            gather_metadata: Собирать ли метаданные (row_count, max_id, etc.)
            field_name_overrides: Ручное переопределение имён полей {position: name}
            
        Returns:
            TableSchema с автоматически определённой структурой и метаданными
            
        Raises:
            ValueError: Если таблица пустая или не существует
        """
        # 1. Получить структуру таблицы через образец строки
        # Note: API expects "data" key for SELECT fields, not "select"
        sample_query = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "select",
            "params": {
                "data": ["*"],
                "from": table_name,
                "limit": 1
            }
        }
        
        try:
            sample_result = await self.client.execute(sample_query)
        except Exception as e:
            raise ValueError(f"Failed to query table '{table_name}': {e}") from e
        
        if not sample_result or len(sample_result) == 0:
            raise ValueError(f"Table '{table_name}' is empty or doesn't exist")
        
        sample_row = sample_result[0]
        total_fields = len(sample_row)
        
        # 2. Автоматическая генерация определений полей
        fields = {}
        field_name_overrides = field_name_overrides or {}
        
        for position, value in enumerate(sample_row):
            field_type = self._infer_field_type(value)
            
            # Проверить ручное переопределение
            if position in field_name_overrides:
                field_name = field_name_overrides[position]
                description = "Manually specified field"
            else:
                field_name = self._infer_field_name(position, value, field_type)
                description = "Auto-detected field"
            
            fields[position] = FieldDefinition(
                name=field_name,
                position=position,
                field_type=field_type,
                description=description
            )
        
        # 3. Собрать метаданные (если включено)
        metadata = None
        if gather_metadata:
            metadata = await self._gather_metadata(table_name, fields)
        
        # 4. Сгенерировать умную конфигурацию синхронизации
        sync_config = self._generate_sync_config(
            table_name=table_name,
            metadata=metadata,
            fields=fields
        )
        
        return TableSchema(
            table_name=table_name,
            fields=fields,
            total_fields=total_fields,
            sync_config=sync_config,
            metadata=metadata
        )
    
    async def _gather_metadata(
        self,
        table_name: str,
        fields: Dict[int, FieldDefinition]
    ) -> TableMetadata:
        """
        Сбор метаданных таблицы.
        
        Собирает:
        - Количество строк (COUNT(*))
        - MAX(id), MIN(id) если есть поле id
        - Диапазоны timestamp полей (MIN/MAX)
        """
        metadata = TableMetadata()
        metadata.analyzed_at = datetime.now().isoformat()
        
        # Подсчёт строк
        try:
            count_query = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "select",
                "params": {
                    "data": ["COUNT(*)"],
                    "from": table_name
                }
            }
            count_result = await self.client.execute(count_query)
            if count_result and len(count_result) > 0:
                metadata.row_count = int(count_result[0][0]) if count_result[0][0] is not None else 0
        except Exception as e:
            print(f"Warning: Could not count rows: {e}")
            metadata.row_count = 0
        
        # Получить MAX(id) и MIN(id) если есть поле id
        id_field = next((f for f in fields.values() if f.name == 'id'), None)
        if id_field:
            try:
                id_stats_query = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "select",
                    "params": {
                        "data": ["MAX(id)", "MIN(id)"],
                        "from": table_name
                    }
                }
                id_result = await self.client.execute(id_stats_query)
                if id_result and len(id_result) > 0:
                    max_id = id_result[0][0]
                    min_id = id_result[0][1]
                    metadata.max_id = int(max_id) if max_id is not None else None
                    metadata.min_id = int(min_id) if min_id is not None else None
            except Exception as e:
                print(f"Warning: Could not get ID statistics: {e}")
        
        # Найти timestamp поля и получить их диапазоны
        timestamp_fields = [
            f for f in fields.values()
            if f.field_type in (FieldType.DATETIME, FieldType.DATE)
        ]
        
        for idx, ts_field in enumerate(timestamp_fields, start=4):
            try:
                range_query = {
                    "jsonrpc": "2.0",
                    "id": idx,
                    "method": "select",
                    "params": {
                        "data": [
                            f"MIN({ts_field.name})",
                            f"MAX({ts_field.name})"
                        ],
                        "from": table_name
                    }
                }
                range_result = await self.client.execute(range_query)
                if range_result and len(range_result) > 0:
                    min_val = range_result[0][0]
                    max_val = range_result[0][1]
                    
                    if min_val is not None or max_val is not None:
                        metadata.timestamp_ranges[ts_field.name] = {
                            'min': str(min_val) if min_val else None,
                            'max': str(max_val) if max_val else None
                        }
            except Exception as e:
                print(f"Warning: Could not get range for {ts_field.name}: {e}")
        
        return metadata
    
    def _generate_sync_config(
        self,
        table_name: str,
        metadata: Optional[TableMetadata],
        fields: Dict[int, FieldDefinition]
    ) -> SyncConfig:
        """
        Генерация умной конфигурации синхронизации на основе метаданных.
        
        Учитывает:
        - Размер таблицы (row_count) для определения chunk_size
        - Наличие полей deleted_at, disabled, archived для WHERE
        - Наличие updated_at для incremental sync
        """
        # Значения по умолчанию если нет метаданных
        if not metadata:
            return SyncConfig()
        
        row_count = metadata.row_count or 0
        
        # Умные значения по умолчанию на основе размера таблицы
        if row_count < 1000:
            # Маленькая таблица: синхронизировать всё сразу
            chunk_size = max(row_count, 100)
            cache_strategy = 'full'
            auto_sync = True
            ttl = 3600  # 1 час
        elif row_count < 100000:
            # Средняя таблица: разумные чанки
            chunk_size = 5000
            cache_strategy = 'full'
            auto_sync = True
            ttl = 1800  # 30 минут
        else:
            # Большая таблица: консервативный подход
            chunk_size = 10000
            cache_strategy = 'incremental'
            auto_sync = False
            ttl = 600  # 10 минут
        
        # Определить WHERE clause на основе флаговых полей
        where_clauses = []
        
        # Проверить поле deleted_at (soft deletes)
        deleted_field = next(
            (f for f in fields.values() if 'deleted' in f.name.lower()),
            None
        )
        if deleted_field:
            where_clauses.append(f"{deleted_field.name} IS NULL")
        
        # Проверить поля disabled/archived/active
        flag_field = next(
            (f for f in fields.values() 
             if f.name.lower() in ('disabled', 'archived') and f.field_type == FieldType.BOOLEAN),
            None
        )
        if flag_field:
            # Для disabled/archived - FALSE, для active - TRUE
            if flag_field.name.lower() in ('disabled', 'archived'):
                where_clauses.append(f"{flag_field.name} = false")
            else:
                where_clauses.append(f"{flag_field.name} = true")
        
        where_clause = " AND ".join(where_clauses) if where_clauses else None
        
        # Определить incremental sync если есть updated_at
        incremental_field = None
        incremental_mode = False
        
        update_field = next(
            (f for f in fields.values() 
             if f.name.lower() in ('updated_at', 'modified_at', 'update_time')
             and f.field_type == FieldType.DATETIME),
            None
        )
        if update_field and row_count > 10000:
            # Включить incremental sync для больших таблиц с updated_at
            incremental_field = update_field.name
            incremental_mode = True
            cache_strategy = 'incremental'
        
        # Ограничение на синхронизацию (2x от текущего размера)
        limit = int(row_count * 2) if row_count > 0 else None
        
        return SyncConfig(
            where=where_clause,
            limit=limit,
            order_by="id",
            chunk_size=chunk_size,
            cache_strategy=cache_strategy,
            auto_sync=auto_sync,
            ttl=ttl,
            incremental_field=incremental_field,
            incremental_mode=incremental_mode
        )
    
    @staticmethod
    def _infer_field_type(value: Any) -> FieldType:
        """Определить тип поля по значению."""
        if value is None:
            return FieldType.UNKNOWN
        
        value_type = type(value)
        
        if value_type == int:
            return FieldType.INTEGER
        elif value_type == float:
            return FieldType.FLOAT
        elif value_type == bool:
            return FieldType.BOOLEAN
        elif value_type == str:
            # Попробовать определить datetime
            try:
                datetime.fromisoformat(value)
                return FieldType.DATETIME
            except (ValueError, AttributeError):
                return FieldType.STRING
        elif value_type in (dict, list):
            return FieldType.JSON
        else:
            return FieldType.UNKNOWN
    
    @staticmethod
    def _infer_field_name(position: int, value: Any, field_type: FieldType) -> str:
        """
        Умное определение имени поля.
        
        Args:
            position: Позиция поля (0-based)
            value: Значение для анализа паттернов
            field_type: Определённый тип поля
            
        Returns:
            Предполагаемое имя поля
        """
        import re
        
        # Позиция 0 почти всегда ID
        if position == 0 and field_type == FieldType.INTEGER:
            return "id"
        
        # Если значение не строка, не можем использовать паттерны
        if value is None or not isinstance(value, str):
            return f"Field_{position}"
        
        value_str = str(value).strip()
        
        # Email паттерн
        if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', value_str):
            return "email"
        
        # URL паттерн
        if re.match(r'^https?://[^\s]+$', value_str):
            return "url"
        
        # UUID паттерн
        if re.match(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', value_str.lower()):
            return "uuid"
        
        # Телефон паттерн
        phone_clean = value_str.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if re.match(r'^\+?[1-9]\d{1,14}$', phone_clean):
            return "phone"
        
        # Datetime поля
        if field_type == FieldType.DATETIME:
            if position == 1:
                return "created_at"
            elif position == 2:
                return "updated_at"
            else:
                return f"timestamp_{position}"
        
        if field_type == FieldType.DATE:
            return f"date_{position}"
        
        # По умолчанию
        return f"Field_{position}"
    
    async def introspect_all_tables(
        self,
        table_names: List[str],
        gather_metadata: bool = True
    ) -> Dict[str, TableSchema]:
        """
        Интроспекция нескольких таблиц параллельно.
        
        Args:
            table_names: Список имён таблиц
            gather_metadata: Собирать ли метаданные
            
        Returns:
            Словарь {table_name: TableSchema}
        """
        tasks = [
            self.introspect_table(table_name, gather_metadata)
            for table_name in table_names
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        schemas = {}
        for table_name, result in zip(table_names, results):
            if isinstance(result, Exception):
                print(f"Error introspecting {table_name}: {result}")
            else:
                schemas[table_name] = result
        
        return schemas


__all__ = ['SchemaIntrospector']
