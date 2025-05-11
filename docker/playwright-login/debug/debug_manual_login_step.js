const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const username = process.env.FREELANCE_USERNAME || 'melleprise@gmail.com';
  const password = process.env.FREELANCE_PASSWORD || 'h@x@jPLsQtbPk2J';
  const loginUrl = process.env.FREELANCE_LOGIN_URL || 'https://www.freelance.de/login.php';

  if (!username || !password) {
    console.error('Bitte FREELANCE_USERNAME und FREELANCE_PASSWORD als ENV setzen!');
    process.exit(1);
  }

  const browser = await chromium.launch({ headless: false, slowMo: 100 });
  const page = await browser.newPage();
  try {
    console.log('Gehe zu Login-Seite:', loginUrl);
    await page.goto(loginUrl);
    console.log('Aktuelle URL nach goto:', page.url());
    // === Consent-Logik direkt nach Seitenaufruf ===
    console.log('Warte auf "Alle Cookies erlauben"-Button...');
    await page.waitForSelector('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll', { timeout: 60000 });
    const allowAllBtn = await page.$('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll');
    if (allowAllBtn) {
      const btnBox = await allowAllBtn.boundingBox();
      if (btnBox) {
        await page.mouse.click(btnBox.x + btnBox.width / 2, btnBox.y + btnBox.height / 2);
        console.log('"Alle Cookies erlauben"-Button per Maus-Klick ausgelöst!');
      } else {
        await allowAllBtn.click();
        console.log('"Alle Cookies erlauben"-Button per .click() ausgelöst!');
      }
      await page.waitForTimeout(1500);
      // Prüfe Consent-Cookie
      const cookies = await page.context().cookies();
      const consentCookie = cookies.find(c => c.name.toLowerCase().includes('consent'));
      if (consentCookie) {
        console.log('Consent-Cookie gesetzt:', consentCookie.name, consentCookie.value);
      } else {
        console.warn('Consent-Cookie wurde nicht gesetzt!');
      }
    } else {
      console.warn('"Alle Cookies erlauben"-Button nicht gefunden!');
    }
    // === Login erst nach Consent ===
    await page.waitForSelector('#username', { timeout: 15000 });
    console.log('Fülle Login-Daten aus...');
    await page.fill('#username', username);
    await page.fill('#password', password);
    await page.waitForTimeout(1000);
    console.log('Klicke Login-Button...');
    await page.click('#login');
    await page.waitForTimeout(2000); // 2s warten, damit Seite reagieren kann
    console.log('Aktuelle URL nach Login:', page.url());
    const screenshotPath = 'after_login_step.png';
    await page.screenshot({ path: screenshotPath });
    console.log('Screenshot nach Login gespeichert:', screenshotPath);
    // Browser bleibt offen für manuelle Analyse
    console.log('Browser bleibt offen. Drücke STRG+C zum Beenden.');
    await new Promise(() => {}); // Nie auflösen, hält das Skript offen
  } catch (e) {
    console.error('Fehler im Debug-Login-Step:', e);
    if (e.stack) console.error(e.stack);
  } finally {
    // await browser.close(); // absichtlich auskommentiert
  }
})(); 