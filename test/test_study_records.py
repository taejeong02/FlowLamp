import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import date
from pathlib import Path

from flowlamp_rpi.study_records import StudyRecordRepository, StudyRecordsError


CREATE_TABLE_SQL = """
CREATE TABLE study_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_date TEXT UNIQUE,
    turtle_neck_count INTEGER,
    drowsy_count INTEGER,
    good_posture_time INTEGER,
    total_study_time INTEGER,
    pure_study_time INTEGER,
    away_count INTEGER,
    away_time INTEGER,
    drowsy_time INTEGER,
    posture_score INTEGER,
    focus_score INTEGER,
    total_score INTEGER,
    created_at TEXT,
    updated_at TEXT
)
"""


class StudyRecordRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "study_records.db"
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(CREATE_TABLE_SQL)
            connection.executemany(
                """
                INSERT INTO study_records (
                    study_date,
                    posture_score,
                    focus_score,
                    total_score
                ) VALUES (?, ?, ?, ?)
                """,
                [
                    ("2026-05-01", 40, 45, 85),
                    ("2026-05-02", 38, 42, 80),
                    ("2026-05-03", 41, 47, 88),
                ],
            )
            connection.commit()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_returns_records_in_date_order(self):
        records = StudyRecordRepository(self.db_path).get_records()

        self.assertEqual(
            [record["study_date"] for record in records],
            ["2026-05-01", "2026-05-02", "2026-05-03"],
        )
        self.assertEqual(records[0]["total_score"], 85)

    def test_filters_inclusive_date_range(self):
        records = StudyRecordRepository(self.db_path).get_records(
            start_date=date(2026, 5, 2),
            end_date=date(2026, 5, 2),
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["study_date"], "2026-05-02")

    def test_missing_database_raises_domain_error(self):
        missing_path = Path(self.temp_dir.name) / "missing.db"

        with self.assertRaises(StudyRecordsError):
            StudyRecordRepository(missing_path).get_records()


if __name__ == "__main__":
    unittest.main()
