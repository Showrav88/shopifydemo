#!/usr/bin/env python3
"""Move Analyze image before Photoroom — URL mode with detail:low (avoids 413 on large base64)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
path = ROOT / "ShopifyProductAdd.V2.json"
data = json.loads(path.read_text())

for node in data["nodes"]:
    if node.get("name") == "Analyze image":
        params = node["parameters"]
        params["inputType"] = "url"
        params["imageUrls"] = (
            "={{ $('Active product row').first().json['Product image URL'] "
            "|| $('Active product row').first().json.validated_image_url }}"
        )
        params.pop("binaryPropertyName", None)
        opts = params.get("options") or {}
        opts["simplify"] = True
        opts["detail"] = "low"
        params["options"] = opts
        print("Patched Analyze image → URL mode, detail: low")

# Reconnect: Active product row → Analyze image → Photoroom → Restore → ImgBB
conns = data["connections"]
conns["Active product row"] = {
    "main": [[{"node": "Analyze image", "type": "main", "index": 0}]]
}
conns["Analyze image"] = {
    "main": [[{"node": "Remove background Photoroom", "type": "main", "index": 0}]]
}
conns["Remove background Photoroom"] = {
    "main": [[{"node": "Restore image binary", "type": "main", "index": 0}]]
}
print("Reordered: Active product row → Analyze image → Photoroom → Restore → ImgBB")

path.write_text(json.dumps(data, indent=2) + "\n")
print("Done:", path)
