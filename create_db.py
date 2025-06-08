import mysql.connector
from mysql.connector import Error
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine

# 環境変数の読み込み
base_path = Path(__file__).parent  # backendディレクトリへのパス
env_path = base_path / '.env'
load_dotenv(dotenv_path=env_path)

# データベース接続情報
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_NAME = os.getenv('DB_NAME')

# データベース接続情報
DB_CONFIG = {
    'host': DB_HOST,
    'user': DB_USER,
    'password': DB_PASSWORD,
    'database': DB_NAME
}

# SSL証明書のパス
ssl_cert = str(base_path / 'DigiCertGlobalRootCA.crt.pem')

# MySQLのURL構築
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_NAME}"

# エンジンの作成（SSL設定を追加）
engine = create_engine(
    DATABASE_URL,
    connect_args={
        "ssl": {
            "ssl_ca": ssl_cert
        }
    },
    echo=True,
    pool_pre_ping=True,
    pool_recycle=3600
)

def init_database():
    try:
        # データベース接続
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 商品マスタテーブルの作成
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS pos_dummy_data (
            item_id INT AUTO_INCREMENT PRIMARY KEY,
            product_code BIGINT NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            price INT NOT NULL
        )
        """)
        
        # サンプルデータの挿入
        sample_data = [
            (1234567890, 'ソフラン', 300),
            (2345678901, 'タイガー歯ブラシ', 200),
            (3456789012, '四ツ谷サイダー', 160),
            (4567890123, '福島産ほれん草', 188),
            (4547366694253, '米津玄師', 2000)
        ]
        
        # 既存のデータを確認
        cursor.execute("SELECT * FROM pos_dummy_data")
        rows = cursor.fetchall()
        print("既存のデータ:")
        for row in rows:
            print(row)
            
        # データの挿入
        cursor.executemany(
            "INSERT INTO pos_dummy_data (product_code, product_name, price) VALUES (%s, %s, %s)",
            sample_data
        )
        
        # 取引テーブルの作成
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            transaction_date DATETIME NOT NULL,
            cashier_code VARCHAR(255) NOT NULL,
            store_code VARCHAR(255) NOT NULL,
            pos_id VARCHAR(255) NOT NULL,
            total_amount INT NOT NULL
        )
        """)
        
        # 取引明細テーブルの作成
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS transaction_details (
            transaction_id INT,
            detail_id INT,
            item_id INT,
            product_code BIGINT,
            product_name VARCHAR(255),
            price INT,
            PRIMARY KEY (transaction_id, detail_id),
            FOREIGN KEY (transaction_id) REFERENCES transactions(id)
        )
        """)
        
        # 変更をコミット
        conn.commit()
        print("データベースの初期化が完了しました。")
        
        # データを確認
        cursor.execute("SELECT * FROM pos_dummy_data")
        rows = cursor.fetchall()
        print("\n挿入後のデータ:")
        for row in rows:
            print(row)

    except Error as e:
        print(f"エラーが発生しました: {str(e)}")
        if conn.is_connected():
            conn.rollback()
    finally:
        if conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    init_database() 