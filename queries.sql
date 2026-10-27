.headers on
.mode column
.print '1. Товары дороже 10000 рублей'
SELECT name, price FROM Products WHERE price > 10000;
.print '2. Женская обувь'
SELECT p.name FROM Products p JOIN Categories c ON c.id=p.category_id
WHERE c.name='Женская обувь';
.print '3. Количество моделей по производителям'
SELECT m.name, COUNT(p.id) AS models FROM Manufacturers m
LEFT JOIN Products p ON p.manufacturer_id=m.id GROUP BY m.id;
.print '4. Средняя цена по категориям'
SELECT c.name, ROUND(AVG(p.price), 2) AS average_price FROM Categories c
LEFT JOIN Products p ON p.category_id=c.id GROUP BY c.id;
.print '5. Суммарный остаток меньше 3'
SELECT p.name, COALESCE(SUM(s.quantity), 0) AS quantity FROM Products p
LEFT JOIN Stock s ON s.product_id=p.id GROUP BY p.id HAVING quantity < 3;
.print '6. Без заказов в прошлом календарном месяце, скидка 25 процентов'
SELECT p.name, p.price, p.price * 0.75 AS price_final FROM Products p
WHERE NOT EXISTS (
 SELECT 1 FROM OrderItems i JOIN Orders o ON o.id=i.order_id
 WHERE i.product_id=p.id
 AND o.order_date >= date('now','localtime','start of month','-1 month')
 AND o.order_date < date('now','localtime','start of month')
);
.print '7. Пять самых дорогих заказов'
SELECT o.id, u.full_name, SUM(i.quantity*i.unit_price) AS total
FROM Orders o JOIN Users u ON u.id=o.user_id
JOIN OrderItems i ON i.order_id=o.id GROUP BY o.id
ORDER BY total DESC, o.id LIMIT 5;
.print '8. Размеры в наличии, которые никогда не заказывались'
SELECT s.value FROM Sizes s
WHERE EXISTS (SELECT 1 FROM Stock st WHERE st.size_id=s.id AND st.quantity>0)
AND NOT EXISTS (SELECT 1 FROM OrderItems i WHERE i.size_id=s.id)
ORDER BY s.value;
