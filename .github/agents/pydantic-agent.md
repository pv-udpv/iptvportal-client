# Pydantic Agent

**Pydantic Model Generation Specialist**

## Responsibilities

- Generate Pydantic models from table schemas with full type hints
- Automate type inference and validation rules
- Ensure mypy strict compliance
- Generate Google-style docstrings for all models and fields
- Integrate models with transport layer and resource managers
- Validate generated models for correctness and completeness

## When to Use

Use this agent when:
- Creating new data models from database schemas
- Generating request/response models for API endpoints
- Adding validation models for user input
- Updating existing models with new fields or validation rules
- Ensuring strict type safety across the codebase

## Tools

### 1. `pydantic-schema` (Primary Tool)
**Purpose**: Generate Pydantic models from table schemas with automated type inference

**Capabilities**:
- Parses YAML/JSON schema definitions
- Generates Pydantic BaseModel classes with proper type hints
- Infers field types from schema metadata (INTEGER → int, STRING → str, etc.)
- Handles Optional types for nullable fields
- Creates Field() validators with constraints
- Generates nested models for relationships
- Adds comprehensive Google-style docstrings

**Input**: Table schema (TableSchema object or YAML file)
**Output**: Python code with Pydantic model definitions

**Example**:
```python
# Input: subscriber schema
class Subscriber(BaseModel):
    """Subscriber account model.
    
    Represents a subscriber account in the IPTVPortal system.
    
    Attributes:
        id: Unique subscriber identifier
        username: Login username, must be unique
        email: Contact email address
        disabled: Account active/disabled status
        created_at: Account creation timestamp
    """
    
    id: int = Field(..., description="Unique subscriber identifier")
    username: str = Field(..., min_length=3, max_length=50, description="Login username")
    email: str | None = Field(None, description="Contact email address")
    disabled: bool = Field(False, description="Account disabled flag")
    created_at: datetime = Field(default_factory=datetime.now, description="Creation timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )
```

### 2. `schema-validator`
**Purpose**: Validate generated Pydantic models for correctness

**Checks**:
- All fields have type hints
- Optional types are properly marked
- Field validators are present where needed
- Docstrings follow Google style guide
- Model configuration is appropriate
- No mypy errors in strict mode

**Input**: Generated model code
**Output**: Validation report with errors/warnings

### 3. `integration-checker`
**Purpose**: Verify model integration with transport and resource managers

**Checks**:
- Models are importable from appropriate modules
- Transport layer can serialize/deserialize models
- Resource managers use models correctly
- Request/response models match API contracts
- Models work with existing query builders

**Input**: Model module and dependent code
**Output**: Integration status report

## Workflow

### Standard Model Generation Flow

1. **Analyze Schema**
   ```bash
   # Use SchemaIntrospector to gather table metadata
   # Identify field types, constraints, relationships
   ```

2. **Generate Model**
   ```bash
   # Use pydantic-schema tool to generate BaseModel class
   # Include all fields with proper types and validators
   # Add comprehensive docstrings
   ```

3. **Validate Model**
   ```bash
   # Run schema-validator to check for issues
   # Run mypy in strict mode: mypy --strict src/iptvportal/models/
   # Fix any type errors or validation issues
   ```

4. **Integration Check**
   ```bash
   # Use integration-checker to verify compatibility
   # Test with transport layer (httpx serialization)
   # Test with resource managers (CRUD operations)
   ```

5. **Generate Tests**
   ```bash
   # Create comprehensive pytest tests for the model
   # Test field validation, constraints, edge cases
   # Test serialization/deserialization
   ```

## Code Standards

### Type Hints
- **REQUIRED**: All fields must have explicit type hints
- Use `str | None` instead of `Optional[str]` (Python 3.10+ syntax)
- Use `list[Type]` and `dict[K, V]` instead of `List` and `Dict`
- Import from `__future__` if needed for forward references

### Field Definitions
```python
from pydantic import BaseModel, Field, field_validator, ConfigDict

class ExampleModel(BaseModel):
    """Model description.
    
    Longer description if needed.
    
    Attributes:
        field_name: Field description
    """
    
    # Required field with validation
    field_name: str = Field(..., min_length=1, max_length=100, description="Field description")
    
    # Optional field with default
    optional_field: int | None = Field(None, ge=0, description="Optional field")
    
    @field_validator('field_name')
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        """Validate field_name is not empty.
        
        Args:
            v: Field value to validate
            
        Returns:
            Validated field value
            
        Raises:
            ValueError: If validation fails
        """
        if not v.strip():
            raise ValueError("field_name cannot be empty")
        return v.strip()
    
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
    )
```

### Docstrings (Google Style)
```python
"""Short one-line summary.

Extended description paragraph. Can contain multiple sentences
explaining the purpose, behavior, and usage of the model.

Attributes:
    field1: Description of field1
    field2: Description of field2
        Can span multiple lines if needed
        
Example:
    >>> model = ExampleModel(field1="value", field2=42)
    >>> model.field1
    'value'
    
Note:
    Any additional notes or warnings.
"""
```

### mypy Strict Compliance
All generated models MUST pass:
```bash
mypy --strict --no-error-summary src/iptvportal/models/
```

Common strict mode requirements:
- No `Any` types without explicit annotation
- All functions have return type annotations
- All parameters have type annotations
- No implicit `Optional` (use explicit `| None`)

## Integration Points

### 1. Schema System
Located in `src/iptvportal/schema/`:
- `table.py`: TableSchema, FieldDefinition, FieldType
- `introspector.py`: SchemaIntrospector for metadata
- `codegen.py`: ORMGenerator (existing, extend for Pydantic v2 features)

### 2. Models Module
Located in `src/iptvportal/models/`:
- `requests.py`: Request validation models
- `responses.py`: Response models
- Add new modules as needed for domain models

### 3. Transport Layer
Located in `src/iptvportal/core/`:
- `client.py`: Sync HTTP client
- `async_client.py`: Async HTTP client
- Models must be serializable with `model_dump()` and `model_validate()`

### 4. Resource Managers
Located in `src/iptvportal/service/`:
- Resource managers use models for type-safe operations
- Models integrate with query builders

## Testing Requirements

All generated models MUST have:

1. **Basic Tests** (`tests/test_models.py` or dedicated file)
   ```python
   def test_model_creation():
       """Test basic model creation."""
       model = MyModel(field1="value", field2=42)
       assert model.field1 == "value"
       assert model.field2 == 42
   ```

2. **Validation Tests**
   ```python
   def test_model_validation():
       """Test field validation."""
       with pytest.raises(ValidationError):
           MyModel(field1="", field2=-1)  # Invalid values
   ```

3. **Serialization Tests**
   ```python
   def test_model_serialization():
       """Test JSON serialization."""
       model = MyModel(field1="value", field2=42)
       data = model.model_dump()
       assert data == {"field1": "value", "field2": 42}
       
       # Test deserialization
       restored = MyModel.model_validate(data)
       assert restored == model
   ```

4. **Type Checking Test**
   ```python
   def test_mypy_compliance():
       """Ensure model passes mypy strict checks."""
       # This is checked in CI, but document expected behavior
       pass
   ```

## Quality Gates

Before considering a model complete:

- [ ] Model passes `mypy --strict` with zero errors
- [ ] All fields have type hints and descriptions
- [ ] Google-style docstrings are present and complete
- [ ] Field validators are implemented for business logic
- [ ] Model configuration is appropriate (from_attributes, etc.)
- [ ] Tests achieve 100% coverage for the model
- [ ] Integration tests pass with transport layer
- [ ] Integration tests pass with resource managers (if applicable)
- [ ] Documentation is updated (README, API reference)
- [ ] No ruff linting errors

## Examples

### From Schema to Model

**Input Schema** (YAML):
```yaml
subscriber:
  total_fields: 5
  fields:
    0:
      name: id
      type: integer
      description: Subscriber ID
      constraints:
        primary_key: true
        nullable: false
    1:
      name: username
      type: string
      description: Login name
      constraints:
        unique: true
        nullable: false
    2:
      name: email
      type: string
      description: Email address
      constraints:
        nullable: true
    3:
      name: disabled
      type: boolean
      description: Account disabled flag
      constraints:
        nullable: false
    4:
      name: created_at
      type: datetime
      description: Creation timestamp
      constraints:
        nullable: false
```

**Generated Model**:
```python
"""Subscriber models for IPTVPortal."""

from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class Subscriber(BaseModel):
    """Subscriber account model.
    
    Represents a subscriber account in the IPTVPortal system with authentication
    credentials and account status.
    
    Attributes:
        id: Unique subscriber identifier
        username: Login username, must be unique across all subscribers
        email: Contact email address for notifications
        disabled: Account active/disabled status
        created_at: Account creation timestamp
        
    Example:
        >>> subscriber = Subscriber(
        ...     id=1,
        ...     username="john_doe",
        ...     email="john@example.com",
        ...     disabled=False,
        ...     created_at=datetime.now()
        ... )
        >>> subscriber.username
        'john_doe'
    """
    
    id: int = Field(..., description="Unique subscriber identifier", ge=1)
    username: str = Field(
        ...,
        min_length=3,
        max_length=50,
        description="Login username, must be unique"
    )
    email: str | None = Field(None, description="Contact email address")
    disabled: bool = Field(False, description="Account disabled flag")
    created_at: datetime = Field(..., description="Account creation timestamp")
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username format.
        
        Ensures username contains only allowed characters and is properly formatted.
        
        Args:
            v: Username to validate
            
        Returns:
            Validated and normalized username
            
        Raises:
            ValueError: If username format is invalid
        """
        if not v.strip():
            raise ValueError("Username cannot be empty or whitespace")
        
        # Normalize
        normalized = v.strip().lower()
        
        # Check allowed characters
        if not normalized.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        
        return normalized
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Validate email format if provided.
        
        Args:
            v: Email address to validate
            
        Returns:
            Validated email or None
            
        Raises:
            ValueError: If email format is invalid
        """
        if v is None:
            return None
        
        email = v.strip().lower()
        if '@' not in email or '.' not in email.split('@')[1]:
            raise ValueError("Invalid email format")
        
        return email
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )
```

## Tips

1. **Start Simple**: Generate basic model first, then add validators
2. **Use Existing Patterns**: Follow patterns from `models/requests.py` and `models/responses.py`
3. **Leverage Schema System**: Use `SchemaIntrospector` to gather metadata automatically
4. **Test Early**: Write tests alongside model generation
5. **Iterate**: Run mypy and tests frequently during development
6. **Document**: Add docstrings as you write code, not after

## Related Agents

- **API Integration Agent**: Uses generated models for API endpoints
- **Resource Manager Agent**: Integrates models with CRUD operations
- **Testing Agent**: Creates comprehensive test suites for models
- **Documentation Agent**: Updates API reference and examples

## References

- [Pydantic v2 Documentation](https://docs.pydantic.dev/latest/)
- [Google Python Style Guide - Docstrings](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)
- [mypy Documentation - Strict Mode](https://mypy.readthedocs.io/en/stable/command_line.html#cmdoption-mypy-strict)
- Project: `src/iptvportal/schema/codegen.py` (existing ORM generator)
- Project: `src/iptvportal/models/` (existing models)
