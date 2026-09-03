#!/usr/bin/env python3
"""Collect Product VOC and run the existing market improvement capabilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from amz import registry


def invoke(capability_id: str, params: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    result = registry.invoke(capability_id, params)
    if result.code.value != "OK":
        return None, {
            "capability": capability_id,
            "code": result.code.value,
            "message": result.message,
            "meta": result.meta.model_dump(mode="json"),
        }
    data = result.data
    return data if isinstance(data, dict) else {"value": data}, None


def run(asins: list[str]) -> dict[str, Any]:
    products: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for asin in asins:
        voc, failure = invoke("entity.product.voc", {"asin": asin})
        if failure:
            failures.append({"asin": asin, **failure})
            continue
        products.append({"asin": asin, **(voc or {})})

    output: dict[str, Any] = {
        "status": "PARTIAL" if failures else "OK",
        "requested_asins": asins,
        "successful_asins": [item["asin"] for item in products],
        "products": products,
        "failures": failures,
        "success_factors": None,
        "market_gap": None,
        "proposals": None,
    }
    if len(products) < 3:
        output["status"] = "INSUFFICIENT_FOR_MARKET_AGGREGATION"
        output["message"] = "至少需要 3 个成功的 Product VOC 才输出市场级结论"
        return output

    leaders = [{"asin": item["asin"], "strengths": item["strengths"]} for item in products]
    weaknesses = [{"asin": item["asin"], "weaknesses": item["weaknesses"]} for item in products]
    use_insights = [{"asin": item["asin"], "use_insights": item["use_insights"]} for item in products]

    success_factors, failure = invoke("analysis.market.success-factors", {"leaders": leaders})
    if failure:
        failures.append(failure)
        output["status"] = "PARTIAL"
        return output
    output["success_factors"] = success_factors

    market_gap, failure = invoke(
        "analysis.market.gap-analysis",
        {"weaknesses": weaknesses, "use_insights": use_insights},
    )
    if failure:
        failures.append(failure)
        output["status"] = "PARTIAL"
        return output
    output["market_gap"] = market_gap

    proposals, failure = invoke(
        "analysis.market.renovation-proposal",
        {
            "success_factors": success_factors.get("market_leaders_success_factors", []),
            "problem_points": market_gap.get("problem_points", []),
            "opportunity_points": market_gap.get("opportunity_points", []),
            "use_insights": market_gap.get("market_use_insights", {}),
        },
    )
    if failure:
        failures.append(failure)
        output["status"] = "PARTIAL"
        return output
    output["proposals"] = proposals
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("asins", nargs="+", help="Three or more Amazon ASINs")
    parser.add_argument("--out", type=Path, help="Write JSON to this file")
    args = parser.parse_args()

    report = run(list(dict.fromkeys(args.asins)))
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        args.out.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if report["status"] == "OK" else 2


if __name__ == "__main__":
    raise SystemExit(main())
