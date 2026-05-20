import pandas as pd
import numpy as np
import joblib
import os
import time
import warnings
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split, StratifiedKFold, RandomizedSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (classification_report, roc_auc_score, balanced_accuracy_score,
                              f1_score, precision_score, recall_score)
from imblearn.over_sampling import SMOTENC
from catboost import CatBoostClassifier
import shap

RANDOM_STATE = 42
DATA_PATH    = "data/cell2cell.csv"
OUTPUT_PATH  = "pipeline/pipeline.pkl"

COLS_TO_DROP = ['CustomerID', 'ServiceArea', 'Homeownership',
                'NotNewCellphoneUser', 'CallForwardingCalls']

COLS_TO_CLIP = [
    'ActiveSubs', 'AgeHH1', 'AgeHH2', 'BlockedCalls', 'CallWaitingCalls',
    'CurrentEquipmentDays', 'CustomerCareCalls', 'DroppedBlockedCalls',
    'DroppedCalls', 'HandsetModels', 'Handsets', 'InboundCalls',
    'PercChangeMinutes', 'PercChangeRevenues', 'ThreewayCalls',
    'TotalRecurringCharge', 'UniqueSubs'
]

COLS_TO_LOG = [
    'MonthlyMinutes', 'MonthlyRevenue', 'OffPeakCallsInOut',
    'OutboundCalls', 'PeakCallsInOut', 'ReceivedCalls', 'UnansweredCalls'
]

COLS_METRIC_TO_BINARY = [
    'AdjustmentsToCreditRating', 'DirectorAssistedCalls', 'OverageMinutes',
    'ReferralsMadeBySubscriber', 'RetentionCalls', 'RetentionOffersAccepted', 'RoamingCalls'
]

BINARY_COLS = [
    'BuysViaMailOrder', 'ChildrenInHH', 'HandsetRefurbished', 'HandsetWebCapable',
    'HasCreditCard', 'MadeCallToRetentionTeam', 'MaritalStatus', 'NewCellphoneUser',
    'NonUSTravel', 'OptOutMailings', 'OwnsComputer', 'OwnsMotorcycle',
    'RespondsToMailOffers', 'RVOwner', 'TruckOwner'
]

COLS_TO_ENCODE = ['PrizmCode', 'Occupation', 'IncomeGroup', 'CreditRating']

METRIC_COLS = [
    'ActiveSubs_clipped', 'AgeHH1_clipped', 'AgeHH2_clipped', 'BlockedCalls_clipped',
    'CallWaitingCalls_clipped', 'CurrentEquipmentDays_clipped', 'CustomerCareCalls_clipped',
    'DroppedBlockedCalls_clipped', 'DroppedCalls_clipped', 'HandsetModels_clipped',
    'Handsets_clipped', 'InboundCalls_clipped', 'PercChangeMinutes_clipped',
    'PercChangeRevenues_clipped', 'ThreewayCalls_clipped', 'TotalRecurringCharge_clipped',
    'UniqueSubs_clipped', 'MonthlyMinutes_log', 'MonthlyRevenue_log',
    'OffPeakCallsInOut_log', 'OutboundCalls_log', 'PeakCallsInOut_log',
    'ReceivedCalls_log', 'UnansweredCalls_log', 'MonthsInService', 'HandsetPrice'
]

YES_NO  = {'Yes': 1, 'No': 0}
CREDIT  = {'1-Highest': 6, '2-High': 5, '3-Good': 4, '4-Medium': 3,
           '5-Low': 2, '6-VeryLow': 1, '7-Lowest': 0}


def basic_clean(df):
    df = df.drop(columns=COLS_TO_DROP, errors='ignore')
    df = df.replace(['Unknown', '', ' ', 'unknown'], np.nan)
    return df


def fit_imputer(df):
    medians = {}
    for col in df.select_dtypes(include=[np.number]).columns:
        medians[col] = df[col].median()
    return medians


def apply_imputer(df, medians):
    for col, val in medians.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(val)
    return df


def fit_clip_bounds(df):
    bounds = {}
    for col in COLS_TO_CLIP:
        if col not in df.columns:
            continue
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3 - Q1
        bounds[col] = (Q1 - 1.5 * IQR, Q3 + 1.5 * IQR)
    return bounds


def apply_features(df, clip_bounds, hp_median=0):
    for col in COLS_TO_CLIP:
        if col not in df.columns:
            continue
        lo, hi = clip_bounds[col]
        df[f"{col}_clipped"] = df[col].clip(lower=lo, upper=hi)

    for col in COLS_TO_LOG:
        if col not in df.columns:
            continue
        df[f"{col}_log"] = np.log1p(df[col].clip(lower=0))

    df['CreditRating'] = df['CreditRating'].map(CREDIT).fillna(3).astype(int)
    df['HandsetPrice'] = pd.to_numeric(df['HandsetPrice'], errors='coerce').fillna(hp_median).astype(int)

    for col in COLS_METRIC_TO_BINARY:
        if col in df.columns:
            df[col] = (pd.to_numeric(df[col], errors='coerce').fillna(0) > 0).astype(int)

    for col in BINARY_COLS:
        if col in df.columns:
            df[col] = df[col].map(YES_NO).fillna(0).astype(int)

    df = pd.get_dummies(df, columns=COLS_TO_ENCODE, drop_first=False)
    df[df.select_dtypes(include='bool').columns] = df.select_dtypes(include='bool').astype(int)
    return df


t0 = time.time()
print("=" * 60)
print("1. VERİ YÜKLENİYOR")
print("=" * 60)

df_raw = pd.read_csv(DATA_PATH, low_memory=False)
df_labeled = df_raw[df_raw['Churn'].notna()].copy()
df_clean = basic_clean(df_labeled)
print(f"Etiketli veri: {len(df_clean)} satır")

print("\n" + "=" * 60)
print("2. TRAIN / VAL / TEST")
print("=" * 60)

y_all     = df_clean['Churn'].map({'Yes': 1, 'No': 0}).astype(int)
X_raw_all = df_clean.drop(columns=['Churn'])

X_tv_raw, X_test_raw, y_tv, y_test = train_test_split(
    X_raw_all, y_all, test_size=0.15, stratify=y_all, random_state=RANDOM_STATE
)
X_train_raw, X_val_raw, y_train, y_val = train_test_split(
    X_tv_raw, y_tv, test_size=0.15, stratify=y_tv, random_state=RANDOM_STATE
)
print(f"Train: {len(X_train_raw)} | Val: {len(X_val_raw)} | Test: {len(X_test_raw)}")

print("\n" + "=" * 60)
print("3. ÖN İŞLEME")
print("=" * 60)

train_numeric = X_train_raw.copy()
for col in train_numeric.select_dtypes(exclude=[np.number]).columns:
    train_numeric[col] = pd.to_numeric(train_numeric[col], errors='coerce')

medians     = fit_imputer(train_numeric)
hp_median   = medians.get('HandsetPrice', 0)
clip_bounds = fit_clip_bounds(apply_imputer(train_numeric.copy(), medians))


def transform(df_in, fit_cols=None, sc=None):
    df = df_in.copy()
    df = apply_imputer(df, medians)
    df = apply_features(df, clip_bounds, hp_median)
    if fit_cols is not None:
        df = df.reindex(columns=fit_cols, fill_value=0)
    if sc is not None:
        present = [c for c in METRIC_COLS if c in df.columns]
        df[present] = sc.transform(df[present])
    return df


X_train_feat = transform(X_train_raw)
feature_cols = [c for c in X_train_feat.columns if c != 'Churn']
X_train_feat = X_train_feat.reindex(columns=feature_cols, fill_value=0)

present_metric = [c for c in METRIC_COLS if c in X_train_feat.columns]
scaler = StandardScaler()
X_train_feat[present_metric] = scaler.fit_transform(X_train_feat[present_metric])

X_val_feat  = transform(X_val_raw,  feature_cols, scaler)
X_test_feat = transform(X_test_raw, feature_cols, scaler)
print(f"Feature sayısı: {len(feature_cols)}")

print("\n" + "=" * 60)
print("4. FEATURE SELECTION")
print("=" * 60)

prelim = CatBoostClassifier(iterations=300, depth=6, learning_rate=0.05,
                             random_seed=RANDOM_STATE, verbose=0,
                             eval_metric='AUC', auto_class_weights='Balanced')
prelim.fit(X_train_feat, y_train)
imp = pd.Series(prelim.get_feature_importance(), index=feature_cols).sort_values(ascending=False)

selected_features = imp[imp > 0.1].index.tolist()
if len(selected_features) < 30:
    selected_features = imp.head(30).index.tolist()

print(f"Toplam: {len(feature_cols)} → Seçilen: {len(selected_features)}")
print(f"Top 10:")
for i, (name, val) in enumerate(imp.head(10).items(), 1):
    print(f"  {i:2d}. {name:35s} {val:.3f}")

X_train_feat = X_train_feat[selected_features]
X_val_feat   = X_val_feat[selected_features]
X_test_feat  = X_test_feat[selected_features]
present_metric_sel = [c for c in present_metric if c in selected_features]

print("\n" + "=" * 60)
print("5. SMOTENC — KISMI DENGELEME (1:0.7)")
print("=" * 60)

cat_names = (
    COLS_METRIC_TO_BINARY + BINARY_COLS +
    [c for c in selected_features if any(c.startswith(p + '_') for p in COLS_TO_ENCODE)]
)
cat_indices = [selected_features.index(c) for c in cat_names if c in selected_features]

n_majority = (y_train == 0).sum()
target_minority = int(n_majority * 0.7)

smote = SMOTENC(categorical_features=cat_indices, random_state=RANDOM_STATE,
                k_neighbors=5, sampling_strategy={1: target_minority})
X_train_res, y_train_res = smote.fit_resample(X_train_feat, y_train)
print(f"Sonrası: {dict(pd.Series(y_train_res).value_counts())}")

print("\n" + "=" * 60)
print("6. MODEL EĞİTİMİ — CLASS WEIGHT + GENİŞ SEARCH")
print("=" * 60)

param_grid = {
    'iterations':          [500, 800, 1000],
    'learning_rate':       [0.03, 0.05, 0.08],
    'depth':               [5, 6, 7, 8],
    'l2_leaf_reg':         [1, 3, 5, 10],
    'bagging_temperature': [0, 0.5, 1.0],
    'random_strength':     [1, 3, 5],
    'border_count':        [64, 128],
}

cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=RANDOM_STATE)
base = CatBoostClassifier(
    random_seed=RANDOM_STATE, verbose=0, eval_metric='AUC',
    auto_class_weights='Balanced', thread_count=-1
)

search = RandomizedSearchCV(
    base, param_grid, n_iter=30, scoring='roc_auc', cv=cv,
    random_state=RANDOM_STATE, n_jobs=-1, verbose=1
)
search.fit(X_train_res, y_train_res)
print(f"\nEn iyi: {search.best_params_}")
print(f"CV ROC-AUC: {search.best_score_:.4f}")

print("\n" + "=" * 60)
print("7. SMART THRESHOLD — VAL SETİ")
print("=" * 60)

best_model = search.best_estimator_
val_proba  = best_model.predict_proba(X_val_feat)[:, 1]

results = []
for t in np.arange(0.20, 0.81, 0.01):
    preds = (val_proba >= t).astype(int)
    p = precision_score(y_val, preds, zero_division=0)
    r = recall_score(y_val, preds, zero_division=0)
    f = f1_score(y_val, preds, zero_division=0)
    bacc = balanced_accuracy_score(y_val, preds)
    j = r + p - 1 if (p + r) > 0 else 0
    results.append((t, p, r, f, bacc, j))

results = pd.DataFrame(results, columns=['threshold', 'precision', 'recall', 'f1', 'balanced_acc', 'youden'])
best_thr_youden = float(results.loc[results['youden'].idxmax(), 'threshold'])
best_thr_bacc   = float(results.loc[results['balanced_acc'].idxmax(), 'threshold'])
best_thr = round((best_thr_youden + best_thr_bacc) / 2, 2)

print(f"Seçilen threshold: {best_thr}")

print("\n" + "=" * 60)
print("8. TEST SONUÇLARI")
print("=" * 60)

test_proba = best_model.predict_proba(X_test_feat)[:, 1]
test_pred  = (test_proba >= best_thr).astype(int)

print(f"Test ROC-AUC      : {roc_auc_score(y_test, test_proba):.4f}")
print(f"Test Balanced Acc : {balanced_accuracy_score(y_test, test_pred):.4f}")
print(f"Test F1 (Churn)   : {f1_score(y_test, test_pred):.4f}")
print(f"Test Precision    : {precision_score(y_test, test_pred):.4f}")
print(f"Test Recall       : {recall_score(y_test, test_pred):.4f}")
print(f"\nClassification Report:")
print(classification_report(y_test, test_pred))

print("\n" + "=" * 60)
print("9. SHAP EXPLAINER OLUŞTURULUYOR")
print("=" * 60)

shap_explainer = shap.TreeExplainer(best_model)
print("✅ SHAP TreeExplainer hazır")

print("\n" + "=" * 60)
print("10. PIPELINE KAYDEDİLİYOR (model + SHAP birlikte)")
print("=" * 60)

os.makedirs("pipeline", exist_ok=True)

joblib.dump({
    'model':           best_model,
    'shap_explainer':  shap_explainer,
    'clip_bounds':     clip_bounds,
    'scaler':          scaler,
    'medians':         medians,
    'feature_columns': selected_features,
    'metric_cols':     present_metric_sel,
    'threshold':       best_thr,
    'all_features':    feature_cols,
}, OUTPUT_PATH)

size_mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
print(f"✅ Pipeline → {OUTPUT_PATH} ({size_mb:.2f} MB)")
print(f"⏱  Toplam süre: {(time.time()-t0)/60:.1f} dakika")
