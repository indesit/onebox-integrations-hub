"""Product Catalog Parser Logic (HUB-013)."""

import re
from typing import Dict, Optional

class ProductCatalogParser:
    @staticmethod
    def parse_characteristic(name: str) -> Dict[str, Optional[str]]:
        """
        Parses characteristic name into structured attributes.
        Example inputs:
        - "бордовий, XS" -> {"color": "бордовий", "size": "XS"}
        - "В полоску, L" -> {"color": "В полоску", "size": "L"}
        - "рожевий, 32, B" -> {"color": "рожевий", "size": "32", "cup": "B"}
        - "чорний" -> {"color": "чорний"}
        """
        if not name:
            return {}

        parts = [p.strip() for r in name.split(',') for p in [r]]
        attrs = {}

        # Size candidates (usually uppercase or digits)
        size_patterns = [
            r'^(XS|S|M|L|XL|XXL)$',
            r'^\d{2}$', # e.g. 32, 34, 36
        ]
        
        # Cup candidates (single uppercase letter)
        cup_pattern = r'^[A-G]$'

        for part in parts:
            # Check for Cup
            if re.match(cup_pattern, part):
                attrs['cup'] = part
                continue
            
            # Check for Size
            is_size = False
            for pattern in size_patterns:
                if re.match(pattern, part):
                    attrs['size'] = part
                    is_size = True
                    break
            if is_size:
                continue
            
            # If not size or cup, assume color or print
            if 'color' not in attrs:
                attrs['color'] = part
            else:
                # Append if multiple non-size parts found
                attrs['color'] += f", {part}"

        return attrs

if __name__ == "__main__":
    # Test cases
    test_data = [
        "бордовий, XS",
        "В полоску, L",
        "рожевий, 32, B",
        "чорний, M",
        "леопардовий принт, S"
    ]
    for text in test_data:
        print(f"'{text}' -> {ProductCatalogParser.parse_characteristic(text)}")
