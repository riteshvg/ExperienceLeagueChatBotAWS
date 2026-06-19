"""Domain-weighted question selector for Educator Mode."""

from __future__ import annotations

from config.exams import Exam, ExamDomain


def select_next_domain(
    exam: Exam,
    domain_scores: dict[str, dict[str, int]],
) -> ExamDomain:
    """Pick the domain with the largest deficit vs target weight."""
    total_asked = sum(d.get("total", 0) for d in domain_scores.values())

    max_deficit = float("-inf")
    selected = exam.domains[0]

    for domain in exam.domains:
        target_count = (domain.weight_pct / 100) * (total_asked + 1)
        actual_count = domain_scores.get(domain.id, {}).get("total", 0)
        deficit = target_count - actual_count
        if deficit > max_deficit:
            max_deficit = deficit
            selected = domain

    return selected
