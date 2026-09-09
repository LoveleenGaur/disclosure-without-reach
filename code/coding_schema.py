"""Coding schema v2: context-aware.

Hand validation of the v1 keyword coder found three systematic false positive
classes, all of which inflate the apparent disclosure rate:

  1. "watermark" appearing inside negative prompts, where it names an artifact
     the user wants the model to avoid drawing. This is the opposite of output
     watermarking.
  2. "provenance" referring to training-corpus provenance tracking rather than
     provenance attached to generated outputs.
  3. Synthetic-content language describing synthetic *training data*, or
     describing the "AI-generated look" as a quality defect the model reduces.

v2 keeps the v1 patterns as candidate generators, then applies an exclusion
filter over a context window around each match. Every trial records both the
raw v1 flag and the refined v2 flag, so the paper can report the gap. That gap
is itself a result: it quantifies how badly naive keyword auditing overstates
disclosure.
"""

from __future__ import annotations

import re

WINDOW = 150

CANDIDATES = {
    "watermark": [
        r"\bwatermark(?:s|ed|ing)?\b",
        r"\bsynthid\b",
        r"\bstegastamp\b",
        r"invisible[- ]watermark",
        r"\bimwatermark\b",
    ],
    "provenance": [
        r"\bc2pa\b",
        r"content\s+credential",
        r"\bprovenance\b",
        r"content\s+authenticity",
    ],
    "synthetic_disclosure": [
        r"ai[- ]generated",
        r"machine[- ]generated",
        r"synthetic\s+(?:content|media|image)",
        r"\bdisclos\w*",
        r"label(?:l)?(?:ed|ing)?\s+as\s+(?:ai|synthetic)",
    ],
    "prohibited_uses": [
        r"\bdeepfake",
        r"\bimpersonat",
        r"non[- ]consensual",
        r"\b(?:dis|mis)information\b",
        r"prohibited\s+use",
        r"out[- ]of[- ]scope\s+use",
        r"\bmisuse\b",
    ],
    "downstream_obligation": [
        r"downstream\s+(?:user|developer|deployer|application)",
        r"(?:users?|deployers?|developers?)\s+(?:must|should|are\s+(?:required|expected))",
        r"you\s+(?:must|are\s+responsible)",
    ],
    "regulatory_reference": [
        r"\bai\s+act\b",
        r"\bgdpr\b",
        r"\bdsa\b",
        r"\blegal\s+(?:obligation|requirement)",
        r"\bregulatory\s+(?:requirement|obligation|compliance)",
    ],
}

# Context cues that disqualify a candidate match.
EXCLUSIONS = {
    "watermark": [
        r"negative[_ ]prompt",
        r"watermark\s+probability",          # LAION training-data filtering
        r"estimated\s+watermark",
        r"filtered\s+to\s+images",
        r"pip\s+install[^\n]{0,80}watermark",  # dependency line, not a claim
        r"```[^`]{0,60}watermark[^`]{0,60}```",
        r"low\s*res|lowres|worst\s+quality|low\s+quality|jpeg\s+artifacts",
        r"\bsignature\b.{0,40}\busername\b|\busername\b.{0,40}\bsignature\b",
        r"\bblurry\b|\bdeformed\b|\bmutated\b",
        r"remove\s+watermark|watermark\s+removal",
        r"generat\w+\s+(?:in-image\s+)?text.{0,60}watermark",
        r"logos?,\s*captions?,\s*watermarks?",
    ],
    "provenance": [
        r"(?:data|dataset|corpus|training)\s+provenance",
        r"provenance\s+(?:tracking|filtering)\s+(?:are|is)\s+applied\s+across\s+the\s+corpus",
        r"deduplication\s+and\s+provenance",
        r"data\s+sources?\s+are\s+reviewed",
        r"provenance,?\s+and\s+alignment\s+with",
        r"licensing\s+compatibility",
        r"admission\s+into\s+training\s+corpora",
    ],
    "synthetic_disclosure": [
        r"synthetic\s+(?:images?|data|samples?)\s+(?:generated\s+)?(?:using|from|with|by)",
        r"ai[- ]generated\s+look",
        r"reduces?\s+the\s+.{0,20}ai[- ]generated",
        r"\|\s*\d+[MK]?\s*\|",          # training-data size tables
        r"training\s+(?:data|set|corpus)",
    ],
    # Red-teaming and evaluation descriptions name harm categories without
    # stating a prohibition. Validation found three such false positives.
    "prohibited_uses": [
        r"testing\s+covered",
        r"red[- ]team",
        r"resilience\s+to\s+attempts",
        r"based\s+on\s+these\s+evaluations",
        r"testing\s+was\s+conducted",
        # Training-data screening pipelines enumerate harm categories without
        # stating a prohibition on use. Found in second-coder validation.
        r"training\s+datasets?\s+passed\s+through",
        r"(?:automated|manual)\s+safeguards",
        r"reduce\s+the\s+presence\s+of",
        r"violating\s+content\s+across\s+categories",
        r"categories\s+including\s+weapons",
        r"layers\s+of\s+automated",
    ],
    # Gate and authentication instructions are access mechanics, not
    # obligations on downstream conduct. Validation found two.
    "downstream_obligation": [
        r"accept\s+the\s+gate",
        r"huggingface[- ]cli\s+login",
        r"HF_TOKEN",
        r"authenticate\s+before",
        r"gated\s+(?:model|repo)",
        # Awareness statements are not obligations. Found in second-coder
        # validation: "Users should be aware of the following limitations".
        r"should\s+be\s+aware",
        r"be\s+aware\s+of\s+the\s+following",
    ],
    "regulatory_reference": [],
}

# Context cues that confirm a candidate, overriding an exclusion.
CONFIRMATIONS = {
    "watermark": [
        r"implements?\s+[^.]{0,40}watermark",
        r"pixel[- ]layer\s+watermark",
        r"applies?\s+[^.]{0,60}(?:watermark|c2pa)",
        r"output.{0,60}watermark",
        r"watermark.{0,60}output",
        r"\bsynthid\b",
        r"invisible\s+watermark.{0,80}(?:embed|appl|add|attach)",
        r"(?:embed|appl|add|attach)\w*.{0,60}invisible\s+watermark",
        r"watermark\w*\s+(?:is|are)\s+(?:embedded|applied|added)",
        r"all\s+(?:images?|outputs?).{0,40}watermark",
    ],
    "provenance": [r"\bc2pa\b", r"content\s+credential", r"content\s+authenticity"],
    "synthetic_disclosure": [
        r"(?:identify|label|interpret|detect)[^.]{0,60}ai[- ]generated",
        r"indicate[^.]{0,60}(?:ai|synthetic|generated)",
        r"disclos\w+.{0,80}(?:ai|synthetic|generated)",
        r"(?:ai|synthetic|generated).{0,80}disclos\w+",
        r"label(?:l)?(?:ed|ing)?\s+as\s+(?:ai|synthetic)",
        r"must\s+(?:be\s+)?(?:marked|labelled|labeled|indicated)",
    ],
    "prohibited_uses": [],
    "downstream_obligation": [],
    "regulatory_reference": [],
}

# Categories where a bare keyword match is too ambiguous to count. A candidate
# is accepted only if an output-directed confirmation cue appears in context.
REQUIRE_CONFIRMATION = {"watermark", "provenance", "synthetic_disclosure"}

C_CAND = {k: [re.compile(p, re.I) for p in v] for k, v in CANDIDATES.items()}
C_EXCL = {k: [re.compile(p, re.I) for p in v] for k, v in EXCLUSIONS.items()}
C_CONF = {k: [re.compile(p, re.I) for p in v] for k, v in CONFIRMATIONS.items()}


def _classify(body: str, cat: str) -> tuple[bool, bool, str | None]:
    """Returns (raw_hit, refined_hit, evidence span)."""
    raw_hit = False
    evidence = None
    for pat in C_CAND[cat]:
        for m in pat.finditer(body):
            lo = max(0, m.start() - WINDOW)
            hi = min(len(body), m.end() + WINDOW)
            ctx = body[lo:hi]
            if not raw_hit:
                raw_hit = True
                evidence = ctx.replace("\n", " ").strip()
            confirmed = any(c.search(ctx) for c in C_CONF[cat])
            if confirmed:
                return True, True, ctx.replace("\n", " ").strip()
            if cat in REQUIRE_CONFIRMATION:
                continue
            if any(e.search(ctx) for e in C_EXCL[cat]):
                continue
            return True, True, ctx.replace("\n", " ").strip()
    return raw_hit, False, evidence


CATEGORIES = list(CANDIDATES)


def code_card_v2(text) -> dict:
    body = text if isinstance(text, str) else ""
    out: dict = {"card_chars": len(body), "has_card": len(body.strip()) > 200}
    for cat in CATEGORIES:
        raw, refined, ev = _classify(body, cat)
        out[f"{cat}_raw"] = raw
        out[cat] = refined
        out[f"{cat}_evidence"] = ev
    # Dependency-only: the card names a watermarking package in an install or
    # code block but makes no claim about marking outputs. Counted separately,
    # because an install line is not a disclosure to downstream developers.
    import re as _re
    out["watermark_dependency_only"] = bool(
        (not out["watermark"]) and out["watermark_raw"] and
        _re.search(r"(?:pip\s+install|import)[^\n]{0,80}watermark", body, _re.I))
    out["any_provenance_signal"] = bool(
        out["watermark"] or out["provenance"] or out["synthetic_disclosure"])
    out["any_provenance_signal_raw"] = bool(
        out["watermark_raw"] or out["provenance_raw"] or out["synthetic_disclosure_raw"])
    return out
