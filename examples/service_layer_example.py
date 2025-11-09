"""Example: Using the new QueryService API for query execution.

This example demonstrates the new service layer architecture that provides
cleaner separation of concerns and easier testing.
"""

from iptvportal import (
    IPTVPortalClient,
    IPTVPortalSettings,
    QueryService,
    SQLQueryInput,
)


def main():
    """Example of using QueryService for SQL queries."""
    
    # 1. Setup configuration
    settings = IPTVPortalSettings(
        api_url="https://api.example.com",
        username="your_username",
        password="your_password",  # Use environment variables in production!
        enable_query_cache=True,
        auto_order_by_id=True,
    )
    
    # 2. Create client (infrastructure layer)
    client = IPTVPortalClient(settings)
    
    # 3. Create service (business logic layer)
    service = QueryService(client)
    
    # 4. Execute queries using the service
    with client:
        # Example 1: Simple SELECT query
        print("=" * 60)
        print("Example 1: Simple SELECT with schema mapping")
        print("=" * 60)
        
        query_input = SQLQueryInput(
            sql="SELECT id, username, email FROM subscriber WHERE disabled = false LIMIT 5",
            use_schema_mapping=True,
            use_cache=True,
        )
        
        result = service.execute_sql(query_input)
        
        print(f"Query: {result.sql}")
        print(f"Method: {result.method}")
        print(f"Table: {result.table}")
        print(f"Rows: {result.row_count}")
        print(f"Time: {result.execution_time_ms:.2f}ms")
        print(f"Data preview: {result.data[:2]}")  # First 2 rows
        
        # Example 2: Dry-run mode (transpile without executing)
        print("\n" + "=" * 60)
        print("Example 2: Dry-run mode (transpile only)")
        print("=" * 60)
        
        query_input = SQLQueryInput(
            sql="SELECT COUNT(*) as total FROM subscriber",
            dry_run=True,
        )
        
        result = service.execute_sql(query_input)
        
        print(f"Query: {result.sql}")
        print(f"JSONSQL: {result.jsonsql}")
        print(f"Would execute on table: {result.table}")
        print("(Query not executed due to dry_run=True)")
        
        # Example 3: Complex query with joins
        print("\n" + "=" * 60)
        print("Example 3: JOIN query")
        print("=" * 60)
        
        query_input = SQLQueryInput(
            sql="""
                SELECT 
                    s.id, 
                    s.username, 
                    t.mac_addr, 
                    t.model
                FROM subscriber s
                LEFT JOIN terminal t ON s.id = t.subscriber_id
                WHERE s.disabled = false
                LIMIT 10
            """,
            use_schema_mapping=True,
        )
        
        result = service.execute_sql(query_input)
        
        print(f"Method: {result.method}")
        print(f"Rows: {result.row_count}")
        print(f"Time: {result.execution_time_ms:.2f}ms")
        print(f"First result: {result.data[0] if result.data else 'No data'}")


# Alternative: Using the traditional client API (still supported!)
def traditional_api_example():
    """Example using the traditional IPTVPortalClient API."""
    
    settings = IPTVPortalSettings(
        api_url="https://api.example.com",
        username="your_username",
        password="your_password",
    )
    
    client = IPTVPortalClient(settings)
    
    with client:
        # Execute JSONSQL directly
        result = client.execute({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "select",
            "params": {
                "data": ["id", "username"],
                "from": "subscriber",
                "limit": 5
            }
        })
        
        print(f"Result: {result}")


# Comparison: Old vs New API
def api_comparison():
    """Compare old client-based API vs new service-based API."""
    
    settings = IPTVPortalSettings()
    client = IPTVPortalClient(settings)
    
    with client:
        # OLD WAY: Direct client usage (still works!)
        print("OLD API (still supported):")
        print("-" * 40)
        from iptvportal.jsonsql import SQLTranspiler
        
        transpiler = SQLTranspiler()
        jsonsql = transpiler.transpile("SELECT * FROM subscriber LIMIT 5")
        result = client.execute({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "select",
            "params": jsonsql
        })
        print(f"Rows: {len(result)}")
        
        # NEW WAY: Service layer (recommended!)
        print("\nNEW API (recommended):")
        print("-" * 40)
        service = QueryService(client)
        
        query_input = SQLQueryInput(
            sql="SELECT * FROM subscriber LIMIT 5",
            use_schema_mapping=True
        )
        result = service.execute_sql(query_input)
        
        print(f"Rows: {result.row_count}")
        print(f"Method: {result.method}")
        print(f"Table: {result.table}")
        print(f"Time: {result.execution_time_ms:.2f}ms")


if __name__ == "__main__":
    print("IPTVPORTAL CLIENT - Service Layer Example")
    print("=" * 60)
    print()
    print("This example requires valid credentials.")
    print("Set IPTVPORTAL_USERNAME and IPTVPORTAL_PASSWORD environment variables.")
    print()
    
    # Uncomment to run:
    # main()
    # traditional_api_example()
    # api_comparison()
    
    print("Examples defined. Uncomment function calls to run.")
