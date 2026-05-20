from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional

import preprocessing
from preprocessing import setup_pipeline, get_raw_customer, predict_customer_churn
from llm_service import chat_with_llm
from auth import login, logout, get_session
from report_service import generate_pdf_report
from fastapi.responses import Response


app = FastAPI(
    title="Pulse AI — Telco Churn Analizi",
    description="SHAP destekli müşteri kayıp tahmin ve LLM aksiyon önerisi sistemi."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.staticfiles import StaticFiles
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

setup_pipeline()


class LoginRequest(BaseModel):
    username: str
    password: str


class ChatSorgusu(BaseModel):
    customer_id: int
    messages: list
    customer_data: dict


def auth_check(authorization: Optional[str]) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Token gerekli.")
    token = authorization.replace("Bearer ", "").strip()
    session = get_session(token)
    if not session:
        raise HTTPException(status_code=401, detail="Geçersiz oturum.")
    return session


@app.get("/")
def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html")


@app.get("/temsilci")
def agent_page(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/yonetici")
def manager_page(request: Request):
    return templates.TemplateResponse(request, "manager.html")


@app.get("/health")
def health():
    return {"durum": "API aktif ve çalışıyor."}


@app.post("/api/login")
def api_login(req: LoginRequest):
    result = login(req.username, req.password)
    if result is None:
        raise HTTPException(status_code=401, detail="Kullanıcı adı veya şifre hatalı.")
    return result


@app.post("/api/logout")
def api_logout(authorization: Optional[str] = Header(None)):
    if authorization:
        token = authorization.replace("Bearer ", "").strip()
        logout(token)
    return {"ok": True}


@app.get("/api/customer/{musteri_id}")
def musteri_getir(musteri_id: int, authorization: Optional[str] = Header(None)):
    auth_check(authorization)

    customer = get_raw_customer(musteri_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"{musteri_id} ID'li müşteri bulunamadı.")

    result = predict_customer_churn(musteri_id)
    if result is None:
        raise HTTPException(status_code=500, detail="Tahmin sırasında bir hata oluştu.")
    return result


@app.get("/api/customers/top-risky")
def top_risky(limit: int = 10, authorization: Optional[str] = Header(None)):
    session = auth_check(authorization)
    if session["role"] != "manager":
        raise HTTPException(status_code=403, detail="Bu sayfaya yalnızca yöneticiler erişebilir.")

    all_predictions = []
    error_count = 0
    first_error = None
    for cid in list(preprocessing.RAW_CUSTOMERS.keys())[:100]:
        try:
            result = predict_customer_churn(cid)
            if result:
                all_predictions.append({
                    "CustomerID":      cid,
                    "churn_proba":     result["churn_proba"],
                    "churn_risk":      result["churn_risk"],
                    "Occupation":      result.get("Occupation", "—"),
                    "MonthsInService": result.get("MonthsInService", "—"),
                    "MonthlyRevenue":  result.get("MonthlyRevenue", "—"),
                })
        except Exception as e:
            error_count += 1
            if first_error is None:
                first_error = f"CID {cid}: {type(e).__name__}: {str(e)}"
            continue

    print(f"⚠️ Toplam hata: {error_count}/500")
    if first_error:
        print(f"İlk hata: {first_error}")
    print(f"✅ Başarılı predict: {len(all_predictions)}")

    all_predictions.sort(key=lambda x: x["churn_proba"], reverse=True)

    acil     = [p for p in all_predictions if p["churn_proba"] >= 0.50][:limit]
    proaktif = [p for p in all_predictions if 0.30 <= p["churn_proba"] < 0.50][:limit]
    sadakat  = [p for p in all_predictions if p["churn_proba"] < 0.30][:limit]

    return {
        "acil":     acil,
        "proaktif": proaktif,
        "sadakat":  sadakat,
        "toplam":   len(all_predictions),
    }


@app.post("/api/chat")
def sohbet_et(sorgu: ChatSorgusu, authorization: Optional[str] = Header(None)):
    auth_check(authorization)

    if not sorgu.messages:
        raise HTTPException(status_code=400, detail="Mesaj boş olamaz.")

    full_customer = predict_customer_churn(sorgu.customer_id)
    if full_customer is None:
        raise HTTPException(status_code=404, detail="Müşteri bulunamadı.")

    reply = chat_with_llm(full_customer, sorgu.messages)
    return {"reply": reply}

@app.get("/api/report/pdf")
def download_pdf_report(authorization: Optional[str] = Header(None)):
    session = auth_check(authorization)
    if session["role"] != "manager":
        raise HTTPException(status_code=403, detail="Yalnızca yöneticiler rapor indirebilir.")

    data = top_risky(limit=10, authorization=authorization)
    pdf_bytes = generate_pdf_report(data)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="pulse-ai-rapor.pdf"'
        }
    )


SAMPLE_CUSTOMERS_CACHE = None

@app.get("/api/sample-customers")
def sample_customers():
    global SAMPLE_CUSTOMERS_CACHE
    if SAMPLE_CUSTOMERS_CACHE is not None:
        return SAMPLE_CUSTOMERS_CACHE

    all_predictions = []
    for cid in list(preprocessing.RAW_CUSTOMERS.keys())[:200]:
        try:
            result = predict_customer_churn(cid)
            if result:
                all_predictions.append({
                    "CustomerID": cid,
                    "churn_proba": result["churn_proba"],
                })
        except Exception:
            continue

    all_predictions.sort(key=lambda x: x["churn_proba"], reverse=True)

    acil     = [p for p in all_predictions if p["churn_proba"] >= 0.50][:4]
    proaktif = [p for p in all_predictions if 0.30 <= p["churn_proba"] < 0.50][:4]
    sadakat  = [p for p in all_predictions if p["churn_proba"] < 0.30][:4]

    samples = acil + proaktif + sadakat
    ids = [s["CustomerID"] for s in samples]

    SAMPLE_CUSTOMERS_CACHE = {"ids": ids}
    return SAMPLE_CUSTOMERS_CACHE

    