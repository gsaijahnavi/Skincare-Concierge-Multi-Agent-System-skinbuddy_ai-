# tools/product_lookup_tool.py

import os
from typing import Dict, Any, List

import pandas as pd

PRODUCTS_PATH = os.path.join(
    os.path.dirname(__file__),
    "../data/product_catalog.xlsx"
)


class ProductLookupTool:
    """
    Thin wrapper over the product catalog Excel.

    Expects columns:
        product_name
        product_url
        product_type
        ingredients
        price
    """

    def __init__(self, products_path: str = PRODUCTS_PATH):
        self.products_path = products_path
        self.products, self.columns = self._load_products_and_columns()

    def _load_products_and_columns(self):
        df = pd.read_excel(self.products_path)

        # Normalize column names just in case (but we keep originals)
        df.columns = [c.strip() for c in df.columns]

        columns = list(df.columns)
        products = df.to_dict(orient="records")
        return products, columns

    def search_products(
        self,
        columns_to_search: List[str],
        patterns: Dict[str, List[str]],
    ) -> List[Dict[str, Any]]:
        """
        Search products using:
          - columns_to_search: list of column names to consider
          - patterns: {column_name: [patterns]}

        Matching logic:
        - If 'product_type' is included AND has patterns, a product MUST match
          at least one of those product_type patterns to be eligible.
        - For other columns, matching is OR across (column, pattern).
        - Returns de-duplicated list of product dicts (by product_name).
        """
        # Normalize inputs
        columns_to_search = [c for c in columns_to_search if c in self.columns]
        patterns = patterns or {}

        # Determine if product_type is required
        require_product_type = (
            "product_type" in columns_to_search
            and isinstance(patterns.get("product_type"), list)
            and len(patterns["product_type"]) > 0
        )

        results: List[Dict[str, Any]] = []

        for product in self.products:
            # 1) Enforce product_type match if required
            if require_product_type:
                pt_value = str(product.get("product_type", "")).lower()
                pt_patterns = [p.lower() for p in patterns.get("product_type", [])]

                if not any(p in pt_value for p in pt_patterns):
                    continue  # skip products not in right category

            # 2) For other columns, match if ANY pattern appears
            matched_any = False
            for col in columns_to_search:
                value = str(product.get(col, "")).lower()

                col_patterns = patterns.get(col, [])
                if not isinstance(col_patterns, list):
                    continue

                for pattern in col_patterns:
                    p = str(pattern).lower()
                    if p and p in value:
                        matched_any = True
                        break

                if matched_any:
                    break

            # If product_type is required but we didn't match any other column,
            # we still allow the product (since category is already right).
            if require_product_type and not matched_any:
                matched_any = True

            if matched_any:
                results.append(product)

        # De-duplicate by product_name
        seen = set()
        unique_results: List[Dict[str, Any]] = []
        for prod in results:
            name = prod.get("product_name")
            if name and name not in seen:
                unique_results.append(prod)
                seen.add(name)

        return unique_results
