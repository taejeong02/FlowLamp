import argparse
import os
import sqlite3
from datetime import datetime

DB_PATH = "study_records.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS study_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    study_date TEXT UNIQUE,
    turtle_neck_count INTEGER,
    drowsy_count INTEGER,
    avg_head_angle REAL,
    head_angle_total REAL,
    head_angle_sample_count INTEGER,
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


def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()


def get_records(db_path=DB_PATH, study_date=None):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM study_records"
    params = ()
    if study_date:
        query += " WHERE study_date = ?"
        params = (study_date,)

    query += " ORDER BY study_date"
    cursor.execute(query, params)

    rows = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()
    return rows, columns


def seconds_to_hms(seconds):
    seconds = int(seconds)
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def print_records(records, columns):
    if not records:
        print("DB에 저장된 학습 기록이 없습니다.")
        return

    for row in records:
        record = dict(zip(columns, row))

        print("-" * 80)
        for column in columns:
            if column == "drowsy_score":
                continue
            value = record[column]
            if column in ("good_posture_time", "total_study_time", "pure_study_time", "away_time", "drowsy_time"):
                value = seconds_to_hms(value)
            print(f"{column}: {value}")


def main():
    parser = argparse.ArgumentParser(description="study_records.db에서 누적 학습 데이터를 조회합니다.")
    parser.add_argument("--show-db", action="store_true", help="모든 DB 레코드를 출력합니다.")
    parser.add_argument("--show-date", type=str, help="특정 날짜의 레코드만 출력합니다. 예: 2026-05-22")
    parser.add_argument("--init-db", action="store_true", help="DB 파일과 테이블을 생성 또는 준비합니다.")
    parser.add_argument("--reset-db", action="store_true", help="기존 DB 파일을 삭제하고 새로 초기화합니다.")
    args = parser.parse_args()

    if args.reset_db:
        if os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        init_db()
        print(f"{DB_PATH} 파일을 초기화하고 기존 데이터를 모두 삭제했습니다.")
        return

    init_db()

    if args.init_db:
        print(f"{DB_PATH} 파일이 준비되었습니다.")
        return

    if args.show_db or args.show_date:
        records, columns = get_records(study_date=args.show_date)
        print_records(records, columns)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
