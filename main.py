import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId

from database import db, create_document, get_documents
from schemas import Product, Order, OrderItem

app = FastAPI(title="BlueLight Gaming Shop API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "BlueLight Gaming Shop API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    return response

# Seed products if collection is empty
@app.post("/seed")
def seed_products():
    try:
        count = db["product"].count_documents({}) if db else 0
        if count > 0:
            return {"seeded": False, "message": "Products already exist"}
        items = [
            {
                "title": "Arcade Pro Blue Light Glasses",
                "description": "Retro-styled frames with premium blue light filtering for marathon sessions.",
                "price": 69.0,
                "category": "gaming",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?q=80&w=1200&auto=format&fit=crop",
                "tint": "amber"
            },
            {
                "title": "Neon Pixel Shields",
                "description": "Ultra-light, anti-glare lenses with vaporwave vibes.",
                "price": 89.0,
                "category": "gaming",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1483985970261-352edc3d1c06?q=80&w=1200&auto=format&fit=crop",
                "tint": "clear"
            },
            {
                "title": "CRT Guardian Lenses",
                "description": "Maximum protection with retro flair. Stream-ready.",
                "price": 99.0,
                "category": "gaming",
                "in_stock": True,
                "image": "https://images.unsplash.com/photo-1512436991641-6745cdb1723f?q=80&w=1200&auto=format&fit=crop",
                "tint": "rose"
            }
        ]
        for it in items:
            create_document("product", it)
        return {"seeded": True, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/products", response_model=List[Product])
def list_products():
    try:
        docs = get_documents("product")
        # convert ObjectId to str and conform to Product model
        normalized = []
        for d in docs:
            d.pop("_id", None)
            normalized.append(Product(**d))
        return normalized
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class CartItem(BaseModel):
    product_id: str
    quantity: int = 1

class CheckoutRequest(BaseModel):
    items: List[CartItem]
    email: Optional[str] = None

@app.post("/checkout")
def checkout(payload: CheckoutRequest):
    try:
        total = 0.0
        for item in payload.items:
            prod = db["product"].find_one({"_id": ObjectId(item.product_id)})
            if not prod:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            total += float(prod.get("price", 0)) * item.quantity
        order = Order(email=payload.email, items=[
            # store as simple dicts
            {"product_id": it.product_id, "quantity": it.quantity} for it in payload.items
        ], total=round(total, 2), status="paid")
        order_id = create_document("order", order)
        return {"ok": True, "order_id": order_id, "total": order.total}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
