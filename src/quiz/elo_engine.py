from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import math

from src.graph.engine import RealTimeGraphEngine
from src.models.schemas import CrossNicheEdge


@dataclass
class QuizOption:
    option_id: str
    entity_uid: str
    text: str
    is_correct: bool
    trap_explanation: str


@dataclass
class QuizQuestion:
    question_id: str
    tier: int  # 1 = Direct Impact, 2 = 2-Hop Cross-Niche, 3 = Counter-Intuitive Trap
    difficulty_elo: float
    niche_ids: List[str]
    prompt: str
    source_attribution: str
    options: List[QuizOption]
    talking_point_one_liner: str
    mechanism_explanation: str
    time_limit_seconds: int = 20


@dataclass
class UserNicheProfile:
    user_id: str
    niche_ratings: Dict[str, float] = field(default_factory=dict)
    niche_attempts: Dict[str, int] = field(default_factory=dict)
    streak: int = 0
    history: List[Dict[str, object]] = field(default_factory=list)

    def get_rating(self, niche_id: str) -> float:
        return self.niche_ratings.get(niche_id, 1200.0)

    def get_attempts(self, niche_id: str) -> int:
        return self.niche_attempts.get(niche_id, 0)


class AdaptiveEloQuizEngine:
    '''
    Multivariate Elo Rating & Question Selection Engine with 4-Option Guessing Correction.
    Grounded in arXiv:2403.07908v1:
      P(correct | lambda_u, mu_i) = c + (1 - c) / (1 + 10^((mu_i - lambda_u) / 400))
    where c = 1 / n_opt = 0.25 for 4-option multiple choice drills.
    Targets a 70-75% expected success rate (Flow State Zone).
    '''

    TARGET_WIN_PROB = 0.72
    GUESSING_FACTOR = 0.25  # 4 options

    def __init__(self, a_k: float = 48.0, b_decay: float = 0.12, k_min: float = 12.0):
        self.a_k = a_k
        self.b_decay = b_decay
        self.k_min = k_min

    def dynamic_uncertainty_k(self, prior_attempts: int) -> float:
        '''U(n) = max(k_min, a / (1 + b * n))'''
        return max(self.k_min, self.a_k / (1.0 + self.b_decay * prior_attempts))

    def predict_win_probability(
        self,
        user: UserNicheProfile,
        niche_ids: List[str],
        question_difficulty: float,
    ) -> float:
        '''
        Computes mean user skill lambda_ui across all tagged niches and returns
        the guessing-corrected probability of a correct response.
        '''
        if not niche_ids:
            mean_skill = 1200.0
        else:
            mean_skill = sum(user.get_rating(nid) for nid in niche_ids) / len(niche_ids)

        logistic_core = 1.0 / (1.0 + math.pow(10.0, (question_difficulty - mean_skill) / 400.0))
        return self.GUESSING_FACTOR + (1.0 - self.GUESSING_FACTOR) * logistic_core

    def ideal_question_difficulty(
        self, user: UserNicheProfile, niche_ids: List[str], target_p: float = TARGET_WIN_PROB
    ) -> float:
        '''
        Inverts the guessing-corrected logistic formula to find the exact question
        difficulty mu_i that yields target_p (default 0.72).
        '''
        mean_skill = (
            sum(user.get_rating(nid) for nid in niche_ids) / len(niche_ids)
            if niche_ids
            else 1200.0
        )
        # Solve: target_p = c + (1 - c) / (1 + 10^((mu - lambda)/400))
        normalized_p = (target_p - self.GUESSING_FACTOR) / (1.0 - self.GUESSING_FACTOR)
        normalized_p = max(0.05, min(0.95, normalized_p))
        offset = 400.0 * math.log10((1.0 / normalized_p) - 1.0)
        return round(mean_skill + offset, 1)

    def update_ratings(
        self,
        user: UserNicheProfile,
        question: QuizQuestion,
        is_correct: bool,
    ) -> Dict[str, float]:
        actual = 1.0 if is_correct else 0.0
        updated: Dict[str, float] = {}

        for nid in question.niche_ids:
            old_r = user.get_rating(nid)
            attempts = user.get_attempts(nid)
            k_val = self.dynamic_uncertainty_k(attempts)
            p_niche = self.predict_win_probability(user, [nid], question.difficulty_elo)
            new_r = round(old_r + k_val * (actual - p_niche), 2)
            user.niche_ratings[nid] = new_r
            user.niche_attempts[nid] = attempts + 1
            updated[nid] = new_r

        user.streak = (user.streak + 1) if is_correct else 0
        user.history.append(
            {
                "question_id": question.question_id,
                "is_correct": is_correct,
                "difficulty_elo": question.difficulty_elo,
                "updated_ratings": dict(updated),
            }
        )
        return updated

    def generate_question_from_edge(
        self,
        edge: CrossNicheEdge,
        graph: RealTimeGraphEngine,
        user: UserNicheProfile,
    ) -> QuizQuestion:
        niche_ids = [edge.source_niche_id, edge.target_niche_id]
        ideal_diff = self.ideal_question_difficulty(user, niche_ids)

        if ideal_diff < 1050:
            tier = 1
        elif ideal_diff < 1250:
            tier = 2
        else:
            tier = 3

        src_ent = graph.entities[edge.source_entity_uid]
        dst_ent = graph.entities[edge.target_entity_uid]
        distractor_ents = graph.get_distractor_entities(
            target_niche_id=edge.target_niche_id,
            exclude_uids=[src_ent.uid, dst_ent.uid],
            count=3,
        )

        options: List[QuizOption] = [
            QuizOption(
                option_id="opt_correct",
                entity_uid=dst_ent.uid,
                text=f"{dst_ent.canonical_name} ({edge.relation_type.value.replace('_', ' ').title()} link)",
                is_correct=True,
                trap_explanation=f"Correct! {edge.mechanism_rationale}",
            )
        ]

        for idx, d_ent in enumerate(distractor_ents, start=1):
            options.append(
                QuizOption(
                    option_id=f"opt_distractor_{idx}",
                    entity_uid=d_ent.uid,
                    text=f"{d_ent.canonical_name} (Active in {d_ent.niche_id}, but no direct causal path)",
                    is_correct=False,
                    trap_explanation=(
                        f"Plausible trap: {d_ent.canonical_name} was in today's headlines, "
                        f"but lacks the {edge.relation_type.value.lower()} dependency on {src_ent.canonical_name}."
                    ),
                )
            )

        prompt_by_tier = {
            1: (
                f"[Tier 1 · Direct Link] Based on breaking updates around {src_ent.canonical_name} "
                f"in '{edge.source_niche_id}', which entity in '{edge.target_niche_id}' experiences the direct {edge.relation_type.value.lower()} impact?"
            ),
            2: (
                f"[Tier 2 · Cross-Niche Ripple] Connect the dots: How does today's development in "
                f"{src_ent.canonical_name} ({edge.source_niche_id}) cascade into '{edge.target_niche_id}'?"
            ),
            3: (
                f"[Tier 3 · Second-Order Trap] Consensus focuses on headline noise around {src_ent.canonical_name}. "
                f"Which cross-domain entity in '{edge.target_niche_id}' faces the non-obvious structural bottleneck?"
            ),
        }

        return QuizQuestion(
            question_id=f"quiz_{edge.edge_id}_t{tier}",
            tier=tier,
            difficulty_elo=ideal_diff,
            niche_ids=niche_ids,
            prompt=prompt_by_tier[tier],
            source_attribution=f"Synthesized across {edge.source_niche_id} & {edge.target_niche_id}",
            options=options,
            talking_point_one_liner=edge.talking_point_one_liner,
            mechanism_explanation=edge.mechanism_rationale,
            time_limit_seconds=20 if tier < 3 else 25,
        )
