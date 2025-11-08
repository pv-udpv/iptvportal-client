"""Configuration inspection and generation tool.

This module provides functionality to scan Python modules for settings classes
(Pydantic BaseSettings, dynaconf configurations) and generate configuration files
based on discovered settings.
"""

import ast
import inspect
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class FieldInfo(BaseModel):
    """Information about a configuration field."""
    
    name: str
    type: str
    default: Any = None
    description: str = ""
    required: bool = False


class SettingsClassInfo(BaseModel):
    """Information about a discovered settings class."""
    
    module: str
    class_name: str
    base_class: str
    fields: list[FieldInfo]
    docstring: str = ""


def discover_settings_classes(
    scope: Path,
    ignore_patterns: list[str] | None = None
) -> list[SettingsClassInfo]:
    """Discover settings classes in Python modules.
    
    Args:
        scope: Directory to start scanning from
        ignore_patterns: List of patterns to ignore (e.g., ['test_*', '__pycache__'])
        
    Returns:
        List of discovered settings class information
    """
    settings_classes = []
    ignore_patterns = ignore_patterns or ["test_*", "__pycache__", ".*"]
    
    for py_file in scope.rglob("*.py"):
        # Check ignore patterns
        should_ignore = False
        for pattern in ignore_patterns:
            if py_file.match(pattern) or any(part.startswith('.') for part in py_file.parts):
                should_ignore = True
                break
        
        if should_ignore:
            continue
        
        try:
            # Parse the Python file
            content = py_file.read_text()
            tree = ast.parse(content)
            
            # Find class definitions that inherit from BaseSettings
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it inherits from BaseSettings or similar
                    base_names = []
                    for base in node.bases:
                        if isinstance(base, ast.Name):
                            base_names.append(base.id)
                        elif isinstance(base, ast.Attribute):
                            base_names.append(base.attr)
                    
                    if any(name in ["BaseSettings", "Settings", "LazySettings"] for name in base_names):
                        # Extract class information
                        class_info = _extract_class_info(node, py_file, content)
                        if class_info:
                            settings_classes.append(class_info)
        
        except Exception as e:
            # Skip files that can't be parsed
            continue
    
    return settings_classes


def _extract_class_info(node: ast.ClassDef, file_path: Path, content: str) -> SettingsClassInfo | None:
    """Extract information from a settings class AST node."""
    try:
        # Get module path - handle both absolute and relative paths
        try:
            if file_path.is_absolute():
                # Try to make it relative to current directory
                try:
                    rel_path = file_path.relative_to(Path.cwd())
                except ValueError:
                    # If not relative to cwd, use the path as-is
                    rel_path = file_path
            else:
                rel_path = file_path
            
            module = str(rel_path).replace("/", ".").replace("\\", ".").replace(".py", "")
            # Remove 'src.' prefix if present
            if module.startswith("src."):
                module = module[4:]
        except Exception:
            module = str(file_path.name).replace(".py", "")
        
        # Get docstring
        docstring = ast.get_docstring(node) or ""
        
        # Get base class
        base_class = "BaseSettings"
        if node.bases:
            base = node.bases[0]
            if isinstance(base, ast.Name):
                base_class = base.id
            elif isinstance(base, ast.Attribute):
                base_class = base.attr
        
        # Extract fields
        fields = []
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                
                # Get type annotation
                field_type = _get_type_string(item.annotation)
                
                # Check if it has a default value or Field()
                default = None
                description = ""
                required = True
                
                if item.value:
                    if isinstance(item.value, ast.Call):
                        # Check if it's Field()
                        if isinstance(item.value.func, ast.Name) and item.value.func.id == "Field":
                            # Extract default and description from Field()
                            if item.value.args:
                                default = _get_value_repr(item.value.args[0])
                                if default != "...":
                                    required = False
                            
                            for keyword in item.value.keywords:
                                if keyword.arg == "default":
                                    default = _get_value_repr(keyword.value)
                                    required = False
                                elif keyword.arg == "description":
                                    description = _get_value_repr(keyword.value)
                        else:
                            default = _get_value_repr(item.value)
                            required = False
                    else:
                        default = _get_value_repr(item.value)
                        required = False
                
                fields.append(FieldInfo(
                    name=field_name,
                    type=field_type,
                    default=default,
                    description=description,
                    required=required
                ))
        
        return SettingsClassInfo(
            module=module,
            class_name=node.name,
            base_class=base_class,
            fields=fields,
            docstring=docstring
        )
    
    except Exception:
        return None


def _get_type_string(annotation: ast.expr) -> str:
    """Convert AST type annotation to string."""
    if isinstance(annotation, ast.Name):
        return annotation.id
    elif isinstance(annotation, ast.Subscript):
        base = _get_type_string(annotation.value)
        if isinstance(annotation.slice, ast.Name):
            return f"{base}[{annotation.slice.id}]"
        elif isinstance(annotation.slice, ast.Tuple):
            items = [_get_type_string(e) for e in annotation.slice.elts]
            return f"{base}[{', '.join(items)}]"
        else:
            return base
    elif isinstance(annotation, ast.Attribute):
        return annotation.attr
    elif isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        # Handle Union types (A | B)
        left = _get_type_string(annotation.left)
        right = _get_type_string(annotation.right)
        return f"{left} | {right}"
    else:
        return "Any"


def _get_value_repr(value: ast.expr) -> Any:
    """Get a representation of a value from AST."""
    if isinstance(value, ast.Constant):
        # Handle Ellipsis (...) specially
        if value.value is ...:
            return "..."  # Return string representation
        return value.value
    elif isinstance(value, ast.Name):
        if value.id == "True":
            return True
        elif value.id == "False":
            return False
        elif value.id == "None":
            return None
        elif value.id == "Ellipsis":
            return "..."  # Return string representation
        else:
            return value.id
    elif isinstance(value, ast.List):
        return [_get_value_repr(e) for e in value.elts]
    elif isinstance(value, ast.Dict):
        return {_get_value_repr(k): _get_value_repr(v) for k, v in zip(value.keys, value.values)}
    elif isinstance(value, ast.Str):
        return value.s
    elif isinstance(value, ast.Num):
        return value.n
    elif isinstance(value, ast.Ellipsis):
        return "..."  # Return string representation
    else:
        return "..."


def generate_settings_yaml(
    settings_classes: list[SettingsClassInfo],
    strategy: Literal["single", "per-module", "file-per-module"],
    settings_context: str,
    output_dir: Path
) -> list[Path]:
    """Generate settings YAML files based on discovered classes.
    
    Args:
        settings_classes: List of discovered settings classes
        strategy: Generation strategy:
            - "single": Generate one settings.yaml with all settings
            - "per-module": Generate one file per Python module
            - "file-per-module": Generate one file per settings class
        settings_context: Base path in the settings tree (e.g., "sync", "cli")
        output_dir: Directory to write generated files
        
    Returns:
        List of generated file paths
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    generated_files = []
    
    if strategy == "single":
        # Generate single settings.yaml with all classes
        settings_dict = {}
        
        for class_info in settings_classes:
            # Create nested structure based on settings_context
            context_parts = settings_context.split(".") if settings_context else []
            current = settings_dict
            
            for part in context_parts:
                if part not in current:
                    current[part] = {}
                current = current[part]
            
            # Add class settings
            class_key = _to_snake_case(class_info.class_name.replace("Settings", ""))
            current[class_key] = _generate_field_dict(class_info.fields)
            
            # Add comment with docstring
            if class_info.docstring:
                current[f"_{class_key}_comment"] = class_info.docstring
        
        # Write to file
        output_file = output_dir / "settings.yaml"
        with output_file.open("w") as f:
            f.write(f"# Generated settings from code inspection\n")
            f.write(f"# Context: {settings_context or 'root'}\n\n")
            yaml.dump(settings_dict, f, default_flow_style=False, sort_keys=False)
        
        generated_files.append(output_file)
    
    elif strategy == "per-module":
        # Group by module and generate one file per module
        by_module: dict[str, list[SettingsClassInfo]] = {}
        for class_info in settings_classes:
            module = class_info.module
            if module not in by_module:
                by_module[module] = []
            by_module[module].append(class_info)
        
        for module, classes in by_module.items():
            settings_dict = {}
            
            for class_info in classes:
                class_key = _to_snake_case(class_info.class_name.replace("Settings", ""))
                settings_dict[class_key] = _generate_field_dict(class_info.fields)
            
            # Write to file
            module_name = module.split(".")[-1]
            output_file = output_dir / f"{module_name}.settings.yaml"
            
            with output_file.open("w") as f:
                f.write(f"# Generated from module: {module}\n\n")
                yaml.dump(settings_dict, f, default_flow_style=False, sort_keys=False)
            
            generated_files.append(output_file)
    
    elif strategy == "file-per-module":
        # Generate one file per settings class
        for class_info in settings_classes:
            settings_dict = _generate_field_dict(class_info.fields)
            
            # Write to file
            class_key = _to_snake_case(class_info.class_name.replace("Settings", ""))
            output_file = output_dir / f"{class_key}.settings.yaml"
            
            with output_file.open("w") as f:
                f.write(f"# Generated from: {class_info.module}.{class_info.class_name}\n")
                if class_info.docstring:
                    f.write(f"# {class_info.docstring}\n")
                f.write("\n")
                yaml.dump(settings_dict, f, default_flow_style=False, sort_keys=False)
            
            generated_files.append(output_file)
    
    return generated_files


def _generate_field_dict(fields: list[FieldInfo]) -> dict[str, Any]:
    """Generate a dictionary of field values for YAML output."""
    result = {}
    
    for field in fields:
        # Use default value or a placeholder
        if field.default is not None and field.default != "...":
            # Handle special types
            if isinstance(field.default, str):
                value = field.default
            else:
                value = field.default
        elif "SecretStr" in field.type:
            value = ""  # Secret fields as empty strings
        elif field.type == "str":
            value = ""
        elif field.type == "int":
            value = 0
        elif field.type == "float":
            value = 0.0
        elif field.type == "bool":
            value = False
        elif field.type.startswith("list") or field.type.startswith("List"):
            value = []
        elif field.type.startswith("dict") or field.type.startswith("Dict"):
            value = {}
        elif " | None" in field.type or "| None" in field.type:
            value = None
        else:
            value = None
        
        result[field.name] = value
    
    return result


def _to_snake_case(name: str) -> str:
    """Convert CamelCase to snake_case."""
    import re
    name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', name).lower()
