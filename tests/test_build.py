from __future__ import annotations

import json
import re
import threading
import urllib.request

import pytest
from typer.testing import CliRunner

from codewalk.build import DATA_PLACEHOLDER, TEMPLATE, TITLE_PLACEHOLDER, build_html, embed
from codewalk.cli import app
from codewalk.errors import CodewalkError
from codewalk.serve import make_server, server_url
from conftest import MINIPROJ

runner = CliRunner()
DATA_BLOCK = re.compile(r'<script id="codewalk-data" type="application/json">(.*?)</script>', re.S)


def extract(page: str) -> dict:
    m = DATA_BLOCK.search(page)
    assert m, "data block not found"
    return json.loads(m.group(1))


def test_template_is_shipped_with_placeholders():
    assert TEMPLATE.is_file(), "build the viewer: npm install && npm run build in viewer/"
    text = TEMPLATE.read_text(encoding="utf-8")
    assert DATA_PLACEHOLDER in text and TITLE_PLACEHOLDER in text
    assert text.count(DATA_PLACEHOLDER) == 1
    assert "<script type=\"module\" src=" not in text, "the template must be a single file with inlined scripts"


def test_embed_round_trips_and_escapes():
    recording = {"title": "A </script> & <b>", "steps": [{"text": "x </script> y", "html": "<\\/escaped>"}], "n": 1.5}
    page = embed(recording)
    assert "<title>A &lt;/script&gt; &amp; &lt;b&gt;</title>" in page
    assert DATA_PLACEHOLDER not in page and TITLE_PLACEHOLDER not in page
    assert extract(page) == recording


def test_embed_fails_without_template(tmp_path):
    with pytest.raises(CodewalkError, match="missing"):
        embed({"title": "x"}, template_path=tmp_path / "nope.html")
    bad = tmp_path / "bad.html"
    bad.write_text("<html></html>")
    with pytest.raises(CodewalkError, match="placeholder"):
        embed({"title": "x"}, template_path=bad)


def test_build_html_default_and_explicit_output(tmp_path):
    steps = tmp_path / "steps.json"
    steps.write_text(json.dumps({"title": "T", "steps": []}))
    out = build_html(steps)
    assert out == tmp_path / "index.html"
    assert extract(out.read_text())["title"] == "T"
    custom = build_html(steps, tmp_path / "pages" / "walk.html")
    assert custom.is_file() and custom.parent.name == "pages"
    (tmp_path / "broken.json").write_text("{")
    with pytest.raises(CodewalkError, match="not valid JSON"):
        build_html(tmp_path / "broken.json")


def test_cli_build_and_record_produce_index_html(tmp_path):
    out = tmp_path / "out"
    result = runner.invoke(app, ["record", str(MINIPROJ / "walkthrough.py"), "-o", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "index.html").is_file() and (out / "steps.json").is_file()
    page = (out / "index.html").read_text()
    assert extract(page)["title"] == "Mini project"
    assert "<title>Mini project</title>" in page

    only = tmp_path / "only"
    result = runner.invoke(app, ["record", str(MINIPROJ / "walkthrough.py"), "-o", str(only), "--json-only"])
    assert result.exit_code == 0, result.output
    assert (only / "steps.json").is_file() and not (only / "index.html").exists()

    result = runner.invoke(app, ["build", str(only / "steps.json"), "-o", str(only / "page.html")])
    assert result.exit_code == 0, result.output
    assert (only / "page.html").is_file() and "wrote" in result.output


def test_serve_static_files(tmp_path):
    (tmp_path / "index.html").write_text("<html><body>hello walkthrough</body></html>")
    (tmp_path / "steps.json").write_text("{}")
    server = make_server(tmp_path, port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = server_url(server)
        assert url.startswith("http://127.0.0.1:")
        with urllib.request.urlopen(url) as res:
            body = res.read().decode()
            assert res.status == 200 and "hello walkthrough" in body
            assert res.headers["Cache-Control"] == "no-store"
        with urllib.request.urlopen(url + "steps.json") as res:
            assert res.read() == b"{}"
        with pytest.raises(urllib.error.HTTPError) as info:
            urllib.request.urlopen(url + "missing.txt")
        assert info.value.code == 404
    finally:
        server.shutdown()
        server.server_close()
