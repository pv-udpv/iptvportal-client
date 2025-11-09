"""SQL to JSONSQL transpiler module (backward compatibility)."""

# Backward compatibility - re-export from jsonsql
from iptvportal.jsonsql.exceptions import TranspilerError, UnsupportedFeatureError
from iptvportal.jsonsql.transpiler import SQLTranspiler

__all__ = ["SQLTranspiler", "TranspilerError", "UnsupportedFeatureError"]
