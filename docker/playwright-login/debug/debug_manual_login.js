const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  const username = process.env.FREELANCE_USERNAME || 'melleprise@gmail.com';
  const password = process.env.FREELANCE_PASSWORD || 'h@x@jPLsQtbPk2J';
  const loginUrl = process.env.FREELANCE_LOGIN_URL || 'https://www.freelance.de/login.php';
  const overviewUrl = process.env.FREELANCE_OVERVIEW_URL || 'https://www.freelance.de/projekte?city=19107&county=53&pageSize=100';
  const detailUrl = process.env.FREELANCE_DETAIL_URL || 'https://www.freelance.de/projekte/projekt-1207060-Cloud-Security-Expert-m-w-d';

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
    console.log('Prüfe auf Cookiebot-Button vor Login...');
    const cookieBtn = await page.$('#CybotCookiebotDialogBodyButtonAccept');
    if (cookieBtn) {
      console.log('Cookiebot-Button gefunden, klicke...');
      await cookieBtn.click();
      await page.waitForTimeout(1500);
      const cookies = await page.context().cookies();
      const consentCookie = cookies.find(c => c.name.includes('CookieConsent') || c.name.includes('Cookiebot'));
      if (!consentCookie) {
        console.warn('Consent-Cookie wurde nicht gesetzt!');
      } else {
        console.log('Consent-Cookie gesetzt:', consentCookie.name, consentCookie.value);
      }
    } else {
      console.log('Kein Cookiebot-Button gefunden vor Login.');
    }
    await page.evaluate(() => {
      const dialog = document.getElementById('CybotCookiebotDialog');
      if (dialog) dialog.remove();
    });
    console.log('Klicke Login-Button...');
    await page.click('#login');
    await page.waitForTimeout(2000); // 2s warten, damit Seite reagieren kann
    console.log('Aktuelle URL nach Login:', page.url());
    const screenshotPath = 'after_login.png';
    await page.screenshot({ path: screenshotPath });
    console.log('Screenshot nach Login gespeichert:', screenshotPath);
    // Warte auf ein Consent-Dialog im DOM (dynamisch, tolerant)
    console.log('Suche nach Cookiebot-Dialog im DOM...');
    let foundConsent = false;
    for (let i = 0; i < 20; i++) { // max 10s
      const consentDiv = await page.$("div[class*='cookie'],div[class*='consent']");
      if (consentDiv) {
        foundConsent = true;
        const html = await consentDiv.evaluate(el => el.innerHTML.slice(0, 200));
        console.log('Consent-Dialog gefunden:', html);
        break;
      }
      await page.waitForTimeout(500);
    }
    if (!foundConsent) {
      console.log('Kein Consent-Dialog im DOM gefunden.');
    }
    // Prüfe, ob Consent-Cookie gesetzt wurde
    const cookiesAfterConsent = await page.context().cookies();
    const consentCookie = cookiesAfterConsent.find(c => c.name.toLowerCase().includes('consent'));
    if (consentCookie) {
      console.log('Consent-Cookie im Browser gesetzt:', consentCookie.name, consentCookie.value);
    } else {
      console.log('Kein Consent-Cookie im Browser gefunden.');
    }
    // Logging für Netzwerk-Request
    // ... (hier ggf. fetch/network-request wie gehabt, mit Status- und Fehler-Logging)
    // Gehe auf die Übersichtsseite
    console.log('Gehe zu Übersichtsseite:', overviewUrl);
    await page.goto(overviewUrl);
    await page.waitForLoadState('networkidle');
    console.log('Aktuelle URL nach Übersicht:', page.url());
    await page.waitForTimeout(1000);
    // Setze das Promo-Cookie
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
    console.log('Promo-Cookie gesetzt!');
    // Gehe auf eine Detailseite
    console.log('Gehe zu Detailseite:', detailUrl);
    await page.goto(detailUrl);
    await page.waitForLoadState('networkidle');
    console.log('Aktuelle URL nach Detail:', page.url());
    // Cookiebot-Consent per Request simulieren
    console.log('Sende Cookiebot-Consent-Request...');
    const cbid = 'cb99fb9b-c373-4fad-aaf2-e16b602e9875'; // von freelance.de
    const userAgent = await page.evaluate(() => navigator.userAgent);
    const referer = detailUrl;
    const url = `https://consent.cookiebot.com/logconsent.ashx?action=accept&nocache=${Date.now()}&dnt=false&method=strict&clp=true&cls=true&clm=true&cbid=${cbid}&cbt=leveloptin&hasdata=true&usercountry=DE&referer=${encodeURIComponent(referer)}&rc=false`;
    const headers = {
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
    };
    try {
      const resp = await page.request.get(url, { headers });
      console.log('Consent-Request Status:', resp.status());
    } catch (e) {
      console.warn('Consent-Request fehlgeschlagen:', e);
    }
    // Dialog per JS entfernen
    await page.evaluate(() => {
      const dialog = document.getElementById('CybotCookiebotDialog');
      if (dialog) dialog.remove();
    });
    console.log('Cookiebot-Dialog entfernt (nach Consent-Request).');
    // Cookies speichern
    const allCookies = await page.context().cookies();
    fs.writeFileSync('debug_cookies.json', JSON.stringify(allCookies, null, 2));
    console.log('Cookies gespeichert in debug_cookies.json');
  } catch (e) {
    console.error('Fehler im Debug-Login:', e);
    if (e.stack) console.error(e.stack);
  } finally {
    // await browser.close(); // absichtlich auskommentiert
  }
})(); 