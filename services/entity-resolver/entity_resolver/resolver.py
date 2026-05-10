"""EntityResolver — deduplication and case resolution logic."""

from __future__ import annotations

import json
import os
import uuid
from datetime import date

import anthropic
import numpy as np
import structlog
from sentence_transformers import SentenceTransformer

from nyaya_shared.models import ExtractedCase
from nyaya_shared.privacy_utils import victim_pseudonym
from nyaya_shared.state_codes import STATE_CODES  # noqa: F401 (available for callers)

logger = structlog.get_logger()

DEDUP_PROMPT = """You are a legal case deduplication expert for India.

Given two crime cases, determine if they describe the SAME real-world criminal case.
Consider: FIR numbers, police stations, court case numbers, crime type, location, approximate dates.
Be conservative — only confirm same case if evidence is strong.

Case A:
{case_a}

Case B:
{case_b}

Output ONLY this JSON:
{{"same_case": <true|false>, "confidence": <0.0-1.0>, "reasoning": "<brief reason>"}}"""


class ResolutionResult:
    """Result of resolving an extracted case to a canonical case record."""

    def __init__(
        self,
        case_id: uuid.UUID,
        resolution_method: str,
        confidence: float,
        is_new: bool = False,
    ) -> None:
        self.case_id = case_id
        self.resolution_method = resolution_method
        self.confidence = confidence
        self.is_new = is_new


class EntityResolver:
    """Resolves an ExtractedCase to an existing or new canonical Case row."""

    def __init__(self, db_session_factory) -> None:  # type: ignore[no-untyped-def]
        self._db = db_session_factory
        self._anthropic = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY", "")
        )
        self._embedding_model: SentenceTransformer | None = None
        self._model_name = os.environ.get(
            "EMBEDDING_MODEL",
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        )

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get_embedding_model(self) -> SentenceTransformer:
        if self._embedding_model is None:
            self._embedding_model = SentenceTransformer(self._model_name)
        return self._embedding_model

    def _build_case_text(self, case: ExtractedCase) -> str:
        parts = [
            f"crime: {case.crime_category}",
            f"state: {case.state} district: {case.district}",
        ]
        if case.fir_number:
            parts.append(f"FIR: {case.fir_number} PS: {case.fir_police_station}")
        if case.court_case_number:
            parts.append(f"court case: {case.court_case_number}")
        if case.ipc_sections:
            parts.append(f"IPC: {','.join(str(s) for s in case.ipc_sections)}")
        if case.incident_date:
            parts.append(f"date: {case.incident_date}")
        event_types = [e.event_type for e in case.events[:5]]
        if event_types:
            parts.append(f"events: {','.join(event_types)}")
        return " | ".join(parts)

    def _generate_case_ref(self, state: str, year: int, seq: int) -> str:
        return f"NYA-{year}-{state.upper()}-{seq:06d}"

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        return float(
            np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
        )

    # ── public API ────────────────────────────────────────────────────────────

    async def resolve(
        self,
        extracted: ExtractedCase,
        sanitized_article_id: uuid.UUID,
    ) -> ResolutionResult:
        """Resolve extracted case to existing or new case.

        Priority order:
        1. FIR exact match
        2. Court case exact match
        3. Embedding similarity (auto / LLM-verify / moderation queue)
        4. New case creation
        """
        async with self._db() as session:
            # 1. FIR exact match
            if extracted.fir_number and extracted.fir_police_station:
                result = await session.execute(
                    "SELECT id FROM cases "
                    "WHERE fir_number = $1 AND fir_police_station = $2 "
                    "AND is_suppressed = FALSE",
                    extracted.fir_number,
                    extracted.fir_police_station,
                )
                row = result.fetchone()
                if row:
                    return ResolutionResult(
                        case_id=row[0],
                        resolution_method="FIR_EXACT",
                        confidence=1.0,
                    )

            # 2. Court case exact match (checks all court number columns)
            if extracted.court_case_number:
                result = await session.execute(
                    "SELECT id FROM cases "
                    "WHERE (court_case_number = $1 "
                    "       OR sessions_case_number = $1 "
                    "       OR hc_case_number = $1) "
                    "AND is_suppressed = FALSE",
                    extracted.court_case_number,
                )
                row = result.fetchone()
                if row:
                    return ResolutionResult(
                        case_id=row[0],
                        resolution_method="COURT_EXACT",
                        confidence=0.98,
                    )

            # 3. Embedding similarity — LSH blocking: same state + crime_category
            candidate_result = await session.execute(
                "SELECT id, district, fir_number, court_case_number, "
                "       ipc_sections::text "
                "FROM cases "
                "WHERE state = $1 "
                "  AND crime_category = $2::crime_category "
                "  AND is_suppressed = FALSE "
                "LIMIT 200",
                extracted.state,
                extracted.crime_category,
            )
            candidates = candidate_result.fetchall()

            if candidates:
                model = self._get_embedding_model()
                query_text = self._build_case_text(extracted)
                query_embedding = model.encode(
                    query_text, normalize_embeddings=True
                )

                best_sim = 0.0
                best_case_id: uuid.UUID | None = None

                for row in candidates:
                    cand_text = (
                        f"crime: {extracted.crime_category} "
                        f"state: {extracted.state} "
                        f"district: {row[1] or ''} "
                        f"FIR: {row[2] or ''} "
                        f"court: {row[3] or ''} "
                        f"IPC: {row[4] or ''}"
                    )
                    cand_embedding = model.encode(
                        cand_text, normalize_embeddings=True
                    )
                    sim = self._cosine_similarity(query_embedding, cand_embedding)
                    if sim > best_sim:
                        best_sim = sim
                        best_case_id = row[0]

                auto_merge_threshold = float(
                    os.environ.get("AUTO_MERGE_THRESHOLD", "0.92")
                )
                llm_upper = float(os.environ.get("LLM_VERIFY_UPPER", "0.92"))
                llm_lower = float(os.environ.get("LLM_VERIFY_LOWER", "0.78"))
                moderation_lower = float(
                    os.environ.get("MODERATION_LOWER", "0.70")
                )

                if best_sim >= auto_merge_threshold and best_case_id:
                    return ResolutionResult(
                        case_id=best_case_id,
                        resolution_method="EMBEDDING_AUTO",
                        confidence=best_sim,
                    )

                if llm_lower <= best_sim < llm_upper and best_case_id:
                    llm_result = await self._llm_verify(
                        extracted, best_case_id, session
                    )
                    if (
                        llm_result["same_case"]
                        and llm_result["confidence"] >= 0.75
                    ):
                        return ResolutionResult(
                            case_id=best_case_id,
                            resolution_method="LLM_VERIFIED",
                            confidence=llm_result["confidence"],
                        )

                elif moderation_lower <= best_sim < llm_lower and best_case_id:
                    # Below LLM threshold — queue for human moderation,
                    # but still proceed to create a new case so the event
                    # is not lost.
                    logger.info(
                        "similarity_needs_moderation",
                        similarity=best_sim,
                        candidate=str(best_case_id),
                    )
                    await self._enqueue_moderation(
                        None, best_case_id, "LOW_SIMILARITY", session
                    )

            # 4. Create new case
            new_case_id = await self._create_new_case(extracted, session)
            return ResolutionResult(
                case_id=new_case_id,
                resolution_method="NEW_CASE",
                confidence=1.0,
                is_new=True,
            )

    # ── private helpers ───────────────────────────────────────────────────────

    async def _llm_verify(
        self,
        extracted: ExtractedCase,
        candidate_id: uuid.UUID,
        session,  # type: ignore[no-untyped-def]
    ) -> dict:
        case_a_text = self._build_case_text(extracted)

        result = await session.execute(
            "SELECT crime_category, state, district, fir_number, court_case_number "
            "FROM cases WHERE id = $1",
            candidate_id,
        )
        row = result.fetchone()
        if row:
            case_b_text = (
                f"crime: {row[0]} state: {row[1]} district: {row[2]} "
                f"FIR: {row[3]} court: {row[4]}"
            )
        else:
            case_b_text = "unknown"

        response = self._anthropic.messages.create(
            model=os.environ.get("DEDUP_MODEL", "claude-haiku-4-5-20251001"),
            max_tokens=256,
            temperature=0.0,
            messages=[
                {
                    "role": "user",
                    "content": DEDUP_PROMPT.format(
                        case_a=case_a_text, case_b=case_b_text
                    ),
                }
            ],
        )
        try:
            return json.loads(response.content[0].text)
        except (json.JSONDecodeError, IndexError):
            logger.warning("llm_verify_parse_error", candidate=str(candidate_id))
            return {
                "same_case": False,
                "confidence": 0.0,
                "reasoning": "parse error",
            }

    async def _enqueue_moderation(
        self,
        case_event_id: uuid.UUID | None,
        case_id: uuid.UUID,
        reason: str,
        session,  # type: ignore[no-untyped-def]
    ) -> None:
        await session.execute(
            "INSERT INTO moderation_queue "
            "(case_event_id, case_id, queue_reason, priority) "
            "VALUES ($1, $2, $3, $4)",
            case_event_id,
            case_id,
            reason,
            5,
        )
        await session.commit()

    async def _create_new_case(
        self,
        extracted: ExtractedCase,
        session,  # type: ignore[no-untyped-def]
    ) -> uuid.UUID:
        year = (
            extracted.incident_date.year
            if extracted.incident_date
            else date.today().year
        )

        state_upper = (extracted.state or "XX").upper()
        seq_result = await session.execute(
            "SELECT COALESCE(MAX(CAST(SPLIT_PART(case_ref, '-', 4) AS INTEGER)), 0) + 1 "
            "FROM cases "
            "WHERE state = $1 AND case_ref LIKE $2",
            state_upper,
            f"NYA-{year}-{state_upper}-%",
        )
        seq = seq_result.scalar() or 1

        case_ref = self._generate_case_ref(state_upper, year, seq)
        new_id = uuid.uuid4()
        pseudonym = victim_pseudonym(str(new_id))

        await session.execute(
            """INSERT INTO cases (
                id, case_ref, victim_pseudonym, crime_category, state, district,
                fir_number, fir_police_station, ipc_sections, pocso_applicable,
                court_case_number, num_victims, num_accused,
                incident_date, incident_date_approx, overall_confidence
            ) VALUES (
                $1, $2, $3, $4::crime_category, $5, $6,
                $7, $8, $9, $10,
                $11, $12, $13,
                $14, $15, $16
            )""",
            new_id,
            case_ref,
            pseudonym,
            extracted.crime_category,
            state_upper,
            extracted.district or "",
            extracted.fir_number,
            extracted.fir_police_station,
            extracted.ipc_sections,
            extracted.pocso_applicable,
            extracted.court_case_number,
            extracted.num_victims,
            extracted.num_accused,
            extracted.incident_date,
            extracted.incident_date_approx,
            extracted.overall_confidence,
        )
        await session.commit()
        logger.info("new_case_created", case_ref=case_ref, case_id=str(new_id))
        return new_id
