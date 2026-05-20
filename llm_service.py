import os
import re
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

client = None
if not GEMINI_API_KEY:
    print("⚠️ GEMINI_API_KEY .env dosyasında bulunamadı!")
else:
    client = genai.Client(api_key=GEMINI_API_KEY)

MODEL_NAME = "gemini-2.5-flash-lite"


SYSTEM_INSTRUCTION = """
Sen "Pulse Retention Copilot" adında, telekom çağrı merkezi temsilcisine
SHAP açıklamaları üzerinden hızlı aksiyon öneren bir retention destek asistanısın.

GENEL KURALLAR:
1. Resmi "siz" dili kullan.
2. Gereksiz sohbet kalıpları kullanma.
3. "Tabii ki", "elbette", "harika soru", "yardımcı olayım" gibi ifadeler yasaktır.
4. Sadece verilen müşteri verisini, churn tahminini ve SHAP faktörlerini kullan.
5. Veride olmayan kampanya, ücret, taahhüt veya müşteri davranışı uydurma.
6. Diğer genel öneri sorularında cevap mutlaka "Evet," veya "Hayır," ile başlamalıdır.
7. Genel cevaplar 4-5 cümleyi asla geçmemelidir.
8. Son cümlede mutlaka somut aksiyon olmalıdır.

FORMAT KURALLARI:
1. Teklif önerisi istenirse cevap mutlaka madde işaretleriyle başlamalıdır.
2. Paket içerikleri şu biçimde verilmelidir:
• 500 dk
• 40 GB
• 6 ay %20 indirim
3. Özet istenirse cevap "Müşterinin Özeti" başlığıyla başlamalıdır.
4. Risk faktörleri istenirse sayı belirtilmişse tam o kadar faktör ver.
5. "3 faktör" denirse 3 faktör, "5 faktör" denirse 5 faktör ver.
6. Sayı belirtilmezse en önemli 3 faktörü ver.
7. Senaryo istenirse mutlaka temsilci konuşma senaryosu üret.
8. Başlık ve madde işareti sadece teklif, özet, faktör listesi ve senaryo cevaplarında kullanılabilir.

Risk seviyesi yorumlarken şu eşikleri kullan:
• %50 ve üzeri: ACİL / yüksek risk
• %27 - %49.9: PROAKTİF / orta risk
• %27 altı: SADAKAT / düşük risk

RİSK TIER KURALI (EN ÖNEMLİ — İHLAL EDİLEMEZ):
Müşteri Kartındaki "Risk Tier" alanı sistem tarafından atanmıştır.
Bu alanı ASLA sorgulama, ASLA override etme, ASLA "aslında PROAKTİF" gibi yeniden yorumlama.
Churn yüzdesine bakıp kendi tier'ını uydurma. Sadece kartta yazan tier'a göre cevap üret.
"Stratejik Yönlendirme" bölümündeki tone ve strategy direktiflerine harfiyen uy.
PROAKTİF veya SADAKAT tier'ında "müşteriyle temas kurulmalı", "iletişime geçilmeli",
"aranmalı" gibi ifadeleri ASLA kullanma. PROAKTİF'te kanalı açıkça SMS/e-posta de;
SADAKAT'ta yalnızca otomatik sadakat programı (puan, doğum günü mesajı) öner.
%29 gibi değerler yüksek risk olarak adlandırılamaz.

Churn olasılığı %50'nin altındaysa "yüksek risk" ifadesini kullanma.

"""




CONTEXT_TEMPLATE = """[MÜŞTERİ KARTI]

KİMLİK
• ID: {customer_id}
• Meslek: {occupation}
• Yaş: {age}
• Gelir Grubu: {income_group}

ABONELİK
• Hizmet Süresi: {months} ay
• Aktif Abonelik Sayısı: {active_subs}
• Önceki Retention Çağrısı: {retention_calls}
• Önceki Kabul Edilen Teklif: {retention_accepted}

KULLANIM
• Aylık Dakika: {monthly_minutes}
• Aylık Gelir: ${monthly_revenue}
• Toplam Aylık Ücret: ${total_charge}
• Aşım Dakika: {overage}
• Gelir Değişimi: {revenue_change}%

KALİTE
• Düşen Çağrı: {dropped_calls}
• Engellenen Çağrı: {blocked_calls}
• Müşteri Hizmetleri Çağrısı: {care_calls}

CİHAZ
• Cihaz Yaşı: {equipment_days} gün
• Cihaz Sayısı: {handsets}

[MODEL TAHMİNİ]
- Churn Olasılığı: %{proba_pct}
- Risk Etiketi: {risk_label}
- Eşik Değeri: %27

[ATANMIŞ RİSK TIER — BU DEĞERİ DEĞİŞTİRME, YENİDEN YORUMLAMA]
>>> {risk_tier} <
Bu tier sistem tarafından kesinleştirilmiştir. Cevabın tamamen bu tier'a göre şekillenmelidir.

[SHAP — RİSK ARTIRAN FAKTÖRLER]
{risk_factors_text}

[SHAP — KORUYUCU FAKTÖRLER]
{protective_factors_text}

[STRATEJİK YÖNLENDİRME]
• Risk tonu: {tone_directive}
• Stratejik öneri: {strategy}
"""


PROMPT_TEMPLATES = {
    "default": """[GÖREV: GENEL AKSİYON CEVABI]

Kullanıcının sorusuna 4-5 cümleyi geçmeden cevap ver.
Eğer soru öneri niteliğindeyse "Evet," veya "Hayır," ile başla.
Risk seviyesini, churn yüzdesini ve en kritik SHAP faktörünü belirt.
Son cümlede somut aksiyon öner.
Düz paragraf yaz, başlık ve madde kullanma.""",

    "risk_factors": """[GÖREV: RİSK FAKTÖRLERİ]

Kullanıcı kaç faktör istediyse tam o kadar faktör ver.
Sayı belirtmediyse en önemli 3 faktörü ver.
Cevap şu formatta olsun:

En Önemli Risk Faktörleri
• Faktör adı: kısa açıklama
• Faktör adı: kısa açıklama

Sonuna tek cümlelik aksiyon önerisi ekle.""",

    "suggest_offer": """[GÖREV: TEKLİF ÖNERİSİ]

Cevap mutlaka madde işaretleriyle başlasın.
Önerilen paketi net şekilde yaz.
Paket içeriğinde dakika, GB, süre veya indirim varsa ayrı maddeler halinde ver.
Sonrasında bu teklifin hangi SHAP faktörünü hedeflediğini kısa açıkla.

Format:
• 500 dk
• 40 GB
• 6 ay %20 indirim

Bu teklif, müşterinin kullanım davranışına göre mevcut paketin yetersiz kalma riskini azaltmak için önerilmektedir.""",

    "call_script": """[GÖREV: KONUŞMA SENARYOSU]

Temsilci için kısa konuşma senaryosu yaz.
Sadece temsilci konuşsun, müşteri repliği yazma.

Format:
Konuşma Senaryosu
• Açılış: ...
• İhtiyaç Tespiti: ...
• Teklif: ...
• Kapanış: ...

Cümleler kısa, resmi ve çağrı merkezi diline uygun olsun.""",

    "summary": """[GÖREV: MÜŞTERİ ÖZETİ]

Cevap mutlaka şu başlıkla başlasın:
Müşterinin Özeti

Altına maddeli kısa özet yaz.
Demografi, hizmet süresi, churn riski, en önemli SHAP faktörü ve önerilen aksiyon yer alsın.

Format:
Müşterinin Özeti
• ...
• ...
• ...
• Önerilen aksiyon: ..."""
}


def get_risk_tier(proba: float) -> dict:
    if proba >= 0.50:
        return {
            'level':    'ACİL',
            'tone':     'aciliyet ve hızlı aksiyon vurgusu yap. "Önümüzdeki 7 gün içinde", "öncelikli liste", "acil arama" gibi ifadeler kullan. Mutlaka temas önerisi sun.',
            'strategy': 'Yüksek değerli, kişiselleştirilmiş teklif sun. Doğrudan iletişim ZORUNLU. Telefon araması öncelikli kanal.'
        }
    elif proba >= 0.30:
        return {
            'level':    'PROAKTİF',
            'tone':     'önleyici, dengeli ton. Aktif arama YOK; SMS veya e-posta gibi düşük temaslı kanalları öner. "Hizmet kalitesi izleme", "pasif iletişim" gibi ifadeler.',
            'strategy': 'Proaktif izleme. Sorun belirtisi varsa SMS/e-posta ile değer önerisi. Doğrudan arama yapılmamalı; müşteri rahatsız edilmemeli.'
        }
    else:
        return {
            'level':    'SADAKAT',
            'tone':     'olumlu ton. Aktif iletişim önerme. "Aramaya gerek yok", "otomatik sadakat programı", "küçük teşekkür hareketi" ifadeleri kullan. Soruda arama/temas geçse bile NET şekilde HAYIR de.',
            'strategy': 'AKTİF İLETİŞİM YAPILMAMALI. Düşük riskli müşteri arandığında ters etki (rahatsızlık, batırma riski) doğar. Sadece otomatik sadakat programı: puan, küçük hediye, doğum günü SMS gibi düşük maliyetli pasif teşekkürler.'
        }

def extract_requested_factor_count(user_message: str) -> int:
    msg = user_message.lower()

    number_map = {
        "bir": 1,
        "iki": 2,
        "üç": 3,
        "uc": 3,
        "dört": 4,
        "dort": 4,
        "beş": 5,
        "bes": 5
    }

    digit_match = re.search(r"\b([1-5])\b", msg)
    if digit_match:
        return int(digit_match.group(1))

    for word, number in number_map.items():
        if word in msg:
            return number

    return 3


def detect_template(user_message: str) -> str:
    msg = user_message.lower()

    if any(k in msg for k in [
        "risk faktör", "neden risk", "churn riski", "en önemli faktör",
        "faktör nedir", "neden ayrıl", "3 faktör", "5 faktör",
        "üç faktör", "beş faktör", "en önemli"
    ]):
        return "risk_factors"

    if any(k in msg for k in [
        "teklif", "paket", "kampanya", "indirim", "öneri sun",
        "hangi teklifi", "ne önerelim"
    ]):
        return "suggest_offer"

    if any(k in msg for k in [
        "senaryo", "arama", "arayacak", "görüşme", "diyalog",
        "ne söyleyeyim", "nasıl konuş", "konuşma metni"
    ]):
        return "call_script"

    if any(k in msg for k in [
        "özet", "özetle", "profil", "genel bilgi", "kim bu müşteri"
    ]):
        return "summary"

    return "default"


def safe(val, default="Veri yok"):
    if val is None or val == "" or str(val).strip().lower() == "unknown":
        return default
    return val


def build_customer_context(customer_data: dict) -> str:
    risk_factors = customer_data.get("risk_factors", [])
    protective = customer_data.get("protective_factors", [])
    proba = customer_data.get("churn_proba", 0)
    risk_label = customer_data.get("churn_risk", "Bilinmiyor")
    tier = get_risk_tier(proba)

    risk_text = "\n".join([
        f"• {f.get('label', 'Bilinmeyen faktör')}: +%{f.get('abs_impact', 0) * 100:.1f}"
        for f in risk_factors
    ]) or "• Belirgin risk faktörü tespit edilmedi."

    protective_text = "\n".join([
        f"• {f.get('label', 'Bilinmeyen faktör')}: -%{f.get('abs_impact', 0) * 100:.1f}"
        for f in protective
    ]) or "• Belirgin koruyucu faktör tespit edilmedi."

    return CONTEXT_TEMPLATE.format(
        customer_id=safe(customer_data.get("CustomerID"), "?"),
        occupation=safe(customer_data.get("Occupation")),
        age=safe(customer_data.get("AgeHH1")),
        income_group=safe(customer_data.get("IncomeGroup")),
        months=safe(customer_data.get("MonthsInService")),
        active_subs=safe(customer_data.get("ActiveSubs")),
        retention_calls=safe(customer_data.get("RetentionCalls"), "0"),
        retention_accepted=safe(customer_data.get("RetentionOffersAccepted"), "0"),
        monthly_minutes=safe(customer_data.get("MonthlyMinutes")),
        monthly_revenue=safe(customer_data.get("MonthlyRevenue")),
        total_charge=safe(customer_data.get("TotalRecurringCharge")),
        overage=safe(customer_data.get("OverageMinutes"), "0"),
        revenue_change=safe(customer_data.get("PercChangeRevenues"), "0"),
        dropped_calls=safe(customer_data.get("DroppedCalls"), "0"),
        blocked_calls=safe(customer_data.get("BlockedCalls"), "0"),
        care_calls=safe(customer_data.get("CustomerCareCalls"), "0"),
        equipment_days=safe(customer_data.get("CurrentEquipmentDays")),
        handsets=safe(customer_data.get("Handsets")),
        proba_pct=f"{proba * 100:.1f}",
        risk_label=risk_label,
        risk_tier=tier["level"],
        risk_factors_text=risk_text,
        protective_factors_text=protective_text,
        tone_directive=tier["tone"],
        strategy=tier["strategy"]
    )


def chat_with_llm(customer_data: dict, conversation: list) -> str:
    if client is None:
        return "Gemini API key tanımlanmamış. .env dosyasını kontrol edin."

    try:
        last_msg = conversation[-1].get("content", "") if conversation else ""
        template_key = detect_template(last_msg)
        template = PROMPT_TEMPLATES.get(template_key, PROMPT_TEMPLATES["default"])
        context = build_customer_context(customer_data)

        factor_count = extract_requested_factor_count(last_msg)

        history_text = ""
        for msg in conversation[:-1][-4:]:
            role = "Temsilci" if msg.get("role") == "user" else "Pulse Retention Copilot"
            history_text += f"{role}: {msg.get('content', '')}\n\n"

        full_prompt = f"""{context}

[GÖREV ŞABLONU]
{template}

[EK TALİMAT]
Eğer görev risk faktörleri ise tam olarak {factor_count} faktör ver.
Eğer görev teklif önerisi ise cevap madde işaretleriyle başlasın.
Eğer görev özet ise "Müşterinin Özeti" başlığıyla başlasın.
Eğer görev senaryo ise "Konuşma Senaryosu" başlığıyla başlasın.
Genel öneri sorularında cevap "Evet," veya "Hayır," ile başlasın.
Müşteri Kartındaki "Atanmış Risk Tier" değerine harfiyen uy.
Tier ACİL değilse "müşteriyle temas kurulmalı", "iletişime geçilmeli", "aranmalı" gibi ifadeleri ASLA kullanma.
PROAKTİF tier'da yalnızca SMS/e-posta öner. SADAKAT tier'da yalnızca otomatik sadakat programı öner.

[KONUŞMA GEÇMİŞİ]
{history_text or "(Henüz konuşma yok)"}

[KULLANICININ MEVCUT SORUSU]
{last_msg}

Yanıtı Türkçe yaz.
"""

        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.3,
                max_output_tokens=500,
                top_p=0.9,
                top_k=40,
                thinking_config=types.ThinkingConfig(thinking_budget=0),
            )
        )

        text = response.text or ""

        if not text and hasattr(response, "candidates") and response.candidates:
            cand = response.candidates[0]
            if cand.content and cand.content.parts:
                text = "".join([
                    p.text for p in cand.content.parts
                    if hasattr(p, "text")
                ])

        if not text:
            return "Yanıt üretilemedi. Lütfen tekrar deneyin."

        return text.strip()

    except Exception as e:
        err = str(e)

        if "429" in err or "RESOURCE_EXHAUSTED" in err:
            return (
                "Şu anda AI yanıt limiti doldu. "
                "Lütfen yaklaşık 1 dakika sonra tekrar deneyin. "
                "Bu sırada SHAP risk faktörleri ekranda görüntülenmeye devam ediyor."
            )

        return f"LLM hatası: {err}"