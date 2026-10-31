
from pathlib import Path
from functools import lru_cache
from typing import Any
import re, math
import numpy as np
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score, mean_squared_error, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

app = FastAPI(title="Islamabad Property Price Intelligence API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "zameen_listings_2026-04-26_174727.xlsx"
FEATURES = ["size_marla", "sector", "prop_type", "listing_age_days", "is_professional"]

class PropertyInput(BaseModel):
    sector: str = "G-13"
    prop_type: str = "House"
    size_marla: float = Field(5, gt=0)
    listing_age_days: int = Field(7, ge=0)
    is_professional: bool = False

class ValueInput(PropertyInput):
    actual_price: float = Field(2.5, gt=0)

class CompareInput(BaseModel):
    property_a: ValueInput
    property_b: ValueInput

def parse_size(v: Any) -> float:
    m = re.search(r"(\d+(\.\d+)?)", str(v))
    return float(m.group(1)) if m else np.nan

def parse_sector(v: Any) -> str:
    m = re.search(r"G-\d{1,2}", str(v).upper())
    return m.group(0) if m else "G-13"

def parse_sub_sector(v: Any) -> str:
    text = str(v).upper()
    m = re.search(r"G-\d{1,2}/\d+", text)
    return m.group(0) if m else parse_sector(text)

def prop_type(title: Any) -> str:
    t = str(title).lower()
    if "plot" in t: return "Plot"
    if "apartment" in t or "flat" in t: return "Apartment"
    if "commercial" in t or "shop" in t or "office" in t or "plaza" in t: return "Commercial"
    return "House"

def age_days(v: Any) -> int:
    t = str(v).lower()
    m = re.search(r"(\d+)", t)
    n = int(m.group(1)) if m else 0
    if "hour" in t or "minute" in t or "today" in t: return 0
    if "week" in t: return n * 7
    if "month" in t: return n * 30
    if "year" in t: return n * 365
    return n

def tier(price: float) -> str:
    if price < 2.5: return "Budget"
    if price <= 3.1: return "Mid-range"
    return "Premium"

def recommendation(score: float) -> str:
    if score > 0.25: return "Buy"
    if score >= -0.15: return "Hold"
    return "Watch"

def records(df, limit=100):
    return df.replace([np.inf, -np.inf], np.nan).fillna("").head(limit).to_dict(orient="records")

def clean_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset file not found: {DATA_PATH}")
    df = pd.read_excel(DATA_PATH)
    df.columns = [str(c).strip() for c in df.columns]

    if "price_crore" not in df.columns:
        price_cols = [c for c in df.columns if "price" in c.lower()]
        if price_cols:
            df["price_crore"] = pd.to_numeric(df[price_cols[0]], errors="coerce")
        else:
            nums = df.select_dtypes(include=[np.number]).columns
            df["price_crore"] = pd.to_numeric(df[nums[0]], errors="coerce") if len(nums) else 2.5

    if "size_marla" not in df.columns:
        df["size_marla"] = df["size"].apply(parse_size) if "size" in df.columns else 5

    if "location" in df.columns:
        df["sector"] = df["location"].apply(parse_sector)
        df["sub_sector"] = df["location"].apply(parse_sub_sector)
    else:
        df["sector"] = df.get("sector", "G-13")
        df["sub_sector"] = df["sector"]

    if "prop_type" not in df.columns:
        df["prop_type"] = df["title"].apply(prop_type) if "title" in df.columns else "House"

    if "listing_age_days" not in df.columns:
        df["listing_age_days"] = df["date_added"].apply(age_days) if "date_added" in df.columns else 0

    if "is_professional" not in df.columns:
        if "seller_badge" in df.columns:
            df["is_professional"] = df["seller_badge"].astype(str).str.lower().str.contains("titanium|professional", na=False)
        else:
            df["is_professional"] = False

    df["price_crore"] = pd.to_numeric(df["price_crore"], errors="coerce")
    df["size_marla"] = pd.to_numeric(df["size_marla"], errors="coerce")
    df["listing_age_days"] = pd.to_numeric(df["listing_age_days"], errors="coerce").fillna(0).astype(int)
    df["price_crore"] = df["price_crore"].fillna(df["price_crore"].median() if not df["price_crore"].dropna().empty else 2.5)
    df["size_marla"] = df["size_marla"].fillna(df["size_marla"].median() if not df["size_marla"].dropna().empty else 5)
    df["sector"] = df["sector"].astype(str)
    df["prop_type"] = df["prop_type"].astype(str)
    df["is_professional"] = df["is_professional"].astype(bool)
    df["price_tier"] = df["price_crore"].apply(tier)
    df["price_per_marla"] = (df["price_crore"] / df["size_marla"].replace(0, np.nan)).fillna(0)
    return df.reset_index(drop=True)

def pipe(model):
    return Pipeline([
        ("prep", ColumnTransformer([
            ("cat", OneHotEncoder(handle_unknown="ignore"), ["sector", "prop_type"]),
            ("num", "passthrough", ["size_marla", "listing_age_days", "is_professional"]),
        ])),
        ("model", model)
    ])

@lru_cache(maxsize=1)
def state():
    df = clean_data()
    X = df[FEATURES].copy()
    X["is_professional"] = X["is_professional"].astype(int)
    y = df["price_crore"].astype(float)
    test_size = 0.30 if len(df) > 20 else 0.2
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    lr = pipe(LinearRegression())
    rf = pipe(RandomForestRegressor(n_estimators=180, random_state=42, min_samples_leaf=2))
    lr.fit(X_train, y_train)
    rf.fit(X_train, y_train)

    lr_pred = lr.predict(X_test)
    rf_pred = rf.predict(X_test)

    df["predicted_price"] = rf.predict(X)
    df["value_score"] = df["predicted_price"] - df["price_crore"]
    df["predicted_tier"] = df["predicted_price"].apply(tier)
    return {"df": df, "lr": lr, "rf": rf, "X_test": X_test, "y_test": y_test, "lr_pred": lr_pred, "rf_pred": rf_pred}

def predict_price(item: PropertyInput) -> float:
    row = pd.DataFrame([{
        "size_marla": item.size_marla,
        "sector": item.sector,
        "prop_type": item.prop_type,
        "listing_age_days": item.listing_age_days,
        "is_professional": int(item.is_professional),
    }])
    return float(state()["rf"].predict(row)[0])

@app.get("/")
def root():
    return {"status": "API running"}

@app.get("/summary")
def summary():
    df = state()["df"]
    sec = df.groupby("sector").agg(
        listings=("price_crore", "count"),
        avg_price=("price_crore", "mean"),
        avg_size=("size_marla", "mean"),
        avg_value_score=("value_score", "mean"),
    ).reset_index().round(3)
    return {
        "total_listings": int(len(df)),
        "average_price": round(float(df["price_crore"].mean()), 3),
        "average_size": round(float(df["size_marla"].mean()), 3),
        "sectors": sorted(df["sector"].unique().tolist()),
        "property_types": sorted(df["prop_type"].unique().tolist()),
        "property_type_count": df["prop_type"].value_counts().to_dict(),
        "sector_summary": sec.to_dict(orient="records"),
        "preview": records(df[["sector", "sub_sector", "prop_type", "size_marla", "price_crore", "listing_age_days", "price_tier"]], 12)
    }

@app.get("/charts")
def charts():
    df = state()["df"]
    sector_avg = df.groupby("sector")["price_crore"].mean().reset_index().round(3)
    type_count = df["prop_type"].value_counts().reset_index()
    type_count.columns = ["prop_type", "count"]
    return {
        "sector_avg": sector_avg.to_dict(orient="records"),
        "type_count": type_count.to_dict(orient="records"),
        "scatter": records(df[["size_marla", "price_crore", "sector", "prop_type"]], 500),
        "price_distribution": records(df[["price_crore"]], 500),
    }

@app.post("/predict")
def predict(item: PropertyInput):
    p = predict_price(item)
    return {"predicted_price": round(p, 3), "price_tier": tier(p), "advice": f"This property looks {tier(p).lower()} according to the dataset."}

@app.post("/value-check")
def value_check(item: ValueInput):
    p = predict_price(item)
    score = p - item.actual_price
    return {
        "predicted_price": round(p, 3),
        "actual_price": item.actual_price,
        "value_score": round(score, 3),
        "status": "Underpriced / Good investment" if score > 0 else "Overpriced / Not best value",
        "recommendation": recommendation(score),
        "price_tier": tier(p)
    }

@app.post("/compare")
def compare(item: CompareInput):
    a = value_check(item.property_a)
    b = value_check(item.property_b)
    better = "Property A" if a["value_score"] >= b["value_score"] else "Property B"
    return {"property_a": a, "property_b": b, "better_option": better, "final_recommendation": f"{better} has the stronger value score."}

@app.get("/explore")
def explore():
    df = state()["df"]
    cols = ["sector", "sub_sector", "prop_type", "size_marla", "price_crore", "price_per_marla", "listing_age_days", "is_professional", "value_score"]
    return {"count": int(len(df)), "rows": records(df[cols], 200)}

@app.get("/recommendations")
def recommendations():
    df = state()["df"]
    top = df.sort_values("value_score", ascending=False).head(10)
    sector = df.groupby("sector").agg(
        avg_price=("price_crore", "mean"),
        avg_predicted=("predicted_price", "mean"),
        avg_value_score=("value_score", "mean"),
        listings=("price_crore", "count"),
    ).reset_index()
    sector["recommendation"] = sector["avg_value_score"].apply(recommendation)
    sector = sector.round(3)
    best = sector.sort_values("avg_value_score", ascending=False).head(1).to_dict(orient="records")
    cols = ["sector", "sub_sector", "prop_type", "size_marla", "price_crore", "predicted_price", "value_score"]
    return {"top_10": records(top[cols], 10), "sector_recommendations": sector.to_dict(orient="records"), "best_sector": best[0] if best else {}}

@app.get("/model-performance")
def model_performance():
    s = state()
    y_test = s["y_test"]
    lr_pred = s["lr_pred"]
    rf_pred = s["rf_pred"]
    y_true_tier = y_test.apply(tier)
    y_pred_tier = pd.Series(rf_pred).apply(tier)
    cm = confusion_matrix(y_true_tier, y_pred_tier, labels=["Budget", "Mid-range", "Premium"]).tolist()
    report = classification_report(y_true_tier, y_pred_tier, labels=["Budget", "Mid-range", "Premium"], output_dict=True, zero_division=0)
    rf = s["rf"]
    prep = rf.named_steps["prep"]
    model = rf.named_steps["model"]
    names = list(prep.named_transformers_["cat"].get_feature_names_out(["sector", "prop_type"])) + ["size_marla", "listing_age_days", "is_professional"]
    importance = sorted([{"feature": n, "importance": round(float(v), 5)} for n, v in zip(names, model.feature_importances_)], key=lambda x: x["importance"], reverse=True)
    return {
        "linear_regression": {"r2": round(float(r2_score(y_test, lr_pred)), 4), "rmse": round(float(math.sqrt(mean_squared_error(y_test, lr_pred))), 4)},
        "random_forest": {"r2": round(float(r2_score(y_test, rf_pred)), 4), "rmse": round(float(math.sqrt(mean_squared_error(y_test, rf_pred))), 4)},
        "feature_importance": importance,
        "actual_vs_predicted": [{"actual": round(float(a), 3), "predicted": round(float(p), 3)} for a, p in zip(y_test, rf_pred)],
        "classification_report": report,
        "confusion_matrix": {"labels": ["Budget", "Mid-range", "Premium"], "matrix": cm}
    }
