from __future__ import annotations

import base64
import dataclasses
import io
import json
import sys
import types

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from PIL import Image

import codewalk
from codewalk.display import encode_png, png_size, sniff_mime
from codewalk.serialize import (
    MAX_ROWS,
    apply_step_budget,
    cap_display,
    display_size,
    jsonable,
    to_display,
    type_name,
)


def strict(display: dict) -> dict:
    """Round-trip through strict JSON (no NaN/Infinity allowed)."""
    return json.loads(json.dumps(display, allow_nan=False))


def decode(display: dict) -> Image.Image:
    assert display["kind"] == "image" and display["mime"] == "image/png"
    img = Image.open(io.BytesIO(base64.b64decode(display["data"])))
    assert (img.width, img.height) == (display["width"], display["height"])
    return img


# ---------------------------------------------------------------- tables


def test_dataframe_table():
    df = pd.DataFrame(
        {
            "a": [1, 2, 3],
            "b": [1.5, np.nan, np.inf],
            "s": ["x", "y", None],
            "t": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
        }
    )
    d = strict(to_display(df))
    assert d["kind"] == "table" and d["type"] == "pandas.DataFrame"
    assert d["columns"] == ["a", "b", "s", "t"]
    assert d["index"] == [0, 1, 2]
    assert d["rows"][0] == [1, 1.5, "x", "2024-01-01T00:00:00"]
    assert d["rows"][1][1] is None  # NaN becomes null
    assert d["rows"][2][1] == "inf"
    assert d["rows"][2][2] is None
    assert d["shape"] == [3, 4]
    assert d["dtypes"]["a"] == "int64" and d["dtypes"]["t"].startswith("datetime64")
    assert d["truncated"] is False and d["index_name"] is None


def test_dataframe_truncation_and_index_name():
    df = pd.DataFrame({"v": range(50)}, index=pd.Index(range(50), name="row"))
    d = to_display(df)
    assert len(d["rows"]) == MAX_ROWS and d["truncated"] and d["shape"] == [50, 1]
    assert d["index_name"] == "row"
    wide = pd.DataFrame({f"c{i}": [i] for i in range(40)})
    w = to_display(wide)
    assert len(w["columns"]) == 30 and w["truncated"] and w["shape"] == [1, 40]


def test_series_and_multiindex():
    d = to_display(pd.Series([1, 2], name="score"))
    assert d["kind"] == "table" and d["columns"] == ["score"] and d["type"] == "pandas.Series"
    assert to_display(pd.Series([1.0]))["columns"] == ["value"]
    mi = pd.DataFrame({("a", "x"): [1], ("a", "y"): [2]})
    mi.index = pd.MultiIndex.from_tuples([("g", 1)], names=["group", "n"])
    d = to_display(mi)
    assert d["columns"] == ["a / x", "a / y"]
    assert d["index"] == ["g / 1"] and d["index_name"] == "group / n"


# ---------------------------------------------------------------- arrays


def test_numpy_arrays():
    a = np.array([[1.0, 2.0, np.nan], [4.0, np.inf, 6.0]])
    d = strict(to_display(a))
    assert d["kind"] == "array" and d["library"] == "numpy"
    assert d["dtype"] == "float64" and d["shape"] == [2, 3] and d["size"] == 6
    assert d["stats"] == {
        "min": 1.0,
        "max": 6.0,
        "mean": pytest.approx(13 / 4),
        "std": pytest.approx(float(np.std([1, 2, 4, 6]))),
        "nan": 1,
    }
    assert d["preview"] == [[1.0, 2.0, "NaN"], [4.0, "Infinity", 6.0]]
    assert d["preview_shape"] == [2, 3] and d["preview_index"] is None and d["truncated"] is False

    v = to_display(np.arange(100))
    assert v["preview_shape"] == [1, 20] and v["truncated"] and v["preview"][0][:3] == [0, 1, 2]
    assert v["stats"] == {"min": 0, "max": 99, "mean": 49.5, "std": pytest.approx(float(np.std(np.arange(100)))), "nan": 0}

    big = to_display(np.zeros((10, 10)))
    assert big["preview_shape"] == [6, 6] and big["truncated"]

    cube = to_display(np.arange(24).reshape(2, 3, 4))
    assert cube["preview_index"] == [0] and cube["preview_shape"] == [3, 4]
    assert cube["preview"][1] == [4, 5, 6, 7]

    scalar = to_display(np.array(3.5))
    assert scalar["shape"] == [] and scalar["preview"] == [[3.5]] and scalar["size"] == 1

    empty = to_display(np.array([]))
    assert empty["stats"] is None and empty["preview"] == [[]]

    flags = to_display(np.array([True, False, True, True]))
    assert flags["dtype"] == "bool" and flags["stats"]["mean"] == 0.75
    assert flags["preview"] == [[True, False, True, True]]

    objs = to_display(np.array(["a", "b"], dtype=object))
    assert objs["stats"] is None and objs["preview"] == [["a", "b"]]

    cplx = to_display(np.array([1 + 2j]))
    assert cplx["stats"] is None and cplx["preview"] == [["(1+2j)"]]


def test_numpy_scalars_and_jsonable():
    assert to_display(np.int64(7)) == {"kind": "json", "value": 7, "type": "numpy.int64"}
    assert to_display(np.float32("nan"))["value"] == "NaN"
    assert jsonable({"k": np.float64(1.5), "arr": (np.int32(1),)}) == {"k": 1.5, "arr": [1]}


def test_fake_torch_tensor(monkeypatch):
    fake = types.ModuleType("torch")

    class Tensor:
        def __init__(self, arr, dtype="torch.float32"):
            self._arr = arr
            self.dtype = dtype
            self.device = "cpu"

        def detach(self):
            return Tensor(self._arr, self.dtype)

        def cpu(self):
            return self

        def float(self):
            return Tensor(self._arr.astype(np.float32), "torch.float32")

        def numpy(self):
            return self._arr

    fake.Tensor = Tensor
    monkeypatch.setitem(sys.modules, "torch", fake)
    d = strict(to_display(Tensor(np.array([[1.0, 2.0]], dtype=np.float32))))
    assert d["kind"] == "array" and d["library"] == "torch"
    assert d["dtype"] == "torch.float32" and d["device"] == "cpu"
    assert d["shape"] == [1, 2] and d["preview"] == [[1.0, 2.0]]
    bf16 = to_display(Tensor(np.array([1.0], dtype=np.float32), "torch.bfloat16"))
    assert bf16["dtype"] == "torch.bfloat16" and bf16["preview"] == [[1.0]]


# ---------------------------------------------------------------- images


def test_matplotlib_figure_and_axes():
    fig, ax = plt.subplots(figsize=(2, 1.5))
    ax.plot([1, 2, 3])
    try:
        d = to_display(fig)
        img = decode(d)
        assert d["type"] == "matplotlib.Figure" and img.width > 50
        a = to_display(ax)
        assert a["kind"] == "image" and a["type"] == "matplotlib.Axes"
        assert plt.fignum_exists(fig.number)  # the recorder never closes figures
    finally:
        plt.close(fig)


def test_pil_image_and_repr_methods():
    img = Image.new("RGB", (8, 4), (255, 0, 0))
    d = to_display(img)
    assert decode(d).size == (8, 4) and d["type"] == "PIL.Image"
    assert to_display(Image.new("F", (3, 3)))["kind"] == "image"  # float mode goes through convert()

    class P:
        def _repr_png_(self):
            return encode_png(np.zeros((2, 2), dtype=np.uint8))

    assert decode(to_display(P())).size == (2, 2)

    class S:
        def _repr_svg_(self):
            return "<svg xmlns='http://www.w3.org/2000/svg' width='1' height='1'></svg>"

    d = to_display(S())
    assert d["kind"] == "image" and d["mime"] == "image/svg+xml" and d["width"] is None
    assert base64.b64decode(d["data"]).startswith(b"<svg")

    class N:
        def _repr_png_(self):
            return None

        def __repr__(self):
            return "N!"

    d = to_display(N())
    assert d["kind"] == "text" and d["text"] == "N!" and d["type"].endswith(".N")


def test_codewalk_image_arrays():
    rgb = np.zeros((3, 5, 3), dtype=np.uint8)
    rgb[..., 0] = 200
    d = to_display(codewalk.image(rgb))
    img = decode(d)
    assert img.size == (5, 3) and img.getpixel((0, 0)) == (200, 0, 0) and d["type"] == "image"

    gray = decode(to_display(codewalk.image(np.linspace(0, 1, 6).reshape(2, 3))))
    assert gray.mode == "L" and gray.getpixel((0, 0)) == 0 and gray.getpixel((2, 1)) == 255

    assert decode(to_display(codewalk.image(np.zeros((3, 4, 7), dtype=np.uint8)))).size == (7, 4)  # CHW
    assert decode(to_display(codewalk.image(np.full((2, 2, 4), 255, dtype=np.uint8)))).mode == "RGBA"

    ints = decode(to_display(codewalk.image(np.array([[0, 1000]], dtype=np.int64))))
    assert ints.getpixel((0, 0)) == 0 and ints.getpixel((1, 0)) == 255
    bools = decode(to_display(codewalk.image(np.array([[True, False]]))))
    assert bools.getpixel((0, 0)) == 255 and bools.getpixel((1, 0)) == 0

    png = encode_png(rgb)
    assert png_size(png) == (5, 3) and sniff_mime(png) == "image/png"
    raw = to_display(codewalk.image(png))
    assert raw["mime"] == "image/png" and raw["width"] == 5
    assert to_display(codewalk.image(b"<svg xmlns='x'/>"))["mime"] == "image/svg+xml"
    assert to_display(codewalk.image(b"\xff\xd8\xff\xe0junk"))["mime"] == "image/jpeg"

    bad = to_display(codewalk.image(np.zeros((2, 2, 2))))
    assert bad["kind"] == "text" and "expected an HxW" in bad["note"]


# ---------------------------------------------------------------- html, ordering, fallbacks


def test_html_and_ordering():
    class M:
        def _repr_html_(self):
            return "<b>hi</b>"

    d = to_display(M())
    assert d["kind"] == "html" and d["html"] == "<b>hi</b>"

    @dataclasses.dataclass
    class D:
        a: int

        def _repr_html_(self):
            return "<i>d</i>"

    assert to_display(D(1))["kind"] == "html"  # an explicit html repr wins over the json tree

    class NoneHtml:
        def _repr_html_(self):
            return None

    assert to_display(NoneHtml())["kind"] == "text"

    class Broken:
        def _repr_html_(self):
            raise RuntimeError("nope")

        def __repr__(self):
            return "B"

    d = to_display(Broken())
    assert d["kind"] == "text" and d["text"] == "B"
    assert d["note"] == "html_display failed: RuntimeError: nope"

    assert to_display({"a": 1})["kind"] == "json"
    assert to_display(pd.DataFrame({"a": [1]}))["kind"] == "table"  # pandas beats its own _repr_html_


def test_text_fallback_and_type_name():
    assert type_name(1) == "int" and type_name(pd.DataFrame()) == "pandas.DataFrame"

    class R:
        def __repr__(self):
            raise ValueError("bad repr")

    d = to_display(R())
    assert d["kind"] == "text" and "repr failed with ValueError" in d["text"]

    class Long:
        def __repr__(self):
            return "x" * 5000

    d = to_display(Long())
    assert d["truncated"] and len(d["text"]) == 2001


# ---------------------------------------------------------------- caps


def test_display_cap():
    class Big:
        def _repr_html_(self):
            return "x" * 3_000_000

    d = strict(to_display(Big()))
    assert d["kind"] == "text" and d["over_limit"]
    assert "html display" in d["text"] and "over the 2 MB limit per object" in d["text"]
    small = {"kind": "html", "html": "y" * 10, "type": "t"}
    assert cap_display(small) is small


def test_step_budget():
    objects = [
        {"name": f"o{i}", "expr": "", "display": {"kind": "html", "html": "z" * 1_500_000, "type": "t"}}
        for i in range(8)
    ]
    apply_step_budget(objects)
    kinds = [o["display"]["kind"] for o in objects]
    assert kinds == ["html"] * 6 + ["text", "text"]
    assert "exceed the 10 MB limit per step" in objects[6]["display"]["text"]
    assert objects[6]["display"]["over_limit"]
    assert sum(display_size(o["display"]) for o in objects) <= 10_000_000
