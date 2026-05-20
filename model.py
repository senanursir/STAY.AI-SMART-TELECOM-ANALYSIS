import pandas as pd
import numpy as np
import joblib
import warnings
warnings.filterwarnings('ignore')
from sklearn.model_selection import RandomizedSearchCV, StratifiedKFold, train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from imblearn.over_sampling import SMOTENC
from catboost import CatBoostClassifier
from preprocess import preprocess, cols_from_metric_to_binary, binary_list, cols_to_encode

df = pd.read_csv('data/cell2cell.csv', low_memory=False)

labeled_df = df[df['Churn'].notna()].copy()
test_df    = df[df['Churn'].isna()].copy()

print('Etiketli veri:', len(labeled_df), '| Test (Churn=NaN):', len(test_df))

train_df, val_df = train_test_split(labeled_df, test_size=0.222, stratify=labeled_df['Churn'], random_state=42)

y_train = train_df['Churn'].map({'Yes': 1, 'No': 0}).astype(int)
y_val   = val_df['Churn'].map({'Yes': 1, 'No': 0}).astype(int)

X_train_raw = train_df.drop(columns=['Churn'])
X_val_raw   = val_df.drop(columns=['Churn'])
X_test_raw  = test_df.drop(columns=['Churn'], errors='ignore')

X_train, clip_bounds, scaler, metric_cols = preprocess(X_train_raw, fit=True)
X_val  = preprocess(X_val_raw,  clip_bounds=clip_bounds, scaler=scaler, metric_cols=metric_cols, fit=False)
X_test = preprocess(X_test_raw, clip_bounds=clip_bounds, scaler=scaler, metric_cols=metric_cols, fit=False)

for df_ in [X_train, X_val, X_test]:
    if 'Churn' in df_.columns:
        df_.drop(columns=['Churn'], inplace=True)

X_val  = X_val.reindex(columns=X_train.columns, fill_value=0)
X_test = X_test.reindex(columns=X_train.columns, fill_value=0)

cat_feature_names = (
    cols_from_metric_to_binary +
    binary_list +
    [col for col in X_train.columns if any(col.startswith(p + '_') for p in cols_to_encode)]
)
cat_indices = [X_train.columns.get_loc(c) for c in cat_feature_names if c in X_train.columns]

smotenc = SMOTENC(categorical_features=cat_indices, random_state=42, k_neighbors=5)
X_resampled, y_resampled = smotenc.fit_resample(X_train, y_train)

param_grid = {
    'iterations':        [300, 500, 700],
    'learning_rate':     [0.01, 0.05, 0.1],
    'depth':             [4, 6, 8],
    'l2_leaf_reg':       [1, 3, 5, 10],
    'bagging_temperature': [0, 0.5, 1.0],
    'random_strength':   [1, 2, 5],
    'border_count':      [32, 64, 128]
}

catboost = CatBoostClassifier(random_seed=42, verbose=0, eval_metric='AUC')
cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

search = RandomizedSearchCV(
    catboost,
    param_distributions=param_grid,
    n_iter=50,
    scoring='roc_auc',
    cv=cv,
    random_state=42,
    n_jobs=-1,
    verbose=1
)

search.fit(X_resampled, y_resampled)
print('En iyi parametreler:', search.best_params_)
print('En iyi ROC-AUC (CV):', round(search.best_score_, 4))

best_model = search.best_estimator_

val_prob = best_model.predict_proba(X_val)[:, 1]
threshold = 0.3
val_pred = (val_prob >= threshold).astype(int)

print('\nValidation Sonuçları (threshold=0.3):')
print(classification_report(y_val, val_pred))
print('Validation ROC-AUC:', round(roc_auc_score(y_val, val_prob), 4))

import os
os.makedirs('pipeline', exist_ok=True)

pipeline_obj = {
    'model':           best_model,
    'clip_bounds':     clip_bounds,
    'scaler':          scaler,
    'feature_columns': list(X_train.columns),
    'metric_cols':     metric_cols
}

joblib.dump(pipeline_obj, 'pipeline/pipeline.pkl')
print('Pipeline kaydedildi → pipeline/pipeline.pkl')
