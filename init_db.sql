-- 商品マスタテーブル
CREATE TABLE IF NOT EXISTS pos_dummy_data (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_code INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    price INTEGER NOT NULL
);

-- サンプルデータの挿入
INSERT INTO pos_dummy_data (product_code, product_name, price) VALUES
(1234567890, 'ソフラン', 300),
(2345678901, 'タイガー歯ブラシ', 200),
(3456789012, '四ツ谷サイダー', 160),
(4567890123, '福島産ほれん草', 188);

-- 取引テーブル
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_date DATETIME NOT NULL,
    cashier_code TEXT NOT NULL,
    store_code TEXT NOT NULL,
    pos_id TEXT NOT NULL,
    total_amount INTEGER NOT NULL
);

-- 取引明細テーブル
CREATE TABLE IF NOT EXISTS transaction_details (
    transaction_id INTEGER,
    detail_id INTEGER,
    item_id INTEGER,
    product_code INTEGER,
    product_name TEXT,
    price INTEGER,
    PRIMARY KEY (transaction_id, detail_id),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
); 