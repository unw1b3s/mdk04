const state = { user: null, products: [], cart: [], filters: {}, order: null, deleted: [] };
const $ = (selector) => document.querySelector(selector);
const money = (value) => value.toLocaleString('ru-RU') + ' ₽';
const escapeHtml = (value) => String(value).replace(/[&<>"']/g, (char) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
}[char]));

async function api(url, data) {
    const options = data === undefined ? {} : {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    };
    const response = await fetch(url, options);
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Ошибка запроса');
    return result;
}

function header() {
    const user = state.user;
    $('#account').innerHTML = user
        ? `<span>${escapeHtml(user.full_name)} · ${escapeHtml(user.role)}</span><button id="logout">Выйти</button>`
        : '<button id="login">Войти</button>';
    $('#account').insertAdjacentHTML('beforeend', `<button id="cart">Корзина (${state.cart.length})</button>`);
    $('#orders-button').hidden = !user || !['Менеджер', 'Администратор'].includes(user.role);
    if (user) $('#logout').addEventListener('click', async () => {
        try {
            await api('/api/logout', {});
            state.user = null;
            header();
            await catalog();
        } catch (error) { $('#message').textContent = error.message; }
    });
    else $('#login').addEventListener('click', () => {
        $('#login-error').textContent = '';
        $('#login-dialog').showModal();
    });
    $('#cart').addEventListener('click', () => {
        $('#message').textContent = 'Корзина пуста.';
    });
}

async function catalog() {
    $('#message').textContent = '';
    state.products = await api('/api/products');
    $('#content').innerHTML = '<h2>Товары</h2><div class="products">' + state.products.map((p) =>
        `<article><h2>${escapeHtml(p.name)}</h2><p>${escapeHtml(p.category)}</p>
        <p>Производитель: ${escapeHtml(p.manufacturer)}</p><p>Состав: ${escapeHtml(p.composition)}</p>
        <p>Остаток: ${p.quantity} пар</p><strong>${money(p.price)}</strong></article>`
    ).join('') + '</div>';
    if (!state.products.length) $('#content').textContent = 'Товаров пока нет.';
}

async function orders() {
    $('#message').textContent = '';
    const rows = await api('/api/orders');
    $('#content').innerHTML = '<h2>Заказы</h2><div class="table-wrap"><table><thead><tr><th>№</th><th>Дата</th><th>ФИО клиента</th><th></th></tr></thead><tbody>' +
        rows.map((o) => `<tr><td>${o.id}</td><td>${escapeHtml(o.order_date)}</td><td>${escapeHtml(o.full_name)}</td><td><button data-order="${o.id}">Открыть</button></td></tr>`).join('') + '</tbody></table></div>';
    if (!rows.length) $('#content').insertAdjacentHTML('beforeend', '<p>Заказов пока нет.</p>');
    document.querySelectorAll('[data-order]').forEach((button) => button.addEventListener('click', async () => {
        try {
            state.order = await api('/api/order?id=' + button.dataset.order);
            state.deleted = [];
            $('#order-title').textContent = 'Заказ № ' + state.order.id;
            $('#order-date').value = state.order.order_date;
            $('#order-error').textContent = '';
            const admin = state.user.role === 'Администратор';
            $('#order-date').disabled = !admin;
            $('#save-order').hidden = !admin;
            renderItems();
            $('#order-dialog').showModal();
        } catch (error) { $('#message').textContent = error.message; }
    }));
}

function renderItems() {
    const items = state.order.items.filter((item) => !state.deleted.includes(item.id));
    const admin = state.user.role === 'Администратор';
    $('#order-items').innerHTML = items.map((i) => `<tr><td>${escapeHtml(i.name)}</td><td>${i.size}</td><td>${i.quantity}</td><td>${money(i.unit_price)}</td><td>${money(i.total)}</td><td>${admin ? `<button type="button" data-delete="${i.id}">Удалить</button>` : ''}</td></tr>`).join('');
    $('#order-total').textContent = 'Итого: ' + money(items.reduce((total, i) => total + i.total, 0));
    document.querySelectorAll('[data-delete]').forEach((button) => button.addEventListener('click', () => {
        state.deleted.push(Number(button.dataset.delete));
        renderItems();
    }));
}

$('#login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    try {
        const login = new FormData(event.target).get('login').trim();
        if (!login) throw new Error('Введите логин.');
        state.user = await api('/api/login?login=' + encodeURIComponent(login));
        header();
        $('#login-dialog').close();
        $('#message').textContent = '';
    } catch (error) { $('#login-error').textContent = error.message; }
});
$('#order-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const button = $('#save-order');
    button.disabled = true;
    try {
        await api('/api/order/update', {
            id: state.order.id, order_date: $('#order-date').value,
            deleted_item_ids: state.deleted
        });
        $('#order-dialog').close();
        await orders();
        $('#message').textContent = 'Изменения сохранены. Удалённые позиции возвращены на склад.';
    } catch (error) { $('#order-error').textContent = error.message; }
    finally { button.disabled = false; }
});
$('#login-close').addEventListener('click', () => $('#login-dialog').close());
$('#order-close').addEventListener('click', () => $('#order-dialog').close());
$('#catalog-button').addEventListener('click', () => catalog().catch((e) => { $('#message').textContent = e.message; }));
$('#orders-button').addEventListener('click', () => orders().catch((e) => { $('#message').textContent = e.message; }));
header();
catalog().catch((error) => { $('#message').textContent = error.message; });
