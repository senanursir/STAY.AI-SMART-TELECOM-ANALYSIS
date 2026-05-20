import os
import pandas as pd
import numpy as np
import joblib

DATASET_PATH  = "data/c2c_holdout.csv"
PIPELINE_PATH = "pipeline/pipeline.pkl"

churn_model     = None
scaler          = None
clip_bounds     = {}
medians         = {}
feature_columns = []
all_features    = []
metric_cols     = []
threshold       = 0.5
shap_explainer  = None
RAW_CUSTOMERS   = {}

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
COLS_TO_DROP   = ['ServiceArea', 'Homeownership', 'NotNewCellphoneUser', 'CallForwardingCalls']

YES_NO = {'Yes': 1, 'No': 0}
CREDIT = {'1-Highest': 6, '2-High': 5, '3-Good': 4, '4-Medium': 3,
          '5-Low': 2, '6-VeryLow': 1, '7-Lowest': 0}

FEATURE_LABELS = {
    'MonthsInService': 'Hizmet Süresi (ay)',
    'CurrentEquipmentDays': 'Mevcut Cihaz Yaşı (gün)',
    'CurrentEquipmentDays_clipped': 'Mevcut Cihaz Yaşı',
    'PercChangeMinutes': 'Dakika Kullanım Değişimi',
    'PercChangeMinutes_clipped': 'Dakika Kullanım Değişimi',
    'PercChangeRevenues': 'Gelir Değişimi',
    'PercChangeRevenues_clipped': 'Gelir Değişimi',
    'MonthlyRevenue': 'Aylık Gelir',
    'MonthlyRevenue_log': 'Aylık Gelir',
    'MonthlyMinutes': 'Aylık Dakika',
    'MonthlyMinutes_log': 'Aylık Dakika',
    'TotalRecurringCharge': 'Toplam Aylık Ücret',
    'TotalRecurringCharge_clipped': 'Toplam Aylık Ücret',
    'CustomerCareCalls': 'Müşteri Hizmetleri Çağrısı',
    'CustomerCareCalls_clipped': 'Müşteri Hizmetleri Çağrısı',
    'DroppedCalls': 'Düşen Çağrı Sayısı',
    'DroppedCalls_clipped': 'Düşen Çağrı Sayısı',
    'BlockedCalls': 'Engellenen Çağrı',
    'BlockedCalls_clipped': 'Engellenen Çağrı',
    'UnansweredCalls': 'Cevapsız Çağrı',
    'UnansweredCalls_log': 'Cevapsız Çağrı',
    'InboundCalls': 'Gelen Çağrı',
    'InboundCalls_clipped': 'Gelen Çağrı',
    'OutboundCalls': 'Giden Çağrı',
    'OutboundCalls_log': 'Giden Çağrı',
    'PeakCallsInOut': 'Yoğun Saat Çağrıları',
    'PeakCallsInOut_log': 'Yoğun Saat Çağrıları',
    'OffPeakCallsInOut': 'Yoğun Olmayan Saat Çağrıları',
    'OffPeakCallsInOut_log': 'Yoğun Olmayan Saat Çağrıları',
    'ReceivedCalls': 'Alınan Çağrı',
    'ReceivedCalls_log': 'Alınan Çağrı',
    'OverageMinutes': 'Aşım Dakikası',
    'RetentionCalls': 'Retention Çağrısı',
    'RetentionOffersAccepted': 'Kabul Edilen Teklif',
    'AdjustmentsToCreditRating': 'Kredi Notu Düzenlemesi',
    'CreditRating': 'Kredi Notu',
    'HandsetPrice': 'Cihaz Fiyatı',
    'HandsetModels': 'Cihaz Model Sayısı',
    'HandsetModels_clipped': 'Cihaz Model Sayısı',
    'Handsets': 'Cihaz Sayısı',
    'Handsets_clipped': 'Cihaz Sayısı',
    'HandsetRefurbished': 'Yenilenmiş Cihaz',
    'HandsetWebCapable': 'Web Destekli Cihaz',
    'AgeHH1': 'Yaş (Birincil)',
    'AgeHH1_clipped': 'Yaş',
    'AgeHH2': 'Yaş (İkincil)',
    'AgeHH2_clipped': 'Yaş (İkincil)',
    'ActiveSubs': 'Aktif Abonelik',
    'ActiveSubs_clipped': 'Aktif Abonelik',
    'UniqueSubs': 'Benzersiz Abonelik',
    'UniqueSubs_clipped': 'Benzersiz Abonelik',
    'NewCellphoneUser': 'Yeni Cep Telefonu Kullanıcısı',
    'MadeCallToRetentionTeam': 'Retention Ekibine Çağrı',
    'ChildrenInHH': 'Evde Çocuk Var',
    'MaritalStatus': 'Medeni Durum',
    'OwnsComputer': 'Bilgisayar Sahipliği',
    'OwnsMotorcycle': 'Motosiklet Sahipliği',
    'HasCreditCard': 'Kredi Kartı',
    'RespondsToMailOffers': 'Posta Tekliflerine Yanıt',
    'BuysViaMailOrder': 'Posta ile Alışveriş',
    'NonUSTravel': 'Yurt Dışı Seyahat',
    'RoamingCalls': 'Roaming Çağrısı',
    'ThreewayCalls': 'Üçlü Görüşme',
    'ThreewayCalls_clipped': 'Üçlü Görüşme',
    'CallWaitingCalls': 'Çağrı Bekletme',
    'CallWaitingCalls_clipped': 'Çağrı Bekletme',
    'DroppedBlockedCalls': 'Düşen/Engellenen Çağrı',
    'DroppedBlockedCalls_clipped': 'Düşen/Engellenen Çağrı',
    'DirectorAssistedCalls': 'Operatör Destekli Çağrı',
    'ReferralsMadeBySubscriber': 'Yapılan Referans',
    'OptOutMailings': 'Posta Almak İstemiyor',
    'RVOwner': 'Karavan Sahibi',
    'TruckOwner': 'Kamyonet Sahibi',
}


def setup_pipeline():
    global churn_model, scaler, clip_bounds, medians, feature_columns, all_features
    global metric_cols, threshold, shap_explainer, RAW_CUSTOMERS

    if not os.path.exists(PIPELINE_PATH):
        raise FileNotFoundError(f"Pipeline bulunamadı: {PIPELINE_PATH}")
    if not os.path.exists(DATASET_PATH):
        raise FileNotFoundError(f"Dataset bulunamadı: {DATASET_PATH}")

    print("Pipeline yükleniyor...")
    obj             = joblib.load(PIPELINE_PATH)
    churn_model     = obj['model']
    scaler          = obj['scaler']
    clip_bounds     = obj['clip_bounds']
    medians         = obj['medians']
    feature_columns = obj['feature_columns']
    all_features    = obj.get('all_features', feature_columns)
    metric_cols     = obj['metric_cols']
    threshold       = obj.get('threshold', 0.5)
    shap_explainer  = obj.get('shap_explainer', None)

    if shap_explainer is None:
        print("⚠️  SHAP explainer pipeline içinde yok!")
    else:
        print("✅ SHAP explainer yüklendi")

    print("Veri seti okunuyor...")
    df = pd.read_csv(DATASET_PATH, encoding="utf-8-sig")
    RAW_CUSTOMERS = df.set_index('CustomerID').to_dict(orient='index')

    print(f"✅ Pipeline hazır. {len(RAW_CUSTOMERS)} müşteri yüklendi. Threshold={threshold}")


def get_raw_customer(customer_id: int):
    return RAW_CUSTOMERS.get(customer_id)


def preprocess_single_row(customer_id: int) -> pd.DataFrame:
    raw_data = get_raw_customer(customer_id)
    if raw_data is None:
        return None

    df = pd.DataFrame([raw_data])
    df = df.drop(columns=COLS_TO_DROP, errors='ignore')
    df = df.replace(['Unknown', '', ' ', 'unknown'], np.nan)

    for col, val in medians.items():
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(val)

    for col in COLS_TO_CLIP:
        if col not in df.columns:
            continue
        lo, hi = clip_bounds.get(col, (None, None))
        if lo is not None:
            df[f"{col}_clipped"] = df[col].clip(lower=lo, upper=hi)
        else:
            df[f"{col}_clipped"] = df[col]

    for col in COLS_TO_LOG:
        if col not in df.columns:
            continue
        df[f"{col}_log"] = np.log1p(df[col].clip(lower=0))

    df['CreditRating'] = df['CreditRating'].map(CREDIT).fillna(3).astype(int)
    df['HandsetPrice'] = pd.to_numeric(df['HandsetPrice'], errors='coerce').fillna(
        medians.get('HandsetPrice', 0)
    ).astype(int)

    for col in COLS_METRIC_TO_BINARY:
        if col in df.columns:
            df[col] = (pd.to_numeric(df[col], errors='coerce').fillna(0) > 0).astype(int)

    for col in BINARY_COLS:
        if col in df.columns:
            df[col] = df[col].map(YES_NO).fillna(0).astype(int)

    df = pd.get_dummies(df, columns=COLS_TO_ENCODE, drop_first=False)
    df[df.select_dtypes(include='bool').columns] = df.select_dtypes(include='bool').astype(int)

    df = df.reindex(columns=all_features, fill_value=0)

    scaler_input_cols = list(getattr(scaler, 'feature_names_in_', metric_cols))
    for c in scaler_input_cols:
        if c not in df.columns:
            df[c] = 0
    df[scaler_input_cols] = df[scaler_input_cols].fillna(0).astype(float)
    df[scaler_input_cols] = scaler.transform(df[scaler_input_cols])

    df = df.reindex(columns=feature_columns, fill_value=0)
    return df


def humanize_feature(name: str) -> str:
    if name in FEATURE_LABELS:
        return FEATURE_LABELS[name]
    for prefix in ['PrizmCode_', 'Occupation_', 'IncomeGroup_', 'CreditRating_']:
        if name.startswith(prefix):
            value = name.replace(prefix, '')
            base  = prefix.rstrip('_')
            return f"{base}: {value}"
    return name.replace('_', ' ').title()


def get_shap_explanation(processed_df: pd.DataFrame, top_n: int = 5):
    if shap_explainer is None:
        return []

    shap_values = shap_explainer.shap_values(processed_df)
    if isinstance(shap_values, list):
        shap_values = shap_values[1] if len(shap_values) > 1 else shap_values[0]

    values = shap_values[0]
    feature_names = processed_df.columns.tolist()
    feature_values = processed_df.iloc[0].values

    label_groups = {}
    for name, val, raw in zip(feature_names, values, feature_values):
        label = humanize_feature(name)
        if label not in label_groups:
            label_groups[label] = {
                'feature':       name,
                'label':         label,
                'shap_value':    0.0,
                'feature_value': float(raw),
            }
        label_groups[label]['shap_value'] += float(val)

    contributions = []
    for label, info in label_groups.items():
        val = info['shap_value']
        contributions.append({
            'feature':       info['feature'],
            'label':         label,
            'shap_value':    val,
            'feature_value': info['feature_value'],
            'direction':     'risk_artirici' if val > 0 else 'risk_azaltici',
            'abs_impact':    abs(val),
        })

    contributions.sort(key=lambda x: x['abs_impact'], reverse=True)
    return contributions[:top_n]


def predict_customer_churn(customer_id: int):
    raw_data = get_raw_customer(customer_id)
    if raw_data is None:
        return None

    processed_df = preprocess_single_row(customer_id)
    if processed_df is None:
        return None

    proba   = float(churn_model.predict_proba(processed_df)[0][1])
    is_high = proba >= threshold

    shap_top = get_shap_explanation(processed_df, top_n=5)

    risk_factors = [s for s in shap_top if s['direction'] == 'risk_artirici']
    protective   = [s for s in shap_top if s['direction'] == 'risk_azaltici']

    result = raw_data.copy()
    result["CustomerID"]       = customer_id
    result["churn_proba"]      = proba
    result["churn_risk_level"] = "high" if is_high else "low"
    result["churn_risk"]       = "Yüksek Risk" if is_high else "Düşük Risk"
    result["shap_top_factors"] = shap_top
    result["risk_factors"]     = risk_factors
    result["protective_factors"] = protective

    return result
