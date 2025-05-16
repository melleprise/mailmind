const express = require('express');
const { chromium } = require('playwright');
const fs = require('fs');
const axios = require('axios');

const app = express();
app.use(express.json());

// Headless-Modus über ENV-Variable steuerbar
const headless = process.env.VISIBLE_BROWSER !== 'true';

// Netzwerk-Logging Setup
const networkLog = [];

const userSessions = {};

async function getOrCreateUserSession(user_id, credentials) {
  if (userSessions[user_id] && userSessions[user_id].context && !userSessions[user_id].closed) {
    return userSessions[user_id];
  }
  if (userSessions[user_id]) {
    try { await userSessions[user_id].browser.close(); } catch {}
    delete userSessions[user_id];
  }
  const browser = await chromium.launch({ headless });
  const context = await browser.newContext();
  const page = await context.newPage();
  // Cookie-Banner IMMER zuerst schließen
  await page.goto('https://www.freelance.de/login.php');
  try {
    await page.waitForSelector('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll', { timeout: 10000 });
    const allowAllBtn = await page.$('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll');
    if (allowAllBtn) {
      await allowAllBtn.click();
      await page.waitForTimeout(1000);
    }
  } catch {}
  // WICHTIG: Immer auf das Verschwinden des Dialogs warten
  try {
    await page.waitForSelector('#CybotCookiebotDialog', { state: 'detached', timeout: 10000 });
  } catch {}
  // Jetzt Login durchführen
  await page.waitForSelector('#username', { timeout: 15000 });
  await page.fill('#username', credentials.username);
  await page.fill('#password', credentials.decrypted_password);
  await page.waitForTimeout(500);
  await page.click('#login');
  await page.waitForTimeout(2000);
  // Promo-Fenster
  try {
    await page.waitForSelector('#no_postlogin_show_pa_default', { timeout: 10000 });
    const infoCheckbox = await page.$('#no_postlogin_show_pa_default');
    if (infoCheckbox && !(await infoCheckbox.isChecked())) {
      await infoCheckbox.check();
      await page.waitForTimeout(500);
      await page.evaluate(async () => {
        const form = new URLSearchParams();
        form.append('action', 'set_cookie');
        form.append('k', 'no_postlogin_FL_-_Post_Login_315468');
        form.append('v', 'true');
        await fetch('/ajax.php', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
          },
          body: form.toString(),
          credentials: 'same-origin',
        });
      });
      await page.goto('https://www.freelance.de/myfreelance/index.php');
    }
  } catch {}
  await page.waitForTimeout(1000);
  userSessions[user_id] = { browser, context, page, closed: false };
  await persistSessionData(context);
  return userSessions[user_id];
}

// Login-Logik für freelance.de (angepasst, um loginUrl zu akzeptieren)
async function loginFreelanceDe(username, password, loginUrl, overviewUrl, detailUrl) {
  const browser = await chromium.launch({ headless });
  const page = await browser.newPage();

  console.log('[PlaywrightLogin] Playwright-Session gestartet');
  page.on('request', async (request) => {
    console.log('[Netzwerk-Log] Request:', request.method(), request.url());
    const entry = {
      type: 'request',
      url: request.url(),
      method: request.method(),
      headers: request.headers(),
      postData: request.postData(),
      timestamp: Date.now()
    };
    networkLog.push(entry);
  });
  page.on('response', async (response) => {
    const req = response.request();
    let body = null;
    try {
      body = await response.text();
    } catch {}
    const entry = {
      type: 'response',
      url: response.url(),
      status: response.status(),
      headers: response.headers(),
      request: {
        method: req.method(),
        headers: req.headers(),
        postData: req.postData()
      },
      body,
      timestamp: Date.now()
    };
    networkLog.push(entry);
    try {
      fs.writeFileSync('network_log.json', JSON.stringify(networkLog, null, 2));
    } catch (e) {
      console.error('[Netzwerk-Log] Fehler beim Schreiben von network_log.json:', e);
    }
  });
  page.on('requestfailed', request => {
    console.log('[Netzwerk-Log] Request FAILED:', request.method(), request.url(), request.failure());
  });

  try {
    console.log('[PlaywrightLogin] Gehe zu Login-Seite:', loginUrl || 'https://www.freelance.de/login.php');
    await page.goto(loginUrl || 'https://www.freelance.de/login.php');
    console.log('[PlaywrightLogin] Aktuelle URL nach goto:', page.url());
    // === Consent-Logik direkt nach Seitenaufruf ===
    console.log('[PlaywrightLogin] Warte auf "Alle Cookies erlauben"-Button...');
    await page.waitForSelector('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll', { timeout: 60000 });
    const allowAllBtn = await page.$('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll');
    if (allowAllBtn) {
      const btnBox = await allowAllBtn.boundingBox();
      if (btnBox) {
        await page.mouse.click(btnBox.x + btnBox.width / 2, btnBox.y + btnBox.height / 2);
        console.log('[PlaywrightLogin] "Alle Cookies erlauben"-Button per Maus-Klick ausgelöst!');
      } else {
        await allowAllBtn.click();
        console.log('[PlaywrightLogin] "Alle Cookies erlauben"-Button per .click() ausgelöst!');
      }
      await page.waitForTimeout(1500);
      // Prüfe Consent-Cookie
      const cookies = await page.context().cookies();
      const consentCookie = cookies.find(c => c.name.toLowerCase().includes('consent'));
      if (consentCookie) {
        console.log('[PlaywrightLogin] Consent-Cookie gesetzt:', consentCookie.name, consentCookie.value);
      } else {
        console.warn('[PlaywrightLogin] Consent-Cookie wurde nicht gesetzt!');
      }
    } else {
      console.warn('[PlaywrightLogin] "Alle Cookies erlauben"-Button nicht gefunden!');
    }
    // === Login erst nach Consent ===
    await page.waitForSelector('#username', { timeout: 15000 });
    console.log('[PlaywrightLogin] Fülle Login-Daten aus...');
    await page.fill('#username', username);
    await page.fill('#password', password);
    await page.waitForTimeout(1000);
    console.log('[PlaywrightLogin] Klicke Login-Button...');
    await page.click('#login');
    await page.waitForTimeout(2000);
    // === Warte explizit auf Promo-Fenster ===
    try {
      await page.waitForSelector('#no_postlogin_show_pa_default', { timeout: 15000 });
      // Checkbox gezielt aktivieren
      const infoCheckbox = await page.$('#no_postlogin_show_pa_default');
      if (infoCheckbox && !(await infoCheckbox.isChecked())) {
        await infoCheckbox.check();
        console.log('[PlaywrightLogin] Promo-Fenster: Checkbox aktiviert!');
        await page.waitForTimeout(500);
        // Sende echten API-Call wie im Browser
        const result = await page.evaluate(async () => {
          const form = new URLSearchParams();
          form.append('action', 'set_cookie');
          form.append('k', 'no_postlogin_FL_-_Post_Login_315468');
          form.append('v', 'true');
          const res = await fetch('/ajax.php', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
              'X-Requested-With': 'XMLHttpRequest',
            },
            body: form.toString(),
            credentials: 'same-origin',
          });
          return { status: res.status, ok: res.ok };
        });
        console.log('[PlaywrightLogin] Promo-Fenster: API-Call /ajax.php gesetzt:', result);
        // Navigiere direkt auf die Zielseite wie im echten Flow
        await page.goto('https://www.freelance.de/myfreelance/index.php');
        console.log('[PlaywrightLogin] Promo-Fenster: Direkt auf https://www.freelance.de/myfreelance/index.php navigiert!');
      }
      } catch (e) {
      console.log('[PlaywrightLogin] Promo-Fenster: Nicht gefunden oder Fehler:', e.message);
      }
    // === Warte bis Dialog verschwindet ===
    await page.waitForSelector('#CybotCookiebotDialog', { state: 'detached', timeout: 10000 }).catch(() => {});
    // === Speichere alle Cookies, LocalStorage und SessionStorage ===
    const cookies = await page.context().cookies();
    const localStorage = await page.evaluate(() => JSON.stringify(window.localStorage));
    const sessionStorage = await page.evaluate(() => JSON.stringify(window.sessionStorage));
    fs.writeFileSync('freelance_cookies.json', JSON.stringify({ cookies, localStorage, sessionStorage }, null, 2));
    // Zusätzlich ins Shared-Volume schreiben
    try {
      fs.writeFileSync('/cookies/freelance_cookies.json', JSON.stringify({ cookies, localStorage, sessionStorage }, null, 2));
      console.log('[PlaywrightLogin] Cookies auch nach /cookies/freelance_cookies.json geschrieben!');
    } catch (e) {
      console.warn('[PlaywrightLogin] Konnte Cookies nicht nach /cookies schreiben:', e.message);
    }
    console.log(`[PlaywrightLogin] Login für ${username} erfolgreich, ${cookies.length} Cookies erhalten (nach Übersicht+Detail).`);
    // Nach Login: Prüfe auf Wartung/Captcha/Fehlerseite
    await checkForUnexpectedPage(page, 'Login-Flow');
    // Browser schließen (nur bei Erfolg)
    await browser.close();
    return { success: true, cookies };
  } catch (e) {
    console.error(`[PlaywrightLogin] Fehler in loginFreelanceDe für ${username}:`, e);
    if (e.stack) console.error(e.stack);
    if (page) {
      await new Promise(() => {});
    }
    return { success: false, error: e.message };
  }
}

// Utility: Prüft auf Wartung, Captcha oder unerwartete Seite
async function checkForUnexpectedPage(page, phase = '') {
  const html = await page.content();
  if (/Wartungsarbeiten|maintenance|System ist derzeit wegen Wartungsarbeiten|Das System ist derzeit wegen Wartungsarbeiten|<div class="maintaince">|meta http-equiv="refresh"/i.test(html)) {
    fs.writeFileSync('unexpected_page_dump.html', html);
    console.error(`[PlaywrightLogin] Unerwartete Wartungsseite nach ${phase}. HTML-Dump gespeichert.`);
    throw new Error('Wartungsmodus erkannt – Seite nicht verfügbar.');
  }
  if (/captcha|verify you are human|bot protection/i.test(html)) {
    fs.writeFileSync('unexpected_page_dump.html', html);
    console.error(`[PlaywrightLogin] Captcha/Anti-Bot-Seite nach ${phase}. HTML-Dump gespeichert.`);
    throw new Error('Captcha/Anti-Bot erkannt – manueller Eingriff nötig.');
  }
  if (!/mein freelance|logout|projekt|dashboard|übersicht|welcome|willkommen/i.test(html)) {
    fs.writeFileSync('unexpected_page_dump.html', html);
    console.error(`[PlaywrightLogin] Unerwartete Seite nach ${phase}. HTML-Dump gespeichert.`);
    throw new Error('Unerwartete Seite nach Login – bitte prüfen.');
  }
}

// Provider-Login-Dispatcher
const loginProviders = {
  'freelance.de': loginFreelanceDe,
  // Weitere Provider können hier ergänzt werden
};

// Generischer Login-Endpunkt (bleibt für direkte Username/Passwort-Logins erhalten, falls benötigt)
app.post('/login/:provider', async (req, res) => {
  const { provider } = req.params;
  const { username, password, login_url } = req.body;
  if (!loginProviders[provider]) {
    return res.status(400).json({ success: false, error: 'Unbekannter Provider' });
  }
  if (!username || !password) {
    return res.status(400).json({ success: false, error: 'Username und Passwort erforderlich' });
  }
  console.log(`[PlaywrightLogin] Aufruf /login/${provider} für User ${username}`);
  const result = await loginProviders[provider](username, password, login_url);
  if (result.success) {
    res.json(result);
  } else {
    res.status(500).json(result);
  }
});

// Neuer Endpunkt für Login via User-ID
app.post('/login-by-user-id', async (req, res) => {
  const { user_id } = req.body;
  if (!user_id) {
    console.error('[PlaywrightLogin] /login-by-user-id: user_id fehlt.');
    return res.status(400).json({ success: false, error: 'user_id erforderlich' });
  }
  try {
    const backendUrl = `http://backend:8000/api/v1/freelance/credentials/${user_id}/`;
    console.log(`[PlaywrightLogin] /login-by-user-id: Rufe Backend für User-ID ${user_id} auf: ${backendUrl}`);
    const backendResponse = await axios.get(backendUrl, {
      headers: {
        'X-Playwright-Login-Service': 'true',
      },
      timeout: 20000
    });
    if (backendResponse.status !== 200 || !backendResponse.data) {
      console.error(`[PlaywrightLogin] /login-by-user-id: Fehlerhafte Antwort vom Backend (${backendResponse.status}) für User ${user_id}:`, backendResponse.data);
      return res.status(500).json({ success: false, error: 'Fehler beim Abrufen der Credentials vom Backend', details: backendResponse.data });
    }
    const credentials = backendResponse.data;
    const username = credentials.username;
    const decryptedPassword = credentials.decrypted_password; 
    const loginUrl = 'https://www.freelance.de/login.php'; // Immer echte Login-Seite verwenden
    const overviewUrl = credentials.link_2;
    // Beispiel-Detailseite: Nimm link_3 oder eine Dummy-URL, falls nicht vorhanden
    const detailUrl = credentials.link_3 || 'https://www.freelance.de/projekte/projekt-1207060-Cloud-Security-Expert-m-w-d';
    if (!username || !decryptedPassword || !loginUrl) {
      console.error(`[PlaywrightLogin] /login-by-user-id: Unvollständige Credentials vom Backend für User ${user_id}:`, credentials);
      return res.status(500).json({ success: false, error: 'Unvollständige Credentials vom Backend' });
    }
    console.log(`[PlaywrightLogin] /login-by-user-id: Starte Playwright Login für ${username} auf ${loginUrl}`);
    // Rufe loginFreelanceDe mit allen URLs auf
    const loginResult = await loginFreelanceDe(username, decryptedPassword, loginUrl, overviewUrl, detailUrl);
    if (loginResult.success) {
      console.log(`[PlaywrightLogin] /login-by-user-id: Login für User ${username} erfolgreich.`);
      res.json(loginResult);
    } else {
      console.error(`[PlaywrightLogin] /login-by-user-id: Playwright Login fehlgeschlagen für User ${username}:`, loginResult.error);
      res.status(500).json(loginResult);
    }
  } catch (error) {
    console.error(`[PlaywrightLogin] /login-by-user-id: Schwerer Fehler für User-ID ${user_id}: ${error.message}`, error.stack);
    if (error.response && error.response.data) {
        console.error('[PlaywrightLogin] /login-by-user-id: Fehlerdetails von Axios (Backend-Antwort):', error.response.data);
        return res.status(500).json({ success: false, error: 'Fehler bei der Kommunikation mit dem Backend', details: error.response.data });
    } else if (error.request) {
        console.error('[PlaywrightLogin] /login-by-user-id: Keine Antwort vom Backend erhalten.');
        return res.status(500).json({ success: false, error: 'Keine Antwort vom Backend erhalten beim Abruf der Credentials.' });
    }
    return res.status(500).json({ success: false, error: `Interner Fehler im Login-Service: ${error.message}` });
  }
});

// Neuer Endpunkt: Beliebige Seite nach Login holen (z.B. Listen- oder Detailseite)
app.post('/fetch-page-by-user-id', async (req, res) => {
  const { user_id, url } = req.body;
  if (!user_id || !url) {
    console.error('[PlaywrightLogin] /fetch-page-by-user-id: user_id oder url fehlt.');
    return res.status(400).json({ success: false, error: 'user_id und url erforderlich' });
  }
  try {
    const backendUrl = `http://backend:8000/api/v1/freelance/credentials/${user_id}/`;
    console.log(`[PlaywrightLogin] /fetch-page-by-user-id: Rufe Backend für User-ID ${user_id} auf: ${backendUrl}`);
    const backendResponse = await axios.get(backendUrl, {
      headers: {
        'X-Playwright-Login-Service': 'true',
      },
      timeout: 20000
    });
    if (backendResponse.status !== 200 || !backendResponse.data) {
      console.error(`[PlaywrightLogin] /fetch-page-by-user-id: Fehlerhafte Antwort vom Backend (${backendResponse.status}) für User ${user_id}:`, backendResponse.data);
      return res.status(500).json({ success: false, error: 'Fehler beim Abrufen der Credentials vom Backend', details: backendResponse.data });
    }
    const credentials = backendResponse.data;
    const username = credentials.username;
    const decryptedPassword = credentials.decrypted_password;
    const loginUrl = 'https://www.freelance.de/login.php'; // Immer echte Login-Seite verwenden
    const overviewUrl = credentials.link_2;
    if (!username || !decryptedPassword || !loginUrl) {
      console.error(`[PlaywrightLogin] /fetch-page-by-user-id: Unvollständige Credentials vom Backend für User ${user_id}:`, credentials);
      return res.status(500).json({ success: false, error: 'Unvollständige Credentials vom Backend' });
    }
    console.log(`[PlaywrightLogin] /fetch-page-by-user-id: Starte Playwright Login für ${username} auf ${loginUrl}`);
    // Login + Übersicht
    const browser = await chromium.launch({ headless });
    const page = await browser.newPage();
    try {
      await page.goto(loginUrl);
      await page.waitForSelector('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll', { timeout: 60000 });
      const allowAllBtn = await page.$('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll');
      if (allowAllBtn) {
        const btnBox = await allowAllBtn.boundingBox();
        if (btnBox) {
          await page.mouse.click(btnBox.x + btnBox.width / 2, btnBox.y + btnBox.height / 2);
        } else {
          await allowAllBtn.click();
        }
        await page.waitForTimeout(1500);
      }
      await page.waitForSelector('#username', { timeout: 15000 });
      await page.fill('#username', username);
      await page.fill('#password', decryptedPassword);
      await page.waitForTimeout(1000);
      await page.click('#login');
      await page.waitForTimeout(2000);
      // === Warte explizit auf Promo-Fenster ===
      try {
        await page.waitForSelector('#no_postlogin_show_pa_default', { timeout: 15000 });
        // Checkbox gezielt aktivieren
        const infoCheckbox = await page.$('#no_postlogin_show_pa_default');
        if (infoCheckbox && !(await infoCheckbox.isChecked())) {
          await infoCheckbox.check();
          console.log('[PlaywrightLogin] Promo-Fenster: Checkbox aktiviert!');
          await page.waitForTimeout(500);
          // Sende echten API-Call wie im Browser
          const result = await page.evaluate(async () => {
            const form = new URLSearchParams();
            form.append('action', 'set_cookie');
            form.append('k', 'no_postlogin_FL_-_Post_Login_315468');
            form.append('v', 'true');
            const res = await fetch('/ajax.php', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
              },
              body: form.toString(),
              credentials: 'same-origin',
            });
            return { status: res.status, ok: res.ok };
          });
          console.log('[PlaywrightLogin] Promo-Fenster: API-Call /ajax.php gesetzt:', result);
          // Navigiere direkt auf die Zielseite wie im echten Flow
          await page.goto('https://www.freelance.de/projekte/projekt-1158325-Ausbilder-m-w-d-fuer-den-Fachbereich-Asbest');
          console.log('[PlaywrightLogin] Promo-Fenster: Direkt auf https://www.freelance.de/projekte/projekt-1158325-Ausbilder-m-w-d-fuer-den-Fachbereich-Asbest navigiert!');
        }
      } catch (e) {
        console.log('[PlaywrightLogin] Promo-Fenster: Nicht gefunden oder Fehler:', e.message);
      }
      // === Warte auf vollständiges Laden der Post-Login-Seite ===
      await page.waitForTimeout(9999999);
      await page.context().addCookies([
        {
          name: 'no_postlogin_FL_-_Post_Login_315468',
          value: 'true',
          domain: 'www.freelance.de',
          path: '/',
          httpOnly: false,
          secure: false,
          sameSite: 'Lax'
        }
      ]);
      if (overviewUrl) {
        await page.goto(overviewUrl);
        await page.waitForTimeout(1000);
      }
      // Jetzt die gewünschte Seite laden (z.B. Listen- oder Detailseite)
      await page.goto(url);
      await page.waitForTimeout(1000);
      const html = await page.content();
      res.json({ success: true, html });
      // Browser schließen (nur bei Erfolg)
      await browser.close();
    } catch (e) {
      console.error(`[PlaywrightLogin] Fehler in /fetch-page-by-user-id für User ${username}:`, e);
      if (e.stack) console.error(e.stack);
      res.status(500).json({ success: false, error: e.message });
    }
  } catch (error) {
    console.error(`[PlaywrightLogin] /fetch-page-by-user-id: Schwerer Fehler für User-ID ${user_id}: ${error.message}`, error.stack);
    if (error.response && error.response.data) {
        console.error('[PlaywrightLogin] /fetch-page-by-user-id: Fehlerdetails von Axios (Backend-Antwort):', error.response.data);
        return res.status(500).json({ success: false, error: 'Fehler bei der Kommunikation mit dem Backend', details: error.response.data });
    } else if (error.request) {
        console.error('[PlaywrightLogin] /fetch-page-by-user-id: Keine Antwort vom Backend erhalten.');
        return res.status(500).json({ success: false, error: 'Keine Antwort vom Backend erhalten beim Abruf der Credentials.' });
    }
    return res.status(500).json({ success: false, error: `Interner Fehler im Login-Service: ${error.message}` });
  }
});

// Endpunkt: Geschützte Seite im User-Context laden
app.post('/fetch-protected-page', async (req, res) => {
  const { user_id, url } = req.body;
  if (!user_id || !url) {
    return res.status(400).json({ success: false, error: 'user_id und url erforderlich' });
  }
  try {
    // Credentials holen
    const backendUrl = `http://backend:8000/api/v1/freelance/credentials/${user_id}/`;
    const backendResponse = await axios.get(backendUrl, {
      headers: { 'X-Playwright-Login-Service': 'true' },
      timeout: 20000
    });
    if (backendResponse.status !== 200 || !backendResponse.data) {
      return res.status(500).json({ success: false, error: 'Fehler beim Abrufen der Credentials vom Backend', details: backendResponse.data });
    }
    const credentials = backendResponse.data;
    // Session holen oder anlegen
    const session = await getOrCreateUserSession(user_id, credentials);
    const page = session.page;
    await page.goto(url);
    await page.waitForTimeout(1000);
    const html = await page.content();
    await persistSessionData(session.context);
    return res.json({ success: true, html });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

// Neuer Endpunkt: Mehrere geschützte Seiten mit einer Session laden
app.post('/fetch-multiple-pages-by-user-id', async (req, res) => {
  const { user_id, urls } = req.body;
  console.log('[BATCH] Aufruf mit user_id:', user_id, 'Anzahl URLs:', urls && urls.length);
  if (!user_id || !Array.isArray(urls) || urls.length === 0) {
    console.log('[BATCH] Fehler: user_id und urls[] erforderlich');
    return res.status(400).json({ success: false, error: 'user_id und urls[] erforderlich' });
  }
  try {
    // Credentials holen
    const backendUrl = `http://backend:8000/api/v1/freelance/credentials/${user_id}/`;
    console.log('[BATCH] Hole Credentials von', backendUrl);
    const backendResponse = await axios.get(backendUrl, {
      headers: { 'X-Playwright-Login-Service': 'true' },
      timeout: 20000
    });
    if (backendResponse.status !== 200 || !backendResponse.data) {
      console.log('[BATCH] Fehler beim Abrufen der Credentials:', backendResponse.status, backendResponse.data);
      return res.status(500).json({ success: false, error: 'Fehler beim Abrufen der Credentials vom Backend', details: backendResponse.data });
    }
    const credentials = backendResponse.data;
    const username = credentials.username;
    const decryptedPassword = credentials.decrypted_password;
    const loginUrl = 'https://www.freelance.de/login.php'; // Immer echte Login-Seite verwenden
    if (!username || !decryptedPassword || !loginUrl) {
      console.log('[BATCH] Unvollständige Credentials:', credentials);
      return res.status(500).json({ success: false, error: 'Unvollständige Credentials vom Backend' });
    }
    // Login-Session aufbauen
    const browser = await chromium.launch({ headless });
    const page = await browser.newPage();
    try {
      console.log('[BATCH] Gehe zu Login-URL:', loginUrl);
      await page.goto(loginUrl);
      console.log('[BATCH] Nach Login-URL:', await page.url());
      try {
        console.log('[BATCH] Warte auf Cookie-Banner...');
        await page.waitForSelector('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll', { timeout: 60000 });
        const allowAllBtn = await page.$('#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll');
        if (allowAllBtn) {
          const btnBox = await allowAllBtn.boundingBox();
          if (btnBox) {
            await page.mouse.click(btnBox.x + btnBox.width / 2, btnBox.y + btnBox.height / 2);
          } else {
            await allowAllBtn.click();
          }
          await page.waitForTimeout(1500);
        }
      } catch (e) {
        console.log('[BATCH] Kein Cookie-Banner gefunden oder Fehler:', e.message);
      }
      console.log('[BATCH] Warte auf Login-Formular...');
      try {
        await page.waitForSelector('#username', { timeout: 15000 });
      } catch (e) {
        const html = await page.content();
        console.log('[BATCH] Timeout beim Warten auf #username! Aktuelle URL:', await page.url());
        console.log('[BATCH] HTML-Ausschnitt:', html.slice(0, 1000));
        throw e;
      }
      await page.fill('#username', username);
      await page.fill('#password', decryptedPassword);
      await page.waitForTimeout(1000);
      await page.click('#login');
      await page.waitForTimeout(2000);
      // Promo-Fenster-Bypass
      try {
        await page.waitForSelector('#no_postlogin_show_pa_default', { timeout: 15000 });
        const infoCheckbox = await page.$('#no_postlogin_show_pa_default');
        if (infoCheckbox && !(await infoCheckbox.isChecked())) {
          await infoCheckbox.check();
          await page.waitForTimeout(500);
          await page.evaluate(async () => {
            const form = new URLSearchParams();
            form.append('action', 'set_cookie');
            form.append('k', 'no_postlogin_FL_-_Post_Login_315468');
            form.append('v', 'true');
            await fetch('/ajax.php', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'X-Requested-With': 'XMLHttpRequest',
              },
              body: form.toString(),
              credentials: 'same-origin',
            });
          });
          await page.goto('https://www.freelance.de/myfreelance/index.php');
        }
      } catch (e) {
        console.log('[BATCH] Kein Promo-Fenster gefunden oder Fehler:', e.message);
      }
      await page.waitForSelector('#CybotCookiebotDialog', { state: 'detached', timeout: 10000 }).catch(() => {});
      // Jetzt alle URLs sequenziell laden
      const results = [];
      for (const url of urls) {
        try {
          console.log('[BATCH] Lade Detailseite:', url);
          await page.goto(url);
          await page.waitForTimeout(1000);
          const html = await page.content();
          results.push({ url, html, success: true });
        } catch (e) {
          console.log('[BATCH] Fehler beim Laden von', url, ':', e.message);
          results.push({ url, html: '', success: false, error: e.message });
        }
      }
      await browser.close();
      return res.json({ success: true, results });
    } catch (e) {
      await browser.close();
      console.log('[BATCH] Fehler im Batch-Login:', e.message);
      return res.status(500).json({ success: false, error: e.message });
    }
  } catch (error) {
    console.log('[BATCH] Schwerer Fehler:', error.message);
    return res.status(500).json({ success: false, error: error.message });
  }
});

// Hilfsfunktion zum Speichern der Session-Daten
async function persistSessionData(context) {
  try {
    const cookies = await context.cookies();
    const storageState = await context.storageState();
    const fs = require('fs');
    fs.writeFileSync('/cookies/freelance.json', JSON.stringify(cookies, null, 2));
    fs.writeFileSync('/cookies/freelance_storage.json', JSON.stringify(storageState, null, 2));
    console.log('[SESSION] Cookies und StorageState gespeichert.');
  } catch (err) {
    console.log('[SESSION] Fehler beim Speichern der Session-Daten:', err);
  }
}

// Endpunkt: Komplette Crawl-Session mit persistenter Session
app.post('/crawl-session', async (req, res) => {
  const { user_id, overview_urls, detail_urls } = req.body;
  if (!user_id || !Array.isArray(overview_urls) || !Array.isArray(detail_urls)) {
    return res.status(400).json({ success: false, error: 'user_id, overview_urls[] und detail_urls[] erforderlich' });
  }
  try {
    // Credentials holen
    const backendUrl = `http://backend:8000/api/v1/freelance/credentials/${user_id}/`;
    const backendResponse = await axios.get(backendUrl, {
      headers: { 'X-Playwright-Login-Service': 'true' },
      timeout: 20000
    });
    if (backendResponse.status !== 200 || !backendResponse.data) {
      return res.status(500).json({ success: false, error: 'Fehler beim Abrufen der Credentials vom Backend', details: backendResponse.data });
    }
    const credentials = backendResponse.data;
    // Session holen oder anlegen
    const session = await getOrCreateUserSession(user_id, credentials);
    const page = session.page;
    // 1. Übersichtseiten laden
    const overview_results = [];
    for (const url of overview_urls) {
      try {
        await page.goto(url);
        await page.waitForTimeout(1000);
        const html = await page.content();
        overview_results.push({ url, html, success: true });
      } catch (e) {
        overview_results.push({ url, html: '', success: false, error: e.message });
      }
    }
    // 2. Detailseiten laden
    const detail_results = [];
    for (const url of detail_urls) {
      try {
        await page.goto(url);
        await page.waitForTimeout(1000);
        const html = await page.content();
        detail_results.push({ url, html, success: true });
      } catch (e) {
        detail_results.push({ url, html: '', success: false, error: e.message });
      }
    }
    await persistSessionData(session.context);
    return res.json({ success: true, overview_results, detail_results });
  } catch (e) {
    return res.status(500).json({ success: false, error: e.message });
  }
});

// Endpunkt: Session explizit schließen
app.post('/close-session', async (req, res) => {
  const { user_id } = req.body;
  if (!user_id) {
    return res.status(400).json({ success: false, error: 'user_id erforderlich' });
  }
  if (userSessions[user_id]) {
    try {
      await userSessions[user_id].browser.close();
      userSessions[user_id].closed = true;
      delete userSessions[user_id];
      return res.json({ success: true });
    } catch (e) {
      return res.status(500).json({ success: false, error: e.message });
    }
  } else {
    return res.status(404).json({ success: false, error: 'Session nicht gefunden' });
  }
});

// Globale Fehler-Handler
process.on('uncaughtException', (err) => {
  console.error('[Global Error] uncaughtException:', err);
});
process.on('unhandledRejection', (reason, promise) => {
  console.error('[Global Error] unhandledRejection:', reason);
});

app.listen(3000, () => console.log('Playwright Login Service listening on 3000')); 