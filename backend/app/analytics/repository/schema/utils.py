"""
Utility functions for schema operations.
"""
from typing import Dict, Any, Optional, List

def singular_form(name):
    """Convert a plural table name to its singular form"""
    if name.endswith('ies'):
        return name[:-3] + 'y'
    elif name.endswith('s') and not name.endswith('ss'):
        return name[:-1]
    return name
    
def plural_form(name):
    """Convert a singular table name to its plural form"""
    if name.endswith('y') and not name.endswith('ay') and not name.endswith('ey') and not name.endswith('oy') and not name.endswith('uy'):
        return name[:-1] + 'ies'
    elif not name.endswith('s'):
        return name + 's'
    return name
