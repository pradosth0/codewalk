from __future__ import annotations

import base64
import io
import json

from PIL import Image

from codewalk import load_walkthrough
from codewalk.check import analyze
from codewalk.recorder import Recording, record
from conftest import FIXTURES

DATAPROJ = FIXTURES / "dataproj"
_cache: dict[str, Recording] = {}


def recording(backend: str) -> Recording:
    if backend not in _cache:
        walkthrough = load_walkthrough(DATAPROJ / "walkthrough.py")
        report = analyze(walkthrough.spec)
        assert report.ok and report.warnings == [], [str(p) for p in report.problems()]
        _cache[backend] = record(walkthrough.spec, backend=backend, report=report)
    return _cache[backend]


def objects(rec: Recording, step_id: str) -> dict:
    step = next(s for s in rec.steps if s["id"] == step_id)
    return {o["name"]: o["display"] for o in step["objects"]}


def decode(display: dict) -> Image.Image:
    assert display["kind"] == "image" and display["mime"] == "image/png"
    img = Image.open(io.BytesIO(base64.b64decode(display["data"])))
    assert (img.width, img.height) == (display["width"], display["height"])
    return img


def test_every_display_kind_is_produced(backend):
    rec = recording(backend)
    assert rec.warnings == [] and not rec.crashed
    assert [s["id"] for s in rec.steps] == ["frame", "X", "model", "figure", "thumb", "cube"]
    kinds = {(s["id"], o["name"]): o["display"]["kind"] for s in rec.steps for o in s["objects"]}
    assert kinds == {
        ("frame", "df"): "table",
        ("frame", "head"): "table",
        ("frame", "y"): "table",
        ("X", "X"): "array",
        ("X", "first"): "json",
        ("model", "model"): "html",
        ("model", "w"): "json",
        ("figure", "fig"): "image",
        ("figure", "ax"): "image",
        ("thumb", "img"): "image",
        ("thumb", "raw"): "image",
        ("thumb", "gray"): "image",
        ("cube", "cube"): "array",
        ("cube", "everything"): "json",
    }
    data = json.loads(rec.to_json())  # strict JSON, no NaN
    assert data["schema"]["nodes"] == ["load", "feats", "fit", "plot", "thumb"]
    assert "done" in rec.steps[-1]["console"]


def test_table_details(backend):
    rec = recording(backend)
    frame = objects(rec, "frame")
    df = frame["df"]
    assert df["shape"] == [30, 4] and df["columns"] == ["x", "y", "label", "when"]
    assert len(df["rows"]) == 20 and df["truncated"]
    assert df["rows"][2][1] is None  # the NaN planted in row 2
    assert df["rows"][0][3] == "2024-01-01T00:00:00"
    assert df["dtypes"]["label"] == "object" or df["dtypes"]["label"].startswith("str")
    head = frame["head"]
    assert head["shape"] == [3, 4] and not head["truncated"]
    y = frame["y"]
    assert y["columns"] == ["y"] and y["type"] == "pandas.Series"
    step = next(s for s in rec.steps if s["id"] == "frame")
    assert step["text"].startswith("The frame has ") and step["text"].endswith(".")
    assert len(step["text"]) < 260  # a DataFrame placeholder is cut to 200 characters


def test_array_details(backend):
    rec = recording(backend)
    X = objects(rec, "X")["X"]
    assert X["shape"] == [30, 2] and X["dtype"] == "float64" and X["library"] == "numpy"
    assert X["stats"]["min"] == 0.0 and X["stats"]["max"] == 29**2 and X["stats"]["nan"] == 0
    assert X["preview_shape"] == [6, 2] and X["truncated"]
    assert objects(rec, "X")["first"] == {"kind": "json", "value": 0.0, "type": "numpy.float64"}
    cube = objects(rec, "cube")["cube"]
    assert cube["shape"] == [2, 3, 4] and cube["dtype"] == "int32"
    assert cube["preview_index"] == [0] and cube["preview"][0] == [0, 1, 2, 3]
    everything = objects(rec, "cube")["everything"]
    assert everything["kind"] == "json" and len(everything["value"]) == 6
    assert "TinyModel object" in everything["value"][2]


def test_html_and_images(backend):
    rec = recording(backend)
    model = objects(rec, "model")
    assert model["model"]["html"].startswith("<table class='tiny'>")
    assert model["w"]["kind"] == "json" and isinstance(model["w"]["value"], float)
    figure = objects(rec, "figure")
    for name in ("fig", "ax"):
        assert decode(figure[name]).width > 100
    assert figure["fig"]["type"] == "matplotlib.Figure" and figure["ax"]["type"] == "matplotlib.Axes"
    thumb = objects(rec, "thumb")
    assert decode(thumb["img"]).size == (40, 30) and thumb["img"]["type"] == "PIL.Image"
    raw = decode(thumb["raw"])
    assert raw.mode == "RGBA" and thumb["raw"]["type"] == "image"
    gray = decode(thumb["gray"])
    assert gray.mode == "L" and gray.size == raw.size


def test_cw_namespace_does_not_leak_into_the_program(backend):
    rec = recording(backend)
    step = next(s for s in rec.steps if s["id"] == "thumb")
    names = {o["name"] for o in step["objects"]}
    assert names == {"img", "raw", "gray"}
    assert "cw" not in step["code"]["source"]
