"""乐谱模型 JSON 往返测试（P1 尾声：渲染→保存→重载→再渲染闭环的数据基础）。"""
from __future__ import annotations

from omg.score import io as score_io
from omg.score.model import Note, Score, Track, transpose


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
    """缺省字段（velocity/technique/gain_db/pan）应填默认值。"""
    text = '{"version":1,"title":"x","tempo_bpm":90,"tracks":[{"id":"a","name":"a",' \
           '"instrument":"i","notes":[{"start_beat":0,"duration":1,"pitch":60}]}]}'
    loaded = score_io.from_json(text)
    assert loaded.tracks[0].notes[0].velocity == 100
    assert loaded.tracks[0].notes[0].technique is None
    assert loaded.tracks[0].gain_db == 0.0
    assert loaded.tracks[0].pan == 0.0


def test_score_roundtrip_gain_pan():
    """gain_db/pan 往返保真。"""
    score = Score(tracks=[Track(id="a", name="a", instrument="i",
                                gain_db=-3.5, pan=0.6,
                                notes=[Note(0, 1.0, 60)])])
    loaded = score_io.from_json(score_io.to_json(score))
    t = loaded.tracks[0]
    assert t.gain_db == -3.5
    assert t.pan == 0.6


def test_transpose():
    """整体移调：所有音符平移，轨道参数保持。"""
    score = Score(tracks=[Track(id="a", name="a", instrument="i",
                                gain_db=-2, pan=0.5, notes=[
                                    Note(0, 1.0, 60, 100, "arco_vib"),
                                    Note(1.0, 0.5, 67, 90, None)])])
    shifted = transpose(score, -5)
    t = shifted.tracks[0]
    assert [n.pitch for n in t.notes] == [55, 62]
    assert t.gain_db == -2 and t.pan == 0.5
    assert t.notes[0].technique == "arco_vib"
