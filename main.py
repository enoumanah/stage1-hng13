# main.py
from fastapi import FastAPI, HTTPException, Query, Path
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import hashlib
import json
import sqlite3
import re

DB_PATH = "strings.db"

app = FastAPI(title="Backend Wizards - Stage 1 String Analyzer")


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def compute_properties(value: str) -> Dict[str, Any]:
    # length = number of characters
    length = len(value)

    # is_palindrome: case-insensitive, ignore whitespace and punctuation for better UX
    normalized = re.sub(r'[\W_]+', '', value.lower())
    is_pal = normalized == normalized[::-1] and len(normalized) > 0

    # unique characters: distinct characters (case-sensitive)
    unique_characters = len(set(value))

    # word count: split on whitespace
    words = re.findall(r'\S+', value)
    word_count = len(words)

    # sha256 hash
    h = sha256_id(value)

    # character frequency map: count exact characters
    freq: Dict[str, int] = {}
    for ch in value:
        freq[ch] = freq.get(ch, 0) + 1

    return {
        "length": length,
        "is_palindrome": is_pal,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "sha256_hash": h,
        "character_frequency_map": freq,
    }


# ---------- DB layer (SQLite) ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """CREATE TABLE IF NOT EXISTS strings (
            id TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            properties TEXT NOT NULL,
            created_at TEXT NOT NULL
        )"""
    )
    conn.commit()
    conn.close()


def insert_record(record_id: str, value: str, properties: dict, created_at: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO strings (id, value, properties, created_at) VALUES (?, ?, ?, ?)",
            (record_id, value, json.dumps(properties), created_at),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise
    conn.close()


def get_record_by_value(value: str) -> Optional[dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, value, properties, created_at FROM strings WHERE value = ?", (value,))
    row = cur.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row[0],
        "value": row[1],
        "properties": json.loads(row[2]),
        "created_at": row[3],
    }


def get_all_records() -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, value, properties, created_at FROM strings ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    result = []
    for r in rows:
        result.append({
            "id": r[0],
            "value": r[1],
            "properties": json.loads(r[2]),
            "created_at": r[3],
        })
    return result


def delete_by_value(value: str) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM strings WHERE value = ?", (value,))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return affected > 0


# ---------- Pydantic models ----------
class CreateStringRequest(BaseModel):
    value: str = Field(..., min_length=1, description="String to analyze")


class StringResponse(BaseModel):
    id: str
    value: str
    properties: Dict[str, Any]
    created_at: str


class ListResponse(BaseModel):
    data: List[StringResponse]
    count: int
    filters_applied: Dict[str, Any]


# ---------- App startup ----------
@app.on_event("startup")
def startup():
    init_db()


# ---------- Endpoints ----------

@app.post("/strings", response_model=StringResponse, status_code=201)
def create_string(payload: CreateStringRequest):
    value = payload.value
    if not isinstance(value, str):
        raise HTTPException(status_code=422, detail="Value must be a string.")

    existing = get_record_by_value(value)
    if existing:
        # 409 Conflict if already exists
        raise HTTPException(status_code=409, detail="String already exists.")

    props = compute_properties(value)
    created_at = utc_now_iso()
    try:
        insert_record(props["sha256_hash"], value, props, created_at)
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="String already exists (hash collision).")

    return {
        "id": props["sha256_hash"],
        "value": value,
        "properties": props,
        "created_at": created_at
    }


@app.get("/strings/{string_value}", response_model=StringResponse)
def get_string(string_value: str = Path(..., description="The exact string value to retrieve")):
    rec = get_record_by_value(string_value)
    if not rec:
        raise HTTPException(status_code=404, detail="String not found.")
    return rec


@app.get("/strings", response_model=ListResponse)
def list_strings(
    is_palindrome: Optional[bool] = Query(None),
    min_length: Optional[int] = Query(None, ge=0),
    max_length: Optional[int] = Query(None, ge=0),
    word_count: Optional[int] = Query(None, ge=0),
    contains_character: Optional[str] = Query(None, min_length=1, max_length=1),
):
    # Validate min <= max if both provided
    if min_length is not None and max_length is not None and min_length > max_length:
        raise HTTPException(status_code=400, detail="min_length cannot be greater than max_length.")

    all_records = get_all_records()
    filtered = []

    for r in all_records:
        p = r["properties"]
        ok = True
        if is_palindrome is not None and p.get("is_palindrome") != is_palindrome:
            ok = False
        if min_length is not None and p.get("length", 0) < min_length:
            ok = False
        if max_length is not None and p.get("length", 0) > max_length:
            ok = False
        if word_count is not None and p.get("word_count") != word_count:
            ok = False
        if contains_character is not None:
            # check exact character presence
            if contains_character not in r["value"]:
                ok = False
        if ok:
            filtered.append(r)

    filters_applied = {
        "is_palindrome": is_palindrome,
        "min_length": min_length,
        "max_length": max_length,
        "word_count": word_count,
        "contains_character": contains_character,
    }

    return {
        "data": filtered,
        "count": len(filtered),
        "filters_applied": filters_applied,
    }


# ---------- Natural language filtering ----------
def parse_nl_query(q: str) -> dict:
    """
    Very small heuristic parser translating English into filter dicts.
    Supported phrases:
      - "single word" -> word_count=1
      - "palindromic" or "palindrome" -> is_palindrome=True
      - "strings longer than N characters" -> min_length=N+1
      - "strings longer than 10 characters" -> min_length=11
      - "strings containing the letter z" -> contains_character=z
      - "strings that contain a" -> contains_character=a (first letter match)
    This is intentionally small and extensible.
    """
    ql = q.lower()
    filters = {}

    # word count heuristics
    if "single word" in ql or "one word" in ql:
        filters["word_count"] = 1

    # palindrome
    if "palindrom" in ql:  # matches palindrome/palindromic
        filters["is_palindrome"] = True

    # longer than N
    m = re.search(r"longer than (\d+)", ql)
    if m:
        n = int(m.group(1))
        filters["min_length"] = n + 1

    # contains letter <char>
    m2 = re.search(r"contain(?:s|ing)? the letter ([a-z])", ql)
    if m2:
        filters["contains_character"] = m2.group(1)

    # contains character: "containing the letter z" or "containing z"
    m3 = re.search(r"containing ([a-z])", ql)
    if m3 and "contains_character" not in filters:
        filters["contains_character"] = m3.group(1)

    # explicit: "that contain the first vowel" -> heuristic: 'a'
    if "first vowel" in ql:
        filters["contains_character"] = "a"

    # conflict checking (simple)
    # e.g., user asks for word_count=1 and min_length > 1000 -> not our job to detect all conflicts
    return filters


@app.get("/strings/filter-by-natural-language")
def filter_by_nl(query: str = Query(..., description="Natural language query")):
    try:
        parsed = parse_nl_query(query)
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to parse natural language query.")

    if not parsed:
        raise HTTPException(status_code=400, detail="No interpretable filters found in query.")

    # Reuse /strings filtering by passing parsed params
    try:
        resp = list_strings(
            is_palindrome=parsed.get("is_palindrome"),
            min_length=parsed.get("min_length"),
            max_length=parsed.get("max_length"),
            word_count=parsed.get("word_count"),
            contains_character=parsed.get("contains_character"),
        )
    except HTTPException as e:
        # propagate 422/400 from list_strings
        raise e

    return {
        "data": resp["data"],
        "count": resp["count"],
        "interpreted_query": {
            "original": query,
            "parsed_filters": parsed,
        }
    }


@app.delete("/strings/{string_value}", status_code=204)
def delete_string(string_value: str = Path(...)):
    existed = delete_by_value(string_value)
    if not existed:
        raise HTTPException(status_code=404, detail="String not found.")
    return
