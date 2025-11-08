"""Query builder with Python DSL and operators."""

from typing import Any


class QueryBuilder:
    """
    Pythonic query builder for IPTVPortal JSONSQL API.
    """
    def __init__(self):
        self._request_id = 1

    def select(
        self,
        data: list[str],
        from_: str,
        where: Any | None = None,
        order_by: str | list[str] | None = None,
        limit: int | None = None,
        offset: int | None = None,
        distinct: bool = False,
        group_by: str | list[str] | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "data": data,
            "from": from_,
        }
        if where:
            params["where"] = where
        if order_by:
            params["order_by"] = order_by
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if distinct:
            params["distinct"] = True
        if group_by:
            params["group_by"] = group_by
        return self._build_request("select", params)
    def insert(
        self,
        into: str,
        columns: list[str],
        values: list[list[Any]],
        returning: str | list[str] | None = None
    ) -> dict[str, Any]:
        params = {
            "into": into,
            "columns": columns,
            "values": values,
        }
        if returning:
            params["returning"] = returning
        return self._build_request("insert", params)
    def update(
        self,
        table: str,
        set_: dict[str, Any],
        where: Any | None = None,
        returning: str | list[str] | None = None
    ) -> dict[str, Any]:
        params = {
            "table": table,
            "set": set_,
        }
        if where:
            params["where"] = where
        if returning:
            params["returning"] = returning
        return self._build_request("update", params)
    def delete(
        self,
        from_: str,
        where: Any | None = None,
        returning: str | list[str] | None = None
    ) -> dict[str, Any]:
        params = {"from": from_}
        if where:
            params["where"] = where
        if returning:
            params["returning"] = returning
        return self._build_request("delete", params)
    def _build_request(self, method: str, params: dict) -> dict:
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": method,
            "params": params,
        }
        self._request_id += 1
        return request

class Field:
    """
    SQLAlchemy-style field for query building.
    """
    def __init__(self, name: str):
        self.name = name
    def __eq__(self, other: Any):
        return {"eq": [self.name, other]}
    def __ne__(self, other: Any):
        return {"neq": [self.name, other]}
    def __gt__(self, other: Any):
        return {"gt": [self.name, other]}
    def __ge__(self, other: Any):
        return {"gte": [self.name, other]}
    def __lt__(self, other: Any):
        return {"lt": [self.name, other]}
    def __le__(self, other: Any):
        return {"lte": [self.name, other]}
    def like(self, pattern: str):
        return {"like": [self.name, pattern]}
    def ilike(self, pattern: str):
        return {"ilike": [self.name, pattern]}
    def in_(self, *values: Any):
        return {"in": [self.name, *values]}
    def contains(self, substr: str):
        return self.ilike(f"%{substr}%")
    def startswith(self, prefix: str):
        return self.ilike(f"{prefix}%")
    def __and__(self, other):
        return {"and": [self, other]}
    def __or__(self, other):
        return {"or": [self, other]}
    def __invert__(self):
        return {"not": [self]}

class Q:
    """
    Django-style Q object for query building.
    """
    def __init__(self, **kwargs):
        self.items = kwargs
    def __and__(self, other):
        return {"and": [self.items, other.items if isinstance(other, Q) else other]}
    def __or__(self, other):
        return {"or": [self.items, other.items if isinstance(other, Q) else other]}
    def __invert__(self):
        return {"not": [self.items]}
    def __repr__(self):
        return f"Q({self.items})"

# Export
__all__ = ["QueryBuilder", "Field", "Q"]
