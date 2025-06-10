from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import mysql.connector
from mysql.connector import Error
from fastapi.middleware.cors import CORSMiddleware
import os
from fastapi.responses import JSONResponse
import logging
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

# ロギングの設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

# アプリケーション起動時のログ
logger.info("アプリケーションを起動します")
#logger.info(f"データベース接続情報: {DB_CONFIG}")

app = FastAPI()

# データベース接続情報
DB_CONFIG = {
    'host': os.getenv('DB_HOST'),
    'user': os.getenv('DB_USER'),
    'password': os.getenv('DB_PASSWORD'),
    'port': os.getenv('DB_PORT'),
    'database': os.getenv('DB_NAME')
}

# CORSの設定
origins = [
    "http://localhost:3000",    # Next.jsのデフォルトポート
    "http://localhost:8000",    # FastAPIのデフォルトポート
    "https://*.azurewebsites.net",  # Azure App Service
    "https://*.vercel.app",     # Vercel
    "*"  # 開発中は全てのオリジンを許可
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
        logger.info(f"商品コード検索開始: {code}")
        
        # 商品コードの型変換を試みる
        try:
            product_code = int(code)
        except ValueError:
            logger.error(f"無効な商品コード形式: {code}")
            return JSONResponse(
                status_code=400,
                content={"error": "商品コードは数値である必要があります"}
            )

        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        try:
            logger.info(f"データベースクエリ実行: product_code = {product_code}")
            cursor.execute("""
                SELECT item_id, product_code, product_name, price 
                FROM pos_dummy_data 
                WHERE product_code = %s
            """, (product_code,))
            
            result = cursor.fetchone()
            logger.info(f"クエリ結果: {result}")
            
            if result is None:
                logger.warning(f"商品が見つかりません: {product_code}")
                return JSONResponse(
                    status_code=404,
                    content={"error": "商品がマスタ未登録です"}
                )
                
            response_data = {
                "item_id": result[0],
                "product_code": result[1],
                "product_name": result[2],
                "price": result[3]
            }
            logger.info(f"レスポンスデータ: {response_data}")
            return response_data

        except Error as e:
            logger.error(f"データベースエラー: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"データベースエラー: {str(e)}"}
            )
        finally:
            if conn.is_connected():
                cursor.close()
                conn.close()
    except Exception as e:
        logger.error(f"予期せぬエラー: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"予期せぬエラー: {str(e)}"}
        )

@app.post("/api/purchase")
async def purchase(request: PurchaseRequest):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 取引テーブルへの登録
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cashier_code = request.cashier_code if request.cashier_code else "9999999999"
        
        cursor.execute("""
            INSERT INTO transactions 
            (transaction_date, cashier_code, store_code, pos_id, total_amount)
            VALUES (%s, %s, %s, %s, %s)
        """, (current_time, cashier_code, request.store_code, request.pos_id, 0))
        
        transaction_id = cursor.lastrowid
        
        # 明細の登録と合計金額の計算
        total_amount = 0
        for index, item in enumerate(request.items, 1):
            cursor.execute("""
                INSERT INTO transaction_details
                (transaction_id, detail_id, item_id, product_code, product_name, price)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (transaction_id, index, item.item_id, item.product_code, 
                  item.product_name, item.price))
            total_amount += item.price
        
        # 合計金額の更新
        cursor.execute("""
            UPDATE transactions 
            SET total_amount = %s 
            WHERE id = %s
        """, (total_amount, transaction_id))
        
        conn.commit()
        return {"success": True, "total_amount": total_amount}
    
    except Exception as e:
        conn.rollback()
        logger.error(f"購入処理中のエラー: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close() 