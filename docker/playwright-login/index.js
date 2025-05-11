const express = require('express');
const { chromium } = require('playwright');
const fs = require('fs');
const axios = require('axios');

const app = express();
app.use(express.json());

// Login-Logik für freelance.de (angepasst, um loginUrl zu akzeptieren)
async function loginFreelanceDe(username, password, loginUrl, overviewUrl, detailUrl) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
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
    // === NEU: Warte auf vollständiges Laden der Post-Login-Seite ===
    await page.waitForLoadState('networkidle');
    console.log('[PlaywrightLogin] Aktuelle URL nach Login:', page.url());
    // === Promo-Cookie setzen ===
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
    console.log('[PlaywrightLogin] Promo-Cookie gesetzt!');
    // === NEU: Gehe zuerst auf die Übersichtsseite, dann auf die Detailseite ===
    if (overviewUrl) {
      console.log('[PlaywrightLogin] Gehe nach Login zu Übersichtsseite:', overviewUrl);
      await page.goto(overviewUrl);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      console.log('[PlaywrightLogin] Aktuelle URL nach Übersicht:', page.url());
    }
    if (detailUrl) {
      console.log('[PlaywrightLogin] Gehe nach Übersicht explizit zu Detailseite:', detailUrl);
      await page.goto(detailUrl);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      console.log('[PlaywrightLogin] Aktuelle URL nach erneutem Detailseiten-Aufruf:', page.url());
      // === Consent-Request nach Detailseite ===
      console.log('[PlaywrightLogin] Sende Cookiebot-Consent-Request...');
      const cbid = 'cb99fb9b-c373-4fad-aaf2-e16b602e9875';
      const userAgent = await page.evaluate(() => navigator.userAgent);
      const referer = detailUrl;
      const url = `https://consent.cookiebot.com/logconsent.ashx?action=accept&nocache=${Date.now()}&dnt=false&method=strict&clp=true&cls=true&clm=true&cbid=${cbid}&cbt=leveloptin&hasdata=true&usercountry=DE&referer=${encodeURIComponent(referer)}&rc=false`;
      try {
        const resp = await page.request.get(url, { headers: {
          'authority': 'consent.cookiebot.com',
          'accept': '*/*',
          'accept-language': 'de-DE,de;q=0.9,en;q=0.8',
          'referer': referer,
          'sec-ch-ua': '"Not.A/Brand";v="99", "Chromium";v="136"',
          'sec-ch-ua-mobile': '?0',
          'sec-ch-ua-platform': '"Linux"',
          'sec-fetch-dest': 'script',
          'sec-fetch-mode': 'no-cors',
          'sec-fetch-site': 'cross-site',
          'user-agent': userAgent
        }});
        console.log('[PlaywrightLogin] Consent-Request Status:', resp.status());
      } catch (e) {
        console.warn('[PlaywrightLogin] Consent-Request fehlgeschlagen:', e);
      }
      // Dialog per JS entfernen
      await page.evaluate(() => {
        const dialog = document.getElementById('CybotCookiebotDialog');
        if (dialog) dialog.remove();
      });
      console.log('[PlaywrightLogin] Cookiebot-Dialog entfernt (nach Consent-Request).');
    }
    // === Cookies speichern ===
    const cookies = await page.context().cookies();
    fs.writeFileSync('freelance_cookies.json', JSON.stringify(cookies, null, 2));
    console.log('[PlaywrightLogin] Cookies gespeichert in freelance_cookies.json');
    console.log(`[PlaywrightLogin] Login für ${username} erfolgreich, ${cookies.length} Cookies erhalten (nach Übersicht+Detail).`);
    return { success: true, cookies };
  } catch (e) {
    console.error(`[PlaywrightLogin] Fehler in loginFreelanceDe für ${username}:`, e);
    if (e.stack) console.error(e.stack);
    return { success: false, error: e.message };
  } finally {
    await browser.close();
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
    const loginUrl = credentials.link_1;
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
    const loginUrl = credentials.link_1;
    const overviewUrl = credentials.link_2;
    if (!username || !decryptedPassword || !loginUrl) {
      console.error(`[PlaywrightLogin] /fetch-page-by-user-id: Unvollständige Credentials vom Backend für User ${user_id}:`, credentials);
      return res.status(500).json({ success: false, error: 'Unvollständige Credentials vom Backend' });
    }
    console.log(`[PlaywrightLogin] /fetch-page-by-user-id: Starte Playwright Login für ${username} auf ${loginUrl}`);
    // Login + Übersicht
    const browser = await chromium.launch({ headless: true });
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
      await page.waitForLoadState('networkidle');
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
        await page.waitForLoadState('networkidle');
        await page.waitForTimeout(1000);
      }
      // Jetzt die gewünschte Seite laden (z.B. Listen- oder Detailseite)
      await page.goto(url);
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(1000);
      const html = await page.content();
      res.json({ success: true, html });
    } catch (e) {
      console.error(`[PlaywrightLogin] Fehler in /fetch-page-by-user-id für User ${username}:`, e);
      if (e.stack) console.error(e.stack);
      res.status(500).json({ success: false, error: e.message });
    } finally {
      await browser.close();
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

app.listen(3000, () => console.log('Playwright Login Service listening on 3000')); 