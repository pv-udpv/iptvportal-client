"""CLI interface for SQL to JSONSQL transpiler (backward compatibility)."""

# Backward compatibility - forward to jsonsql module
from iptvportal.jsonsql.__main__ import main

if __name__ == "__main__":
    main()
