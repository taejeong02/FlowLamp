"""Read-only access to the study records SQLite database."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date
from pathlib import Path
from typing import Any


class StudyRecordsError(RuntimeError):
    """Raised when study records cannot be read."""


class StudyRecordRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path).expanduser().resolve()

    def get_records(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[dict[str, Any]]:
        if not self.db_path.is_file():
            raise StudyRecordsError(f"Study records DB not found: {self.db_path}")

        query = """
            SELECT
                study_date,
                turtle_neck_count,
                drowsy_count,
                good_posture_time,
                total_study_time,
                pure_study_time,
                away_count,
                away_time,
                drowsy_time,
                posture_score,
                focus_score,
                total_score,
                created_at,
                updated_at
            FROM study_records
        """
        conditions: list[str] = []
        parameters: list[str] = []

        if start_date is not None:
            conditions.append("study_date >= ?")
            parameters.append(start_date.isoformat())
        if end_date is not None:
            conditions.append("study_date <= ?")
            parameters.append(end_date.isoformat())
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY study_date"

        uri = f"{self.db_path.as_uri()}?mode=ro"
        try:
            with closing(
                sqlite3.connect(uri, uri=True, timeout=2)
            ) as connection:
                connection.row_factory = sqlite3.Row
                rows = connection.execute(query, parameters).fetchall()
        except sqlite3.Error as exc:
            raise StudyRecordsError(f"Failed to read study records: {exc}") from exc

        return [dict(row) for row in rows]
