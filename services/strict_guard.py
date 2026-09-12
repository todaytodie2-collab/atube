# -*- coding: utf-8 -*-
"""
A TuBe Strict Taxonomic Guard & Dual-Signal Classifier
Pre-ingestion filter that prevents misclassification using taxonomy_rules.json
and dual-signal NLP text checks.
"""

import json
import os
import re

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RULES_FILE = os.path.join(PROJECT_ROOT, "config", "taxonomy_rules.json")

class StrictTaxonomicGuard:
    _rules = None

    @classmethod
    def load_rules(cls):
        if cls._rules is None:
            if os.path.exists(RULES_FILE):
                try:
                    with open(RULES_FILE, 'r', encoding='utf-8') as f:
                        cls._rules = json.load(f)
                except Exception:
                    cls._rules = {}
            else:
                cls._rules = {}
        return cls._rules

    @classmethod
    def guard_and_classify(cls, item: dict) -> dict:
        rules = cls.load_rules()
        title = (item.get("title") or "").lower()
        arabic_title = (item.get("arabic_title") or "").lower()
        combined = f"{title} {arabic_title}"
        current_cat = item.get("category", "foreign")
        c_type = item.get("content_type", "movie")

        blacklists = rules.get("strict_blacklists", {})
        overrides = rules.get("category_overrides", {})

        # 1. Check strict blacklists (e.g., Foreign series in Arabic categories)
        for cat, forbidden_terms in blacklists.items():
            if current_cat == cat:
                for term in forbidden_terms:
                    if term in combined:
                        # Reassign to proper foreign/international category
                        if c_type == "series":
                            item["category"] = "foreign"
                        else:
                            item["category"] = "foreign"
                        print(f"[StrictGuard] Blocked misclassification of '{item.get('title')}' from {cat} -> foreign")
                        break

        # 2. Dual-Signal Classification via overrides
        for cat, keywords in overrides.items():
            for kw in keywords:
                if kw in combined:
                    item["category"] = cat
                    # Set proper content type based on category
                    if cat in ["turkish", "indian", "asian", "documentary"] and ("مسلسل" in combined or "season" in combined or "حلقة" in combined or item.get("total_seasons", 0) > 0):
                        item["content_type"] = "series"
                    elif cat in ["plays", "wrestling"]:
                        item["content_type"] = "movie"
                    break

        return item
