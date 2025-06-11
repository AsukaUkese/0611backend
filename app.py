from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from dotenv import load_dotenv
import os
import logging

# .env 読み込み
load_dotenv()

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)
logger.info("アプリケーションを起動します")

# DB接続設定
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

app = FastAPI()

# CORS設定
origins = [
    "http://localhost:3000",
    "http://localhost:8000",
    "https://*.azurewebsites.net",
    "https://*.vercel.app",
    "*"
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

@app.get("/")
async def root():
    return {"message": "POS API Server is running"}

class ProductResponse(BaseModel):
    item_id: int
    product_code: int
    product_name: str
    price: int

class PurchaseItem(BaseModel):
    item_id: int
    product_code: int
    product_name: str
    price: int

class PurchaseRequest(BaseModel):
    cashier_code: str
    store_code: str = "30"
    pos_id: str = "90"
    items: List[PurchaseItem]

@app.get("/api/products/{code}")
async def get_product(code: str):
    try:
        product_code = int(code)
    except ValueError:
        logger.error(f"無効な商品コード: {code}")
        return JSONResponse(status_code=400, content={"error": "商品コードは数値である必要があります"})

    # 🔧 修正：スキーマ名を明示的に指定
    query = text("""
        SELECT item_id, product_code, product_name, price 
        FROM pos_asuka.product_master 
        WHERE product_code = :product_code
    """)
    
    try:
        with engine.connect() as conn:
            result = conn.execute(query, {"product_code": product_code}).fetchone()
            if result is None:
                logger.warning(f"商品が見つかりません: {product_code}")
                return JSONResponse(status_code=404, content={"error": "商品がマスタ未登録です"})
            return dict(result._mapping)
    except SQLAlchemyError as e:
        logger.error(f"データベースエラー: {str(e)}")
        return JSONResponse(status_code=500, content={"error": f"データベースエラー: {str(e)}"})

@app.post("/api/purchase")
async def purchase(request: PurchaseRequest):
    try:
        with engine.begin() as conn:
            # 取引登録
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            insert_transaction = text("""
                INSERT INTO transactions (transaction_date, cashier_code, store_code, pos_id, total_amount)
                VALUES (:transaction_date, :cashier_code, :store_code, :pos_id, 0)
            """)
            result = conn.execute(insert_transaction, {
                "transaction_date": now,
                "cashier_code": request.cashier_code or "9999999999",
                "store_code": request.store_code,
                "pos_id": request.pos_id
            })
            transaction_id = result.lastrowid

            # 明細登録
            total_amount = 0
            for idx, item in enumerate(request.items, 1):
                insert_detail = text("""
                    INSERT INTO transaction_details
                    (transaction_id, detail_id, item_id, product_code, product_name, price)
                    VALUES (:transaction_id, :detail_id, :item_id, :product_code, :product_name, :price)
                """)
                conn.execute(insert_detail, {
                    "transaction_id": transaction_id,
                    "detail_id": idx,
                    "item_id": item.item_id,
                    "product_code": item.product_code,
                    "product_name": item.product_name,
                    "price": item.price
                })
                total_amount += item.price

            # 合計金額更新
            update_total = text("""
                UPDATE transactions SET total_amount = :total_amount WHERE id = :transaction_id
            """)
            conn.execute(update_total, {
                "total_amount": total_amount,
                "transaction_id": transaction_id
            })

        return {"success": True, "total_amount": total_amount}
    
    except SQLAlchemyError as e:
        logger.error(f"購入処理エラー: {str(e)}")
        raise HTTPException(status_code=500, detail=f"購入処理中のエラー: {str(e)}")
