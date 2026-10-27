PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS Categories (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS Manufacturers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS Sizes (
    id INTEGER PRIMARY KEY,
    value INTEGER NOT NULL UNIQUE CHECK(value BETWEEN 20 AND 50)
);
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY,
    login TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('Клиент', 'Менеджер', 'Администратор'))
);
CREATE TABLE IF NOT EXISTS Products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL REFERENCES Categories(id),
    manufacturer_id INTEGER NOT NULL REFERENCES Manufacturers(id),
    composition TEXT NOT NULL,
    price INTEGER NOT NULL CHECK(price > 0), -- целые рубли
    UNIQUE(name, manufacturer_id)
);
CREATE TABLE IF NOT EXISTS Stock (
    product_id INTEGER NOT NULL REFERENCES Products(id) ON DELETE CASCADE,
    size_id INTEGER NOT NULL REFERENCES Sizes(id),
    quantity INTEGER NOT NULL CHECK(quantity >= 0),
    PRIMARY KEY(product_id, size_id)
);
CREATE TABLE IF NOT EXISTS Orders (
    id INTEGER PRIMARY KEY,
    order_date TEXT NOT NULL CHECK(length(order_date) = 10 AND date(order_date) IS NOT NULL AND date(order_date) = order_date),
    user_id INTEGER NOT NULL REFERENCES Users(id)
);
CREATE TABLE IF NOT EXISTS OrderItems (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES Orders(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL,
    size_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    unit_price INTEGER NOT NULL CHECK(unit_price > 0),
    FOREIGN KEY(product_id, size_id) REFERENCES Stock(product_id, size_id),
    UNIQUE(order_id, product_id, size_id)
);
CREATE INDEX IF NOT EXISTS idx_products_category ON Products(category_id);
CREATE INDEX IF NOT EXISTS idx_products_manufacturer ON Products(manufacturer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date ON Orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_user ON Orders(user_id);
CREATE INDEX IF NOT EXISTS idx_items_product ON OrderItems(product_id, size_id);
