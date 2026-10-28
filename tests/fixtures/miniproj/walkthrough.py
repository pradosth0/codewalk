from codewalk import Walkthrough

walkthrough = Walkthrough(
    title="Mini project",
    entry="run.py --rows 5",
    schema=["Load", "Transform", "Accumulate", "Score"],
)

walkthrough.step(
    id="load",
    at="mini/stages.py::load",
    highlight="load",
    show={"n": "n"},
    text="Load {{n}} rows.",
)
walkthrough.step(
    id="total",
    after="mini/stages.py:18",
    highlight="transform",
    show={"total": "total", "out": "out"},
    text="The total is {{total}}.",
)
walkthrough.step(
    id="score",
    at="mini/stages.py::score",
    when="return",
    highlight="score",
    show={"result": "__return__"},
)
