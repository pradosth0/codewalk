"""Reference walkthrough for the demo pipeline, in three levels of detail.

    uv run codewalk record examples/demo_pipeline/walkthroughs/train.py -o out/demo
    uv run codewalk serve out/demo --open

Level 1 is one key step per stage (what a project manager needs), level 2 the normal
walk, level 3 line by line inside one training epoch. A key step sits where a stage's
result is visible (its return) and summarises the deeper steps recorded before it.
"""

from codewalk import Walkthrough

walkthrough = Walkthrough(
    title="How the demo pipeline trains a rentals model",
    description="""
    `run.py` reads a daily bike-rental export, cleans it, turns it into a numeric
    matrix, fits a linear model by gradient descent and reports how well it fits.

    **Next** walks the six key steps, one per stage, each showing that stage's
    result. Press **Down** (or ↓) on a key step to see how it was produced, step by
    step, and **Up** (↑) to come back to the summary. "Walk at 3" visits everything.
    """,
    entry="run.py --epochs 120",
    root="..",
    levels=["Overview", "Walkthrough", "Line by line"],
    schema="""
    flowchart LR
      raw[(data/raw.csv)] --> load[Load] --> clean[Clean] --> feats[Features]
      feats --> train[Train] --> eval[Evaluate] --> report[Report]
    """,
)

# ----------------------------------------------------------------------------- load
walkthrough.step(
    id="load",
    level=1,
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

# ----------------------------------------------------------------------------- clean
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
    id="fill",
    title="Fill a sensor column",
    after="demo/clean.py:28",
    hit="all",
    highlight="clean",
    focus="demo/clean.py:25-28",
    show={"column": "column", "gaps": "int(missing.sum())", "median": "round(df[column].median(), 1)", "filled": "df[column].describe()"},
    text="""
    Column `{{column}}`: {{gaps}} empty readings were replaced with the column's
    median, {{median}}.

    The median is robust to the odd extreme reading, and filling rather than dropping
    keeps the day's other columns. `filled` is `describe()` of the column after the
    fill: the count now matches the number of rows.
    """,
)

walkthrough.step(
    id="clean",
    level=1,
    title="Clean the frame",
    at="demo/clean.py::clean",
    when="return",
    highlight="clean",
    show={"report": "__return__[1]", "clean": "__return__[0]", "summary": "__return__[0].describe()"},
    text="""
    `clean` returns the cleaned frame and a report of what it changed: duplicated
    rows dropped, counter glitches removed, empty sensor readings filled with the
    column median. 183 rows went in, 178 come out, and the `report` tab counts every
    intervention.

    `summary` is `describe()` of the result: the maximum of `rentals` is now
    plausible, and no column has fewer values than the others. Press **Down** to see
    each of the three interventions as it happened.
    """,
)

# ----------------------------------------------------------------------------- features
walkthrough.step(
    id="features",
    level=1,
    title="Build the design matrix",
    at="demo/features.py::build_features",
    when="return",
    highlight="feats",
    focus="demo/features.py:26-28",
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

# ----------------------------------------------------------------------------- train
# The loop step is declared first because its first hit (epoch 0) comes before the
# line-by-line steps (epoch 10); those three are summarised by the hit at epoch 10.
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
    id="error",
    level=3,
    title="Predict and measure the error",
    after="demo/train.py:21",
    condition="epoch == 10",
    highlight="train",
    focus="demo/train.py:20-21",
    show={"error": "error", "pred": "pred", "y": "y", "epoch": "epoch"},
    text="""
    Inside epoch {{epoch}}. `pred` is the model's guess for every day with the
    current weights, `error` the signed difference to the truth `y`: positive where
    the model predicts too many rentals, negative where too few.
    """,
)

walkthrough.step(
    id="loss",
    level=3,
    title="The loss is the mean squared error",
    after="demo/train.py:22",
    condition="epoch == 10",
    highlight="train",
    focus="demo/train.py:22-23",
    show={"loss": "f'{loss:,.0f}'", "error": "error"},
    text="""
    Squaring the errors makes big misses count much more than small ones and removes
    the sign; the mean turns it into a single number, {{loss}}, that gradient descent
    will push down. It is appended to `history` so the curve can be drawn later.
    """,
)

walkthrough.step(
    id="grad",
    level=3,
    title="The gradient points uphill",
    after="demo/train.py:24",
    condition="epoch == 10",
    highlight="train",
    focus="demo/train.py:24-25",
    show={"grad": "grad", "names": "self.names", "w": "self.w"},
    text="""
    `grad` is the derivative of the loss with respect to each weight: `X.T @ error`
    sums, for every column, the error weighted by that feature. A positive entry means
    increasing that weight would increase the loss, so the next line moves the weight
    the other way, scaled by the learning rate.
    """,
)

walkthrough.step(
    id="fitted",
    level=1,
    title="Fit the model",
    at="demo/train.py::LinearModel.fit",
    when="return",
    highlight="train",
    show={"model": "__return__", "weights": "self.w", "loss": "plot_loss(self.history)"},
    text="""
    Training is 120 passes of gradient descent over the whole matrix. `fit` returns
    the model itself so that `LinearModel(names).fit(X, y)` reads as one expression.
    The `model` tab is the object's own HTML representation (its `_repr_html_`
    method): the weight of each named feature.

    Because the numeric columns were standardised, their weights are comparable: a
    one-standard-deviation warmer day adds about as many rentals as the temperature
    weight says, rain costs the `weather=rain` weight. **Down** shows four of the
    passes; down again from one of them, the lines inside a pass.
    """,
)

# ----------------------------------------------------------------------------- evaluate
walkthrough.step(
    id="residual",
    title="Residuals",
    after="demo/evaluate.py:14",
    highlight="eval",
    show={"residual": "residual", "pred": "pred"},
    text="""
    `residual` is truth minus prediction for every day, the raw material of every
    metric below. Its mean is close to zero (the bias weight absorbs any constant
    offset); its spread is what the metrics measure.
    """,
)

walkthrough.step(
    id="rmse",
    title="Root mean squared error",
    after="demo/evaluate.py:16",
    highlight="eval",
    focus="demo/evaluate.py:15-16",
    show={"rmse": "round(rmse)", "mae": "round(mae)", "residual": "residual"},
    text="""
    `rmse` ({{rmse}}) is the square root of the training loss, so it is in rentals per
    day again. `mae` ({{mae}}) is the plain average miss; it is smaller because the
    squared error weights the worst days more heavily.
    """,
)

walkthrough.step(
    id="r2",
    title="R squared",
    after="demo/evaluate.py:17",
    highlight="eval",
    focus="demo/evaluate.py:17",
    show={"r2": "round(r2, 3)", "variance": "float(np.sum((y - y.mean()) ** 2))", "unexplained": "float(np.sum(residual**2))"},
    text="""
    `r2` = 1 minus unexplained variance over total variance: {{r2}} means the model
    accounts for about 90 % of the day-to-day variation in rentals. A model that
    always predicted the mean would score 0.
    """,
)

walkthrough.step(
    id="score",
    level=1,
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

# ----------------------------------------------------------------------------- report
walkthrough.step(
    id="report",
    level=1,
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
