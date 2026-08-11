"""乐谱 JSON 序列化/反序列化。带 version 字段，未来 schema 演进可迁移。"""
from __future__ import annotations

import json
from pathlib import Path

from .model import Note, Score, Track

SCHEMA_VERSION = 1


def to_json(score: Score) -> str:
    data = {
        "version": SCHEMA_VERSION,
        "title": score.title,
        "tempo_bpm": score.tempo_bpm,
        "tracks": [
            {
                "id": t.id,
                "name": t.name,
                "instrument": t.instrument,
                "gain_db": t.gain_db,
                "pan": t.pan,
                "notes": [
                    {
                        "start_beat": n.start_beat,
                        "duration": n.duration,
                        "pitch": n.pitch,
                        "velocity": n.velocity,
                        "technique": n.technique,
                    }
                    for n in t.notes
                ],
            }
            for t in score.tracks
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def from_json(text: str) -> Score:
    data = json.loads(text)
    tracks = [
        Track(
            id=t["id"],
            name=t.get("name", t["id"]),
            instrument=t["instrument"],
            gain_db=t.get("gain_db", 0.0),
            pan=t.get("pan", 0.0),
            notes=[
                Note(
                    start_beat=n["start_beat"],
                    duration=n["duration"],
                    pitch=n["pitch"],
                    velocity=n.get("velocity", 100),
                    technique=n.get("technique"),
                )
                for n in t.get("notes", [])
            ],
        )
        for t in data.get("tracks", [])
    ]
    return Score(
        title=data.get("title", "untitled"),
        tempo_bpm=float(data.get("tempo_bpm", 90.0)),
        tracks=tracks,
    )


def save(score: Score, path: str | Path) -> None:
    Path(path).write_text(to_json(score), encoding="utf-8")


def load(path: str | Path) -> Score:
    return from_json(Path(path).read_text(encoding="utf-8"))
