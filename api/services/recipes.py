"""UGC ad recipes: shot plans that already obey the waste-guard rules.

Structure adapted (our own wording) from OSideMedia/higgsfield-ai-prompt-skill
(MIT, @6a6a5dd, skills/higgsfield-recipes "Product Advertisement" pattern:
texture reveal -> feature -> emotional connection -> end frame) and the idea of
editable recipe starters from ItsSNOWMOBILE/aftertake (MIT, @0dc2f84).
Each shot carries only a Motion Block; the Identity Block comes from the chosen
character/product, so the two never mix. Every shot is <= 15 s.
"""
from __future__ import annotations

from typing import Any

RECIPES: list[dict[str, Any]] = [
    {"id": "ugc-testimonial", "name": "UGC testimonial", "needs": ["character", "product"], "ratio": "9:16",
     "shots": [
         {"seconds": 5, "motion": "Handheld selfie framing. The presenter looks into the lens and holds the product up beside their face."},
         {"seconds": 10, "motion": "Slow push-in. They use the product in one natural motion and react with a small, genuine smile."}]},
    {"id": "unboxing", "name": "Unboxing", "needs": ["character", "product"], "ratio": "9:16",
     "shots": [
         {"seconds": 5, "motion": "Top-down. Hands slide the box onto a table and lift the lid."},
         {"seconds": 10, "motion": "Close-up. The product is lifted out and turned once toward the lens, then set down label forward."}]},
    {"id": "product-hero", "name": "Product hero", "needs": ["product"], "ratio": "9:16",
     "shots": [
         {"seconds": 5, "motion": "Macro dolly across the surface texture, soft light sweeping left to right."},
         {"seconds": 10, "motion": "Slow orbit around the product, ending on a still front view with space above for text."}]},
    {"id": "problem-solution", "name": "Problem, then solution", "needs": ["character", "product"], "ratio": "9:16",
     "shots": [
         {"seconds": 5, "motion": "Static medium shot. The presenter shows the everyday moment the product improves."},
         {"seconds": 10, "motion": "Cut to close-up. They use the product; camera pushes in on the result."}]},
    {"id": "before-after", "name": "Before / after", "needs": ["character", "product"], "ratio": "9:16",
     "shots": [
         {"seconds": 5, "motion": "Locked-off frame of the before state, natural light."},
         {"seconds": 10, "motion": "Same framing, the after state; a slow push-in ends on the product in hand."}]},
    {"id": "try-on", "name": "Try-on", "needs": ["character", "product"], "ratio": "9:16",
     "shots": [
         {"seconds": 5, "motion": "Mirror shot. The presenter holds the item up against themselves."},
         {"seconds": 10, "motion": "Full-body turn, slow and steady, ending facing the lens."}]},
]


def list_recipes() -> dict[str, Any]:
    return {"ok": True, "recipes": RECIPES}


def get_recipe(recipe_id: str) -> dict[str, Any]:
    for r in RECIPES:
        if r["id"] == recipe_id:
            return {"ok": True, "recipe": r}
    return {"ok": False, "error": "recipe_not_found"}
