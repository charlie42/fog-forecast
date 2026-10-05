"""Are fancier models better than the logistic regression of the site? No.
At a city they did not learn from, they are no better for fog and worse for mist.

Run: pip install xgboost, then python compare_models.py (about 40 minutes on 8 cores)
Boosting, forests and a logistic regression with its strength searched get the same seven inputs.
Two tests: a winter is held out, or a winter of one city is held out and that city is left out of the
fit, as a new city on the site is. Settings are chosen on splits of the fitting mornings only.

Fog skill   winter held out: logistic 23.4%, model chosen on the splits +1.4 (-0.0 to +3.0)
            winter and city: logistic 22.1%, model chosen on the splits -1.5 (-3.6 to +0.5)
Mist skill  winter held out: logistic 28.6%, model chosen on the splits +1.1 (+0.2 to +2.0)
            winter and city: logistic 27.5%, model chosen on the splits -2.4 (-3.7 to -1.1)"""
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'   # one thread per fit, since eight folds are fitted at a time
import warnings

import numpy as np
import xgboost
from joblib import Parallel, delayed
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

import common
from common import MORNING_INPUTS, logit, skill

warnings.filterwarnings('ignore')
LOW = 0.005   # usual rates are kept between 0.5% and 99.5% before the log-odds
SITE = 'logistic (site)'
CHOSEN = 'best by inner score'
UP, DOWN, FREE = 1, -1, 0
DIRECTION = [UP, DOWN, DOWN, DOWN, DOWN, FREE, UP]   # of the chance when an input rises, for the monotone boosting


# Settings to choose from. They are drawn at random, always the same ones, in the order written here.
rng = np.random.default_rng(0)


def between(low, high):
    """A number between `low` and `high`, small ones as likely as large ones."""
    return float(np.exp(rng.uniform(np.log(low), np.log(high))))


def boosting_setting():
    depth = [2, 3, 4, 5, None][rng.integers(5)]
    setting = dict(max_depth=depth, max_iter=int(rng.integers(50, 601)), learning_rate=round(between(.02, .2), 4),
                   min_samples_leaf=int(rng.integers(10, 201)), l2_regularization=round(float(rng.uniform(0, 10)), 2))
    if depth is None:
        setting['max_leaf_nodes'] = int(rng.integers(4, 17))
    return setting


def xgboost_setting():
    return dict(max_depth=int(rng.integers(2, 6)), n_estimators=int(rng.integers(50, 601)),
                learning_rate=round(between(.02, .2), 4), min_child_weight=int(rng.integers(1, 51)),
                reg_lambda=round(float(rng.uniform(0, 10)), 2), subsample=round(float(rng.uniform(.6, 1)), 2),
                colsample_bytree=round(float(rng.uniform(.5, 1)), 2))


def forest_setting():
    return dict(min_samples_leaf=int(between(5, 100)), max_features=int(rng.integers(2, 8)))


BOOSTING = [boosting_setting() for _ in range(30)]
XGBOOST = [xgboost_setting() for _ in range(30)]
FOREST = [forest_setting() for _ in range(8)]
EXTRA_TREES = [forest_setting() for _ in range(8)]
STRENGTH = [dict(C=c) for c in (0.003, 0.01, 0.03, 0.1, 0.3, 1, 10, 100)]

# name: (settings to choose from, the model for one setting)
MODELS = {
    SITE: ([{}], lambda s: common.logistic()),
    'logistic C search': (STRENGTH, lambda s: make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, **s))),
    'hist boosting': (BOOSTING, lambda s: HistGradientBoostingClassifier(early_stopping=False, random_state=0, **s)),
    'hist boosting monotone': (BOOSTING, lambda s: HistGradientBoostingClassifier(
        early_stopping=False, monotonic_cst=DIRECTION, random_state=0, **s)),
    'xgboost': (XGBOOST, lambda s: xgboost.XGBClassifier(n_jobs=1, tree_method='hist', random_state=0, verbosity=0, **s)),
    'random forest': (FOREST, lambda s: RandomForestClassifier(500, n_jobs=1, random_state=0, **s)),
    'extra trees': (EXTRA_TREES, lambda s: ExtraTreesClassifier(500, n_jobs=1, random_state=0, **s)),
}


def load():
    """The mornings of the 14 airports, each with its winter (October to March, named by the year it starts in)."""
    table, _, _ = common.load_europe()
    table['winter'] = np.minimum((table.day - np.timedelta64(182, 'D')).dt.year, 2025)
    return table.reset_index(drop=True)


def usual_rates(table, rows, target):
    """The usual rate of each city, counted on `rows` only."""
    return table.city.map(rows.groupby('city')[target].mean())


def inputs(rows, rate):
    """The seven inputs: the six of the morning and the log-odds of the usual rate."""
    x = rows[MORNING_INPUTS].copy()
    x['usual'] = logit(np.asarray(rate), LOW)
    return x.values


def chances(model, x, y, x_new):
    return model.fit(x, y).predict_proba(x_new)[:, 1]


def inner_splits(fitting, target):
    """Five splits of the fitting mornings by calendar month, each as (x, y, x left out, y left out)."""
    y = fitting[target].values.astype(float)
    splits = []
    for kept, left_out in GroupKFold(5).split(fitting, groups=fitting.fold.values):
        rate = usual_rates(fitting, fitting.iloc[kept], target)
        splits.append((inputs(fitting.iloc[kept], rate.iloc[kept]), y[kept],
                       inputs(fitting.iloc[left_out], rate.iloc[left_out]), y[left_out]))
    return splits


def inner_score(model, setting, splits):
    """Mean squared error of one setting on the mornings left out of the five splits."""
    errors = [(chances(model(setting), x, y, x_out) - y_out) ** 2 for x, y, x_out, y_out in splits]
    return np.concatenate(errors).mean()


def one_fold(table, target, held_out, city):
    """Chances for the mornings held out, from every model fitted without their winter (and without `city`).

    Returns {name: (chances, inner score of the setting chosen)} and the usual rate of those mornings."""
    other_winters = (table.winter != table.winter[held_out].iloc[0]).values
    rate = usual_rates(table, table[other_winters], target)   # a city left out keeps its own usual rate
    rows = other_winters if city is None else other_winters & (table.city != city).values
    fitting = table[rows].reset_index(drop=True)
    x, y = inputs(fitting, rate[rows]), fitting[target].values.astype(float)
    x_out = inputs(table[held_out], rate[held_out])
    splits = inner_splits(fitting, target)
    result = {}
    for name, (settings, model) in MODELS.items():
        scores = [inner_score(model, setting, splits) for setting in settings]
        best = int(np.argmin(scores))
        result[name] = chances(model(settings[best]), x, y, x_out), scores[best]
    return result, rate[held_out].values


def test(table, target, with_city):
    """A chance for every morning from every model, each from a fit without that morning's winter (and city)."""
    winters, cities = sorted(table.winter.unique()), sorted(table.city.unique())
    if with_city:
        folds = [(((table.winter == w) & (table.city == c)).values, c) for w in winters for c in cities]
    else:
        folds = [((table.winter == w).values, None) for w in winters]
    folds = [fold for fold in folds if fold[0].any()]
    results = Parallel(n_jobs=8)(delayed(one_fold)(table, target, held_out, city) for held_out, city in folds)
    p = {name: np.full(len(table), np.nan) for name in [*MODELS, CHOSEN]}
    usual = np.full(len(table), np.nan)
    for (held_out, _), (result, rate) in zip(folds, results):
        usual[held_out] = rate
        for name, (chance, _) in result.items():
            p[name][held_out] = chance
        p[CHOSEN][held_out] = min(result.values(), key=lambda pair: pair[1])[0]   # the model with the lowest inner score
    return p, usual


def difference_range(p, q, usual, y, month, resamples=2000):
    """90% range of the skill of `p` minus the skill of `q` when the months are resampled."""
    months = sorted(set(month))
    rows = {m: np.where(month == m)[0] for m in months}
    draw = np.random.default_rng(0)
    differences = []
    for _ in range(resamples):
        k = np.concatenate([rows[m] for m in draw.choice(months, len(months))])
        differences.append(skill(p[k], usual[k], y[k]) - skill(q[k], usual[k], y[k]))
    return np.percentile(differences, 5), np.percentile(differences, 95)


if __name__ == '__main__':
    table = load()
    for with_city in (False, True):
        for target in ('fog', 'mist'):
            p, usual = test(table, target, with_city)
            y = table[target].values.astype(float)
            print(f'\n=== {target.upper()}, held out: {"winter+city" if with_city else "winter"} ===', flush=True)
            for name, chance in p.items():
                line = f'{name:24s} skill {skill(chance, usual, y):5.1%}'
                if name != SITE:
                    low, high = difference_range(chance, p[SITE], usual, y, table.fold.values)
                    line += f'  vs logistic {skill(chance, usual, y) - skill(p[SITE], usual, y):+.1%} ({low:+.1%} to {high:+.1%})'
                print(line, flush=True)
