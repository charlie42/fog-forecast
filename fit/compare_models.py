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
RATE_FLOOR = 0.005   # usual rates are clipped to 0.5%..99.5% before the log-odds
BASELINE = 'logistic (site)'
SELECTED = 'best by inner score'
MONOTONIC = [1, -1, -1, -1, -1, 0, 1]   # per input: the chance may only rise (1), only fall (-1), or either (0)


# Parameter grids. They are sampled at random with a fixed seed, in the order written here.
rng = np.random.default_rng(0)


def sample_log_uniform(low, high):
    """Sample a number between `low` and `high`, uniform on the log scale."""
    return float(np.exp(rng.uniform(np.log(low), np.log(high))))


def sample_boosting_params():
    max_depth = [2, 3, 4, 5, None][rng.integers(5)]
    params = dict(max_depth=max_depth, max_iter=int(rng.integers(50, 601)),
                  learning_rate=round(sample_log_uniform(.02, .2), 4), min_samples_leaf=int(rng.integers(10, 201)),
                  l2_regularization=round(float(rng.uniform(0, 10)), 2))
    if max_depth is None:
        params['max_leaf_nodes'] = int(rng.integers(4, 17))
    return params


def sample_xgboost_params():
    return dict(max_depth=int(rng.integers(2, 6)), n_estimators=int(rng.integers(50, 601)),
                learning_rate=round(sample_log_uniform(.02, .2), 4), min_child_weight=int(rng.integers(1, 51)),
                reg_lambda=round(float(rng.uniform(0, 10)), 2), subsample=round(float(rng.uniform(.6, 1)), 2),
                colsample_bytree=round(float(rng.uniform(.5, 1)), 2))


def sample_forest_params():
    return dict(min_samples_leaf=int(sample_log_uniform(5, 100)), max_features=int(rng.integers(2, 8)))


BOOSTING_GRID = [sample_boosting_params() for _ in range(30)]
XGBOOST_GRID = [sample_xgboost_params() for _ in range(30)]
FOREST_GRID = [sample_forest_params() for _ in range(8)]
EXTRA_TREES_GRID = [sample_forest_params() for _ in range(8)]
LOGISTIC_GRID = [dict(C=c) for c in (0.003, 0.01, 0.03, 0.1, 0.3, 1, 10, 100)]

# name: (parameter grid, function that builds the model from one set of parameters)
MODELS = {
    BASELINE: ([{}], lambda params: common.logistic()),
    'logistic C search': (LOGISTIC_GRID, lambda params: make_pipeline(
        StandardScaler(), LogisticRegression(max_iter=2000, **params))),
    'hist boosting': (BOOSTING_GRID, lambda params: HistGradientBoostingClassifier(
        early_stopping=False, random_state=0, **params)),
    'hist boosting monotone': (BOOSTING_GRID, lambda params: HistGradientBoostingClassifier(
        early_stopping=False, monotonic_cst=MONOTONIC, random_state=0, **params)),
    'xgboost': (XGBOOST_GRID, lambda params: xgboost.XGBClassifier(
        n_jobs=1, tree_method='hist', random_state=0, verbosity=0, **params)),
    'random forest': (FOREST_GRID, lambda params: RandomForestClassifier(500, n_jobs=1, random_state=0, **params)),
    'extra trees': (EXTRA_TREES_GRID, lambda params: ExtraTreesClassifier(500, n_jobs=1, random_state=0, **params)),
}


def load_mornings():
    """Load the mornings of the 14 airports and label each with its winter (October to March, by starting year)."""
    table, _, _ = common.load_europe()
    table['winter'] = np.minimum((table.day - np.timedelta64(182, 'D')).dt.year, 2025)
    return table.reset_index(drop=True)


def compute_usual_rates(table, rows, target):
    """Compute the usual rate of each city from `rows` only, and return it for every row of `table`."""
    return table.city.map(rows.groupby('city')[target].mean())


def build_features(rows, usual_rate):
    """Build the feature matrix: the six morning inputs and the log-odds of the usual rate."""
    X = rows[MORNING_INPUTS].copy()
    X['usual'] = logit(np.asarray(usual_rate), RATE_FLOOR)
    return X.values


def fit_predict(model, X_train, y_train, X_test):
    """Fit the model and return its predicted probabilities for `X_test`."""
    return model.fit(X_train, y_train).predict_proba(X_test)[:, 1]


def make_inner_splits(train, target):
    """Split the training mornings five ways by calendar month. Returns (X_train, y_train, X_val, y_val) tuples."""
    y = train[target].values.astype(float)
    splits = []
    for train_idx, val_idx in GroupKFold(5).split(train, groups=train.fold.values):
        usual_rate = compute_usual_rates(train, train.iloc[train_idx], target)
        splits.append((build_features(train.iloc[train_idx], usual_rate.iloc[train_idx]), y[train_idx],
                       build_features(train.iloc[val_idx], usual_rate.iloc[val_idx]), y[val_idx]))
    return splits


def score_params(make_model, params, splits):
    """Return the mean squared error of one set of parameters over the validation parts of the splits."""
    errors = [(fit_predict(make_model(params), X_train, y_train, X_val) - y_val) ** 2
              for X_train, y_train, X_val, y_val in splits]
    return np.concatenate(errors).mean()


def predict_fold(table, target, test_mask, excluded_city):
    """Predict the test mornings with every model, trained without their winter (and without `excluded_city`).

    Returns {name: (predictions, inner score of the selected parameters)} and the usual rate of the test mornings."""
    test_winter = table.winter[test_mask].iloc[0]
    other_winters = (table.winter != test_winter).values
    usual_rate = compute_usual_rates(table, table[other_winters], target)   # an excluded city keeps its own usual rate
    train_mask = other_winters if excluded_city is None else other_winters & (table.city != excluded_city).values
    train = table[train_mask].reset_index(drop=True)
    X_train, y_train = build_features(train, usual_rate[train_mask]), train[target].values.astype(float)
    X_test = build_features(table[test_mask], usual_rate[test_mask])
    splits = make_inner_splits(train, target)
    results = {}
    for name, (grid, make_model) in MODELS.items():
        scores = [score_params(make_model, params, splits) for params in grid]
        best = int(np.argmin(scores))
        results[name] = fit_predict(make_model(grid[best]), X_train, y_train, X_test), scores[best]
    return results, usual_rate[test_mask].values


def predict_held_out(table, target, exclude_city):
    """Predict every morning with every model, each time trained without that morning's winter (and city)."""
    winters, cities = sorted(table.winter.unique()), sorted(table.city.unique())
    if exclude_city:
        folds = [(((table.winter == w) & (table.city == c)).values, c) for w in winters for c in cities]
    else:
        folds = [((table.winter == w).values, None) for w in winters]
    folds = [fold for fold in folds if fold[0].any()]
    fold_results = Parallel(n_jobs=8)(
        delayed(predict_fold)(table, target, test_mask, city) for test_mask, city in folds)
    predictions = {name: np.full(len(table), np.nan) for name in [*MODELS, SELECTED]}
    usual_rate = np.full(len(table), np.nan)
    for (test_mask, _), (results, fold_usual_rate) in zip(folds, fold_results):
        usual_rate[test_mask] = fold_usual_rate
        for name, (fold_predictions, _) in results.items():
            predictions[name][test_mask] = fold_predictions
        # the model with the lowest inner score in this fold
        predictions[SELECTED][test_mask] = min(results.values(), key=lambda result: result[1])[0]
    return predictions, usual_rate


def bootstrap_skill_difference(p, q, usual_rate, y, month, n_resamples=2000):
    """Return the 90% range of skill(p) - skill(q) when the calendar months are resampled."""
    months = sorted(set(month))
    rows_of = {m: np.where(month == m)[0] for m in months}
    bootstrap_rng = np.random.default_rng(0)
    differences = []
    for _ in range(n_resamples):
        idx = np.concatenate([rows_of[m] for m in bootstrap_rng.choice(months, len(months))])
        differences.append(skill(p[idx], usual_rate[idx], y[idx]) - skill(q[idx], usual_rate[idx], y[idx]))
    return np.percentile(differences, 5), np.percentile(differences, 95)


def main():
    table = load_mornings()
    for exclude_city in (False, True):
        for target in ('fog', 'mist'):
            predictions, usual_rate = predict_held_out(table, target, exclude_city)
            y = table[target].values.astype(float)
            baseline_skill = skill(predictions[BASELINE], usual_rate, y)
            print(f'\n=== {target.upper()}, held out: {"winter+city" if exclude_city else "winter"} ===', flush=True)
            for name, p in predictions.items():
                line = f'{name:24s} skill {skill(p, usual_rate, y):5.1%}'
                if name != BASELINE:
                    low, high = bootstrap_skill_difference(p, predictions[BASELINE], usual_rate, y, table.fold.values)
                    line += f'  vs logistic {skill(p, usual_rate, y) - baseline_skill:+.1%} ({low:+.1%} to {high:+.1%})'
                print(line, flush=True)


if __name__ == '__main__':
    main()
