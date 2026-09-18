#!/usr/bin/env python3
"""Do not overwrite QA Status with PASS when Shopify product is created."""
import json
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parent.parent / "ShopifyProductAdd.V2.json"


def main():
    data = json.loads(WORKFLOW.read_text())
    for node in data["nodes"]:
        if node.get("name") == "Update sheet Shopify URLs":
            cols = node["parameters"]["columns"]["value"]
            cols.pop("QA Status", None)
    WORKFLOW.write_text(json.dumps(data, indent=2) + "\n")
    print("Removed QA Status overwrite from Update sheet Shopify URLs")


if __name__ == "__main__":
    main()
