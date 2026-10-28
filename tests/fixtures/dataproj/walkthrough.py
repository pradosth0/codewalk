from codewalk import Walkthrough

walkthrough = Walkthrough(
    title="Data pipeline",
    entry="pipeline.py",
    schema="""
    flowchart LR
      load[Load] --> feats[Features] --> fit[Fit] --> plot[Plot] --> thumb[Thumbnail]
    """,
)

walkthrough.step(
    id="frame",
    at="pipeline.py::features",
    highlight="feats",
    show={"df": "df", "head": "df.head(3)", "y": "df['y']"},
    text="The frame has {{head}}.",
)
walkthrough.step(
    id="X",
    after="pipeline.py:37",
    highlight="feats",
    show={"X": "X", "first": "X[0, 0]"},
)
walkthrough.step(
    id="model",
    at="pipeline.py::fit",
    when="return",
    highlight="fit",
    show={"model": "__return__", "w": "w"},
)
walkthrough.step(
    id="figure",
    at="pipeline.py::thumbnail",
    highlight="plot",
    show={"fig": "fig", "ax": "fig.axes[0]"},
)
walkthrough.step(
    id="thumb",
    at="pipeline.py::thumbnail",
    when="return",
    highlight="thumb",
    show={"img": "__return__", "raw": "cw.image(rgba)", "gray": "cw.image(rgba[:, :, 0] / 255.0)"},
)
walkthrough.step(
    id="cube",
    at="pipeline.py::main",
    when="return",
    highlight="thumb",
    show={"cube": "cube", "everything": "__return__"},
)
