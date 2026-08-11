"""乐谱模型 JSON 往返测试（P1 尾声：渲染→保存→重载→再渲染闭环的数据基础）。"""
from __future__ import annotations

from omg.score import io as score_io
from omg.score.model import Note, Score, Track


def test_score_roundtrip():
    score = Score(
        title="t", tempo_bpm=72.5,
        tracks=[
            Track(id="v", name="violin", instrument="solo_violin", notes=[
                Note(0, 1.0, 60, 100, "arco_vib"),
                Note(1.0, 0.5, 62, 90, "spiccato"),
            ]),
        ],
    )
    text = score_io.to_json(score)
    assert '"version": 1' in text
    loaded = score_io.from_json(text)
    assert loaded.title == "t"
    assert loaded.tempo_bpm == 72.5
    assert len(loaded.tracks) == 1
    t = loaded.tracks[0]
    assert t.id == "v" and t.instrument == "solo_violin"
    assert len(t.notes) == 2
    assert t.notes[0].pitch == 60 and t.notes[0].technique == "arco_vib"
    assert t.notes[1].start_beat == 1.0 and t.notes[1].duration == 0.5


def test_score_roundtrip_defaults():
    """缺省字段（velocity/technique）应填默认值。"""
    text = '{"version":1,"title":"x","tempo_bpm":90,"tracks":[{"id":"a","name":"a",' \
           '"instrument":"i","notes":[{"start_beat":0,"duration":1,"pitch":60}]}]}'
    loaded = score_io.from_json(text)
    assert loaded.tracks[0].notes[0].velocity == 100
    assert loaded.tracks[0].notes[0].technique is None
