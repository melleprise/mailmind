const { chromium } = require('playwright');
const fs = require('fs');
const axios = require('axios');

(async () => {
  console.log('Starte Browser...');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  console.log('Gehe zu Login-Seite...');
  await page.goto('https://www.freelance.de/login.php');
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
  // --- Credentials dynamisch vom Backend holen ---
  const userId = process.env.FREELANCE_USER_ID || '2';
  const backendUrl = process.env.FREELANCE_BACKEND_URL || 'http://backend:8000/api/v1/freelance/credentials/' + userId + '/';
  console.log('Hole Credentials von:', backendUrl);
  let username, password;
  try {
    const resp = await axios.get(backendUrl);
    username = resp.data.username;
    password = resp.data.password;
    console.log('Credentials geladen:', username);
  } catch (e) {
    console.error('Fehler beim Laden der Credentials:', e);
    process.exit(1);
  }
  await page.fill('#username', username);
  await page.fill('#password', password);
  console.log('Prüfe auf Cookiebot...');
  await page.waitForTimeout(1000);
  const cookieBtn = await page.$('#CybotCookiebotDialogBodyButtonAccept');
  if (cookieBtn) {
    console.log('Cookiebot gefunden, akzeptiere...');
    await cookieBtn.click();
    await page.waitForTimeout(1500);
    const cookies = await page.context().cookies();
    const consentCookie = cookies.find(c => c.name.includes('CookieConsent') || c.name.includes('Cookiebot'));
    if (!consentCookie) {
      console.warn('Consent-Cookie wurde nicht gesetzt!');
    }
  } else {
    console.log('Kein Cookiebot gefunden.');
  }
  console.log('Entferne ggf. Cookiebot-Overlay per JS...');
  await page.evaluate(() => {
    const dialog = document.getElementById('CybotCookiebotDialog');
    if (dialog) dialog.remove();
  });
  console.log('Klicke Login...');
  await page.click('#login');
  console.log('Warte auf Netzwerkleerlauf...');
  await page.waitForLoadState('networkidle');
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
  // Gehe auf eine Detailseite (optional, falls gewünscht)
  const detailUrl = 'https://www.freelance.de/projekte/projekt-1207060-Cloud-Security-Expert-m-w-d';
  console.log('Gehe zu Detailseite:', detailUrl);
  await page.goto(detailUrl);
  await page.waitForLoadState('networkidle');
  console.log('Aktuelle URL nach Detail:', page.url());
  if (page.url().includes('promotion/postlogin.php')) {
    console.warn('Weiterleitung auf promotion/postlogin.php erkannt!');
  }
  const html = await page.content();
  if (!html.includes('Projektbeschreibung') && !html.includes('project-description')) {
    console.warn('Projektbeschreibung nicht gefunden! HTML (gekürzt):', html.slice(0, 1000));
  }
  // Cookiebot-Consent per Request simulieren
  console.log('Sende Cookiebot-Consent-Request...');
  const cbid = 'cb99fb9b-c373-4fad-aaf2-e16b602e9875';
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
  console.log('Speichere Cookies...');
  const cookies = await page.context().cookies();
  fs.writeFileSync('freelance_cookies.json', JSON.stringify(cookies, null, 2));
  console.log('Cookies gespeichert in freelance_cookies.json');
  await browser.close();
  console.log('Browser geschlossen.');
})(); 