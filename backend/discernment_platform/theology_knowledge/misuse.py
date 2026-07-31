from __future__ import annotations

import re


RULES = {
    "proof_texting": re.compile(r"(这节经文单独证明|只看这一节就知道)"),
    "word_study_fallacy": re.compile(r"(Strong编号.*所以|词根.*必然表示|这个词包含所有意思)"),
    "prosperity_gospel_use": re.compile(r"(奉献就一定发财|信主就不会生病|保证事业成功)"),
    "political_nationalization": re.compile(r"(现代.*国家就是圣约以色列|这个民族就是神唯一选民)"),
    "abusive_authority_use": re.compile(r"(顺服牧者所以不能质疑|不可碰神的受膏者所以不能调查)"),
    "victim_blame_use": re.compile(r"(受害者必须马上饶恕并恢复接触|被虐待是因为不够顺服)"),
    "anti_medical_or_anti_professional_use": re.compile(r"(不要看医生只祷告|心理咨询是不信神)"),
    "eschatological_date_setting": re.compile(r"(耶稣一定在\d{4}年再来|世界末日在\d{4}年)"),
}


def detect_misuse(text: str) -> dict:
    risks = [name for name, pattern in RULES.items() if pattern.search(text)]
    severity = "none"
    if risks:
        severity = "medium"
    if any(r in risks for r in {
        "abusive_authority_use",
        "victim_blame_use",
        "anti_medical_or_anti_professional_use",
    }):
        severity = "high"

    return {
        "risk_types": risks,
        "severity": severity,
        "human_review_required": severity in {"high", "critical"},
        "recommended_correction": (
            "Return to paragraph, book, genre, audience, canonical context and qualified pastoral application."
            if risks else ""
        ),
    }
