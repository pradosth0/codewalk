"""Turn captured Python values into display objects the viewer can render.

Kinds: table (pandas), array (numpy, torch), image (matplotlib, PIL, `_repr_png_`,
`_repr_svg_`, `codewalk.image`), html (`_repr_html_`), json (containers, dataclasses,
pydantic), text (repr fallback) and error. Every display is strict JSON. A display over
MAX_DISPLAY_BYTES, or a step over MAX_STEP_BYTES in total, is replaced by a text notice.
Optional libraries are never imported here: an object of theirs can only exist once its
library is loaded, so `sys.modules` is consulted instead.
"""

from __future__ import annotations

import base64
import dataclasses
import enum
import io
import json
import math
import numbers
import pathlib
import sys
from typing import Any, Callable, Iterable, Optional

from .display import ImageDisplay, png_size

Display = dict
Predicate = Callable[[Any], bool]
Serializer = Callable[[Any], Optional[Display]]  # None means "not mine after all"

MAX_TEXT = 2000
MAX_ITEMS = 200
MAX_DEPTH = 4
MAX_ROWS = 20
MAX_COLS = 30
PREVIEW_1D = 20
PREVIEW_2D = 6
FIGURE_DPI = 110
MAX_DISPLAY_BYTES = 2_000_000
MAX_STEP_BYTES = 10_000_000


def _module(name: str) -> Any:
    return sys.modules.get(name)


def type_name(value: Any) -> str:
    t = type(value)
    module = getattr(t, "__module__", None) or "builtins"
    if module in ("builtins", "__main__"):
        return t.__qualname__
    return f"{module.split('.')[0]}.{t.__qualname__}"


def safe_repr(value: Any, limit: int = MAX_TEXT) -> tuple[str, bool]:
    try:
        text = repr(value)
    except Exception as e:  # a broken __repr__ must not kill the recording
        text = f"<{type_name(value)} object: repr failed with {type(e).__name__}: {e}>"
    if len(text) > limit:
        return text[:limit] + "…", True
    return text, False


# --------------------------------------------------------------------------- text, error


def text_display(value: Any) -> Display:
    text, truncated = safe_repr(value)
    return {"kind": "text", "text": text, "truncated": truncated, "type": type_name(value)}


def error_display(exc: BaseException, names: Iterable[str] = ()) -> Display:
    return {"kind": "error", "message": f"{type(exc).__name__}: {exc}", "names": list(names)}


def plain_text(value: Any, limit: int = 200) -> str:
    """Short text form used for `{{placeholders}}` in step text."""
    if isinstance(value, str):
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return str(value)
    np = _module("numpy")
    if np is not None and isinstance(value, np.generic):
        return str(value.item())
    text, _ = safe_repr(value, limit)
    return text


# --------------------------------------------------------------------------- json


def _is_namedtuple(value: Any) -> bool:
    return isinstance(value, tuple) and hasattr(value, "_fields") and hasattr(value, "_asdict")


def _is_pydantic(value: Any) -> bool:
    return hasattr(value, "model_dump") and hasattr(type(value), "model_fields")


def is_jsonish(value: Any) -> bool:
    if isinstance(value, (type(None), bool, int, float, str, dict, list, tuple, set, frozenset)):
        return True
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return True
    return _is_namedtuple(value) or _is_pydantic(value) or isinstance(value, (enum.Enum, pathlib.PurePath))


def _key(k: Any) -> str:
    if isinstance(k, str):
        return k
    if isinstance(k, (bool, int, float)) or k is None:
        return str(k)
    text, _ = safe_repr(k, 80)
    return text


def jsonable(value: Any, depth: int = 0) -> Any:
    """Convert a value to strict JSON (no NaN/Infinity), with depth and size limits."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return float(value)
    np = _module("numpy")
    if np is not None and isinstance(value, np.generic):
        return jsonable(value.item(), depth)
    if isinstance(value, enum.Enum):
        return f"{type(value).__name__}.{value.name}"
    if isinstance(value, pathlib.PurePath):
        return str(value)
    if depth >= MAX_DEPTH:
        text, _ = safe_repr(value, 200)
        return text
    if _is_namedtuple(value):
        return {k: jsonable(v, depth + 1) for k, v in value._asdict().items()}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: jsonable(getattr(value, f.name), depth + 1) for f in dataclasses.fields(value)}
    if _is_pydantic(value):
        try:
            return jsonable(value.model_dump(), depth + 1)
        except Exception:
            text, _ = safe_repr(value, 200)
            return text
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for i, (k, v) in enumerate(value.items()):
            if i >= MAX_ITEMS:
                out["…"] = f"{len(value) - MAX_ITEMS} more"
                break
            out[_key(k)] = jsonable(v, depth + 1)
        return out
    if isinstance(value, (list, tuple, set, frozenset)):
        items = list(value)
        out_list = [jsonable(v, depth + 1) for v in items[:MAX_ITEMS]]
        if len(items) > MAX_ITEMS:
            out_list.append(f"… {len(items) - MAX_ITEMS} more")
        return out_list
    text, _ = safe_repr(value, 200)
    return text


def json_display(value: Any) -> Display:
    return {"kind": "json", "value": jsonable(value), "type": type_name(value)}


# --------------------------------------------------------------------------- table (pandas)


def _is_pandas(value: Any) -> bool:
    pd = _module("pandas")
    return pd is not None and isinstance(value, (pd.DataFrame, pd.Series))


def _label(name: Any) -> str:
    if isinstance(name, tuple):
        return " / ".join(str(p) for p in name)
    return str(name)


def _cell(value: Any, pd: Any) -> Any:
    if value is None:
        return None
    try:
        na = pd.isna(value)
        if (isinstance(na, bool) or getattr(na, "shape", None) == ()) and bool(na):
            return None
    except (TypeError, ValueError):
        pass
    np = _module("numpy")
    if isinstance(value, bool) or (np is not None and isinstance(value, np.bool_)):
        return bool(value)
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, numbers.Real):
        f = float(value)
        return f if math.isfinite(f) else str(f)
    if isinstance(value, str):
        return value if len(value) <= 200 else value[:200] + "…"
    iso = getattr(value, "isoformat", None)
    if callable(iso):
        try:
            return iso()
        except Exception:
            pass
    text, _ = safe_repr(value, 200)
    return text


def table_display(value: Any) -> Display:
    pd = _module("pandas")
    if isinstance(value, pd.Series):
        frame = value.to_frame(name=value.name if value.name is not None else "value")
    else:
        frame = value
    n_rows, n_cols = frame.shape
    head = frame.iloc[:MAX_ROWS, :MAX_COLS]
    columns = [_label(c) for c in head.columns]
    index = [_label(i) if isinstance(i, tuple) else _cell(i, pd) for i in head.index]
    rows = [[_cell(v, pd) for v in row] for row in head.itertuples(index=False, name=None)]
    dtypes = {_label(c): str(dt) for c, dt in head.dtypes.items()}
    names = [n for n in getattr(frame.index, "names", [frame.index.name]) if n is not None]
    return {
        "kind": "table",
        "columns": columns,
        "index": index,
        "index_name": " / ".join(str(n) for n in names) if names else None,
        "rows": rows,
        "shape": [int(n_rows), int(n_cols)],
        "dtypes": dtypes,
        "truncated": bool(n_rows > MAX_ROWS or n_cols > MAX_COLS),
        "type": type_name(value),
    }


# --------------------------------------------------------------------------- array (numpy, torch)


def _is_ndarray(value: Any) -> bool:
    np = _module("numpy")
    return np is not None and isinstance(value, np.ndarray)


def _is_numpy_scalar(value: Any) -> bool:
    np = _module("numpy")
    return np is not None and isinstance(value, np.generic)


def _is_torch_tensor(value: Any) -> bool:
    torch = _module("torch")
    return torch is not None and isinstance(value, torch.Tensor)


def _num(v: Any) -> Any:
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        try:
            v = v.item()
        except Exception:
            pass
    if isinstance(v, bool):
        return v
    if isinstance(v, numbers.Integral):
        return int(v)
    if isinstance(v, numbers.Real):
        f = float(v)
        if math.isnan(f):
            return "NaN"
        if math.isinf(f):
            return "Infinity" if f > 0 else "-Infinity"
        return f
    if isinstance(v, complex):
        return str(v)
    if isinstance(v, str):
        return v[:200]
    text, _ = safe_repr(v, 100)
    return text


def _array_stats(arr: Any, np: Any) -> Optional[dict]:
    if arr.size == 0:
        return None
    if arr.dtype == np.bool_:
        data = arr.astype(np.float64)
    elif np.issubdtype(arr.dtype, np.number) and not np.issubdtype(arr.dtype, np.complexfloating):
        data = arr
    else:
        return None
    with np.errstate(all="ignore"):
        if np.issubdtype(data.dtype, np.floating):
            nan = int(np.isnan(data).sum())
            finite = data[np.isfinite(data)]
        else:
            nan = 0
            finite = data.reshape(-1)
        if finite.size == 0:
            return {"min": None, "max": None, "mean": None, "std": None, "nan": nan}
        return {
            "min": _num(finite.min()),
            "max": _num(finite.max()),
            "mean": _num(finite.mean()),
            "std": _num(finite.std()),
            "nan": nan,
        }


def _array_preview(arr: Any) -> tuple[list, list[int], Optional[list[int]]]:
    if arr.ndim == 0:
        return [[_num(arr[()])]], [1, 1], None
    if arr.ndim == 1:
        row = arr[:PREVIEW_1D]
        return [[_num(v) for v in row]], [1, int(len(row))], None
    index = None
    view = arr
    if arr.ndim > 2:
        index = [0] * (arr.ndim - 2)
        view = arr[tuple(index)]
    block = view[:PREVIEW_2D, :PREVIEW_2D]
    return [[_num(v) for v in row] for row in block], [int(block.shape[0]), int(block.shape[1])], index


def array_display(value: Any) -> Display:
    np = _module("numpy")
    if np is None:
        raise TypeError("numpy is required to display arrays")
    extra: dict[str, Any] = {}
    if _is_torch_tensor(value):
        library = "torch"
        dtype = str(value.dtype)
        extra["device"] = str(value.device)
        tensor = value.detach().cpu()
        if str(tensor.dtype) == "torch.bfloat16":
            tensor = tensor.float()
        arr = tensor.numpy()
    else:
        library = "numpy"
        arr = value
        dtype = str(arr.dtype)
    preview, preview_shape, index = _array_preview(arr)
    shown = preview_shape[0] * preview_shape[1]
    return {
        "kind": "array",
        "library": library,
        "dtype": dtype,
        "shape": [int(s) for s in arr.shape],
        "size": int(arr.size),
        "stats": _array_stats(arr, np),
        "preview": preview,
        "preview_shape": preview_shape,
        "preview_index": index,
        "truncated": bool(arr.size > shown),
        "type": type_name(value),
        **extra,
    }


def numpy_scalar_display(value: Any) -> Display:
    return {"kind": "json", "value": jsonable(value.item()), "type": type_name(value)}


# --------------------------------------------------------------------------- image


def image_display_from_bytes(data: bytes, mime: str, type_: str) -> Display:
    width, height = png_size(data) if mime == "image/png" else (None, None)
    return {
        "kind": "image",
        "mime": mime,
        "data": base64.b64encode(data).decode("ascii"),
        "width": width,
        "height": height,
        "type": type_,
    }


def _is_image_display(value: Any) -> bool:
    return isinstance(value, ImageDisplay)


def wrapped_image_display(value: ImageDisplay) -> Display:
    data, mime = value.encoded()
    return image_display_from_bytes(data, mime, "image")


def _is_figure_like(value: Any) -> bool:
    figure_mod = _module("matplotlib.figure")
    if figure_mod is None:
        return False
    if isinstance(value, figure_mod.FigureBase):
        return True
    axes_mod = _module("matplotlib.axes")
    return axes_mod is not None and isinstance(value, axes_mod.Axes)


def _root_figure(value: Any) -> Any:
    figure_mod = _module("matplotlib.figure")
    fig = value
    for _ in range(6):
        if isinstance(fig, figure_mod.Figure):
            return fig
        fig = getattr(fig, "figure", None)
        if fig is None:
            break
    raise TypeError(f"could not find the Figure behind {type_name(value)}")


def figure_display(value: Any) -> Display:
    fig = _root_figure(value)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=FIGURE_DPI, bbox_inches="tight")
    return image_display_from_bytes(buf.getvalue(), "image/png", type_name(value))


def _is_pil_image(value: Any) -> bool:
    image_mod = _module("PIL.Image")
    return image_mod is not None and isinstance(value, image_mod.Image)


def pil_display(value: Any) -> Display:
    buf = io.BytesIO()
    try:
        value.save(buf, format="PNG")
    except Exception:
        buf = io.BytesIO()
        value.convert("RGB").save(buf, format="PNG")
    return image_display_from_bytes(buf.getvalue(), "image/png", type_name(value))


def _has_method(value: Any, name: str) -> bool:
    return callable(getattr(type(value), name, None))


def repr_png_display(value: Any) -> Optional[Display]:
    data = value._repr_png_()
    if data is None:
        return None
    if isinstance(data, str):
        data = base64.b64decode(data)
    return image_display_from_bytes(bytes(data), "image/png", type_name(value))


def repr_svg_display(value: Any) -> Optional[Display]:
    data = value._repr_svg_()
    if data is None:
        return None
    if isinstance(data, str):
        data = data.encode("utf-8")
    return image_display_from_bytes(bytes(data), "image/svg+xml", type_name(value))


# --------------------------------------------------------------------------- html


def html_display(value: Any) -> Optional[Display]:
    html = value._repr_html_()
    if html is None:
        return None
    return {"kind": "html", "html": str(html), "type": type_name(value)}


# --------------------------------------------------------------------------- caps


def display_size(display: Display) -> int:
    return len(json.dumps(display, ensure_ascii=False, allow_nan=False))


def over_limit_display(display: Display, size: int, limit: int, scope: str) -> Display:
    kind = display.get("kind", "?")
    type_ = display.get("type", "object")
    if scope == "display":
        advice = "show a smaller piece instead (df.head(), arr[:10], a smaller figure)"
        text = (
            f"<{kind} display of {type_} is {size / 1e6:.1f} MB, over the "
            f"{limit / 1e6:.0f} MB limit per object; {advice}>"
        )
    else:
        text = (
            f"<{kind} display of {type_} ({size / 1e6:.1f} MB) dropped: this step's objects "
            f"exceed the {limit / 1e6:.0f} MB limit per step; show fewer or smaller objects>"
        )
    return {"kind": "text", "text": text, "truncated": True, "type": type_, "over_limit": True}


def cap_display(display: Display, limit: int = MAX_DISPLAY_BYTES) -> Display:
    size = display_size(display)
    if size <= limit:
        return display
    return over_limit_display(display, size, limit, "display")


def apply_step_budget(objects: list[dict], limit: int = MAX_STEP_BYTES) -> list[dict]:
    """Keep the total size of a step's displays under `limit`, dropping the ones that overflow."""
    total = 0
    for obj in objects:
        size = display_size(obj["display"])
        if total + size > limit:
            obj["display"] = over_limit_display(obj["display"], size, limit, "step")
            size = display_size(obj["display"])
        total += size
    return objects


# --------------------------------------------------------------------------- registry

_registry: list[tuple[Predicate, Serializer]] = [
    (_is_image_display, wrapped_image_display),
    (_is_pandas, table_display),
    (_is_ndarray, array_display),
    (_is_torch_tensor, array_display),
    (_is_numpy_scalar, numpy_scalar_display),
    (_is_figure_like, figure_display),
    (_is_pil_image, pil_display),
    (lambda v: _has_method(v, "_repr_png_"), repr_png_display),
    (lambda v: _has_method(v, "_repr_svg_"), repr_svg_display),
    (lambda v: _has_method(v, "_repr_html_"), html_display),
    (is_jsonish, json_display),
]


def register(predicate: Predicate, serializer: Serializer, *, first: bool = False) -> None:
    """Add a serializer. Predicates are tried in order; the first one whose serializer
    returns a display wins. A serializer may return None to pass."""
    if first:
        _registry.insert(0, (predicate, serializer))
    else:
        _registry.append((predicate, serializer))


def to_display(value: Any) -> Display:
    """Serialize any value. Never raises; a failing serializer falls back to text with a note."""
    for predicate, serializer in _registry:
        try:
            matched = predicate(value)
        except Exception:
            matched = False
        if not matched:
            continue
        try:
            display = serializer(value)
        except Exception as e:
            display = text_display(value)
            display["note"] = f"{serializer.__name__} failed: {type(e).__name__}: {e}"
        if display is None:
            continue
        return cap_display(display)
    return cap_display(text_display(value))
