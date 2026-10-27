// Не требуется для запуска приложения. Проверка интерфейса через Playwright.
const { chromium } = require('playwright');
const fs = require('fs');
const assert = require('assert/strict');
const path = require('path');
(async () => {
    const root = path.resolve(__dirname, '..');
    const db = path.join(root, 'shop.db');
    const original = fs.readFileSync(db);
    const browser = await chromium.launch({ headless: true, executablePath: process.env.BROWSER_PATH || chromium.executablePath() });
    const page = await browser.newPage({ viewport: { width: 1280, height: 850 } });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    const evidence = name => path.join(root, 'reports/evidence', name + '.png');
    const login = async name => {
        await page.getByRole('button', { name: 'Войти', exact: true }).click();
        await page.getByLabel('Логин', { exact: true }).fill(name);
        await page.locator('#login-form').getByRole('button', { name: 'Войти', exact: true }).click();
        await page.waitForFunction(() => !document.querySelector('#login-dialog').open);
    };
    try {
        await page.goto(process.env.BASE_URL || 'http://127.0.0.1:8001');
        await page.locator('article').first().waitFor();
        assert.equal(await page.locator('article').count(), 4);
        await page.screenshot({ path: evidence('01_catalog'), fullPage: true });
        console.log('PASS: 4 товара, загруженные через fetch; screenshot 01_catalog.png');
        for (const name of ['client1', 'client2', 'client3', 'manager', 'admin']) {
            await login(name);
            const staff = ['manager', 'admin'].includes(name);
            assert.equal(await page.locator('#orders-button').isVisible(), staff);
            if (staff) {
                await page.locator('#orders-button').click();
                await page.getByRole('button', { name: 'Открыть' }).first().waitFor();
                if (name === 'manager') {
                    await page.screenshot({ path: evidence('02_orders'), fullPage: true });
                }
                await page.getByRole('button', { name: 'Открыть' }).first().click();
                await page.locator('#order-dialog').waitFor();
                assert.equal(await page.locator('#order-date').isEnabled(), name === 'admin');
                assert.equal(await page.locator('#save-order').isVisible(), name === 'admin');
                assert.match(await page.locator('#order-total').innerText(), /44\s?000/);
                if (name === 'admin') {
                    await page.screenshot({ path: evidence('03_admin_before'), fullPage: true });
                    await page.locator('#order-date').fill('2026-10-20');
                    await page.getByRole('button', { name: 'Удалить', exact: true }).first().click();
                    await page.getByRole('button', { name: 'Сохранить изменения' }).click();
                    await page.waitForFunction(() => !document.querySelector('#order-dialog').open);
                    await page.getByRole('button', { name: 'Открыть' }).first().click();
                    await page.locator('#order-dialog').waitFor();
                    assert.equal(await page.locator('#order-date').inputValue(), '2026-10-20');
                    assert.equal(await page.locator('#order-items tr').count(), 1);
                    assert.match(await page.locator('#order-total').innerText(), /32\s?000/);
                    await page.screenshot({ path: evidence('04_admin_after'), fullPage: true });
                    console.log('PASS: сохранение даты и удаление позиции; screenshots 03, 04');
                }
                await page.getByRole('button', { name: 'Закрыть', exact: true }).click();
            }
            console.log('PASS: вход ' + name + ', видимость кнопок по роли');
            await page.getByRole('button', { name: 'Выйти', exact: true }).click();
            await page.getByRole('button', { name: 'Войти', exact: true }).waitFor();
        }
        await page.getByRole('button', { name: 'Корзина (0)', exact: true }).click();
        assert.match(await page.locator('#message').innerText(), /Корзина пуста/);
        assert.deepEqual(errors, []);
        console.log('PASS: корзина каркаса; ошибок Console/pageerror: 0');
        await page.setViewportSize({ width: 390, height: 844 });
        await page.screenshot({ path: evidence('05_mobile'), fullPage: true });
        assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
        console.log('PASS: мобильная ширина 390px без горизонтального переполнения');
    } finally {
        await browser.close();
        fs.writeFileSync(db, original);
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
