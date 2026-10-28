"""Reference walkthrough for the demo pipeline.

    uv run codewalk record examples/demo_pipeline/walkthroughs/train.py -o out/demo
    uv run codewalk serve out/demo --open
"""

from codewalk import Walkthrough

walkthrough = Walkthrough(
    title="How the demo pipeline trains a rentals model",
    description="""
    `run.py` reads a daily bike-rental export, cleans it, turns it into a numeric
    matrix, fits a linear model by gradient descent and reports how well it fits.

    This walkthrough stops at each stage and shows the objects as they are at that
    moment: the frame, the design matrix, the weights while they are still moving,
    and the final metrics. Use **Next** (or the right arrow key) to step through it.
    """,
    entry="run.py --epochs 120",
    root="..",
    schema="""
    flowchart LR
      raw[(data/raw.csv)] --> load[Load] --> clean[Clean] --> feats[Features]
      feats --> train[Train] --> eval[Evaluate] --> report[Report]
    """,
)

walkthrough.step(
    id="load",
    title="Read the raw export",
    at="demo/load.py::load_csv",
    when="return",
    highlight="load",
    show={"raw": "__return__", "dtypes": "__return__.dtypes", "shape": "__return__.shape"},
    text="""
    `load_csv` is the only function that knows about the file format. It parses the
    `date` column (the CSV stores it as text) and sorts by date, because the export
    comes back in a random order.

    The frame has shape {{shape}}. Look at the `dtypes` tab: everything numeric was
    read as a number, and `weather` stays a string column, which is dealt with later.
    """,
)

walkthrough.step(
    id="duplicates",
    title="Drop duplicated rows",
    after="demo/clean.py:19",
    highlight="clean",
    show={"removed": "report['duplicates']", "before": "len(raw)", "after": "len(df)", "report": "report"},
    text="""
    The export sometimes repeats rows when it is re-run. `drop_duplicates()` removed
    {{removed}} of them ({{before}} rows before, {{after}} after).

    Every change `clean` makes is counted in `report`, so the run can print what it
    did and a reviewer can tell a dataset change from a code change.
    """,
)

walkthrough.step(
    id="outliers",
    title="Remove counter glitches",
    at="demo/clean.py:23",
    highlight="clean",
    focus="demo/clean.py:21-23",
    show={"outliers": "df[outliers]", "threshold": "MAX_RENTALS", "flag": "outliers"},
    text="""
    Two days report over 10 000 rentals, which is a counter glitch, not a busy day.
    The `outliers` tab shows them: `rentals` is 99 999 and 123 456, the rest of the row
    looks ordinary.

    We are paused **before** line 23 runs, so `df` still contains them. The threshold
    `MAX_RENTALS` is a module constant so that it is easy to find and to question.
    """,
)

walkthrough.step(
    id="missing",
    title="Fill missing sensor readings",
    at="demo/clean.py::clean",
    when="return",
    highlight="clean",
    show={"report": "__return__[1]", "summary": "__return__[0].describe()", "clean": "__return__[0]"},
    text="""
    `clean` returns two things: the frame and the report. Temperature and humidity are
    sensor columns with occasional gaps, filled with each column's median. The
    `report` tab counts every intervention.

    `summary` is `describe()` of the cleaned frame: the maximum of `rentals` is now
    plausible, and no column has fewer values than the others.
    """,
)

walkthrough.step(
    id="features",
    title="Build the design matrix",
    at="demo/features.py::build_features",
    when="return",
    highlight="feats",
    focus="demo/features.py:27-29",
    show={"X": "X", "names": "names", "y": "y", "scaled": "scaled"},
    text="""
    The model only understands numbers, so each day becomes one row of `X`:

    1. a constant `bias` column,
    2. the numeric sensors, standardised to mean 0 and standard deviation 1 so
       that one learning rate suits all of them,
    3. one-hot columns for `cloudy` and `rain` (`clear` is the baseline, so it needs
       no column of its own, which keeps the columns independent),
    4. the `holiday` flag.

    `names` keeps the column order, so the fitted weights can be labelled later.
    """,
)

walkthrough.step(
    id="epoch",
    title="One gradient step",
    after="demo/train.py:25",
    highlight="train",
    hit="all",
    condition="epoch in (0, 1, 10, 119)",
    show={"epoch": "epoch", "loss": "f'{loss:,.0f}'", "w": "self.w", "grad": "grad"},
    plot="plot_loss(self.history)",
    text="""
    Epoch {{epoch}}: the mean squared error is {{loss}}.

    Each pass predicts with the current weights, measures the error, computes the
    gradient of the squared error and takes a step against it. The `w` tab shows the
    weights after this step and `grad` the direction they just moved in; the plot is
    the loss so far on a log scale. The first steps do most of the work.
    """,
)

walkthrough.step(
    id="fitted",
    title="The fitted model",
    at="demo/train.py::LinearModel.fit",
    when="return",
    highlight="train",
    show={"model": "__return__", "weights": "self.w", "loss": "plot_loss(self.history)"},
    text="""
    `fit` returns the model itself so that `LinearModel(names).fit(X, y)` reads as one
    expression. The `model` tab is the object's own HTML representation (its
    `_repr_html_` method): the weight of each named feature.

    Because the numeric columns were standardised, their weights are comparable:
    a one-standard-deviation warmer day adds about as many rentals as the
    temperature weight says, rain costs the `weather=rain` weight.
    """,
)

walkthrough.step(
    id="score",
    title="Score the fit",
    at="demo/evaluate.py::score",
    when="return",
    highlight="eval",
    show={"metrics": "__return__", "rmse": "round(__return__['rmse'])", "residual": "residual"},
    plot="plot_predictions(y, pred)",
    text="""
    `score` compares predictions with the truth: the root mean squared error is
    {{rmse}} rentals per day, and the metrics dict also carries the mean absolute
    error and R squared.

    The plot puts actual rentals on the x axis and predictions on the y axis; a
    perfect model would sit on the dashed line. The `residual` tab is the raw
    difference per day, useful for spotting days the model gets badly wrong.
    """,
)

walkthrough.step(
    id="report",
    title="Report the result",
    at="run.py:36",
    highlight="report",
    code="run.py::main",
    focus="run.py:31-35",
    show={"metrics": "metrics", "report": "report", "model": "model"},
    text="""
    Back in `main`, everything is in hand: the cleaning `report`, the `model` and
    its `metrics`. The highlighted lines print them and, with `--plot`, save the
    predicted-against-actual figure.

    We are paused on the final `return`, so the **console** toggle below shows
    everything the script printed. That is the end of the run.
    """,
)
