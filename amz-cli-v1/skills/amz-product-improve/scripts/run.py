#!/usr/bin/env python3
"""Run the Market business method for an explicit Product sample."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from amz import Code, registry
from amz.schemas.entity_ref import EntityRef, product_ref


def run(asins: list[str], term: str | None = None, marketplace: str = "US") -> dict[str, Any]:
    refs = list(dict.fromkeys(product_ref(marketplace, asin) for asin in asins))
    if len(refs) < 3:
        return {"status": "INSUFFICIENT_FOR_MARKET_AGGREGATION", "message": "至少需要 3 个不同商品；Entity 还会检查有效评论证据", "failures": []}
    identity = {"term": term, "marketplace": marketplace, "category": ""}
    if not term:
        result = registry.invoke("entity.product.primary_keyword_ref", refs[0].identity)
        if result.code != Code.OK:
            return {"status": "FAILED", "failures": [result.model_dump(mode="json")]}
        identity = EntityRef.model_validate(result.data).identity
    result = registry.invoke("entity.market.proposals", {
        **identity, "sample_refs": [ref.model_dump(mode="json") for ref in refs],
    })
    if result.code != Code.OK:
        return {"status": "INSUFFICIENT_EVIDENCE" if result.code == Code.ERROR_MISSING_FIELDS else "FAILED",
                "requested_asins": [ref.identity["asin"] for ref in refs],
                "failures": [result.model_dump(mode="json")]}
    data = result.data
    failures = [source for source in data["evidence"].get("sources", []) if source.get("state", "ready") != "ready"]
    return {"status": "PARTIAL" if failures else "OK", "requested_asins": [ref.identity["asin"] for ref in refs],
            "success_factors": data["success_factors"], "market_gap": data["market_gap"],
            "proposals": data["micro_renovation_proposals"], "evidence": data["evidence"], "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asins", nargs="+", help="Three or more Amazon ASINs")
    parser.add_argument("--term", help="Explicit market keyword; otherwise use the first Product's primary keyword")
    parser.add_argument("--marketplace", default="US")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    report = run(args.asins, term=args.term, marketplace=args.marketplace)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if report["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
