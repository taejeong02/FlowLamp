import argparse
import os
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "study_records.db")
PARENT_DB_PATH = os.path.join(os.path.dirname(BASE_DIR), "study_records.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS study_records (
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


def get_table_columns(conn, table_name="study_records"):
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


def migrate_db_schema(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='study_records'")
    if not cursor.fetchone():
        conn.close()
        return

    columns = get_table_columns(conn)
    obsolete_columns = {"avg_head_angle", "head_angle_total", "head_angle_sample_count"}
    if not any(col in columns for col in obsolete_columns):
        conn.close()
        return

    keep_columns = [
        "id",
        "study_date",
        "turtle_neck_count",
        "drowsy_count",
        "good_posture_time",
        "total_study_time",
        "pure_study_time",
        "away_count",
        "away_time",
        "drowsy_time",
        "posture_score",
        "focus_score",
        "total_score",
        "created_at",
        "updated_at",
    ]
    keep_columns = [col for col in keep_columns if col in columns]

    cursor.execute("ALTER TABLE study_records RENAME TO study_records_old")
    cursor.execute(CREATE_TABLE_SQL)
    cols_sql = ", ".join(keep_columns)
    cursor.execute(f"INSERT INTO study_records ({cols_sql}) SELECT {cols_sql} FROM study_records_old")
    cursor.execute("DROP TABLE study_records_old")
    conn.commit()
    conn.close()


def init_db(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()
    migrate_db_schema(db_path)


def resolve_db_path():
    if os.path.exists(DB_PATH):
        return DB_PATH
    if os.path.exists(PARENT_DB_PATH):
        return PARENT_DB_PATH
    return DB_PATH


def get_records(db_path, study_date=None):
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

    db_path = resolve_db_path()

    if args.reset_db:
        if os.path.exists(db_path):
            os.remove(db_path)
        init_db(db_path)
        print(f"{db_path} 파일을 초기화하고 기존 데이터를 모두 삭제했습니다.")
        return

    init_db(db_path)

    if args.init_db:
        print(f"{db_path} 파일이 준비되었습니다.")
        return

    if args.show_db or args.show_date:
        records, columns = get_records(db_path, study_date=args.show_date)
        print_records(records, columns)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
