const { chromium } = require('playwright');
const fs = require('fs');

(async () => {
  console.log('Starte Browser...');
  const browser = await chromium.launch({ headless: true, slowMo: 100 });
  const page = await browser.newPage();
  console.log('Gehe zu Login-Seite...');
  await page.goto('https://www.freelance.de/login.php');
  console.log('Warte auf Username-Feld...');
  await page.waitForSelector('#username', { timeout: 15000 });
  console.log('Fülle Login-Daten aus...');
  await page.fill('#username', 'melleprise@gmail.com');
  await page.fill('#password', 'h@x@jPLsQtbPk2J');
  console.log('Prüfe auf Cookiebot...');
  await page.waitForTimeout(1000);
  const cookieBtn = await page.$('#CybotCookiebotDialogBodyButtonAccept');
  if (cookieBtn) {
    console.log('Cookiebot gefunden, akzeptiere...');
    await cookieBtn.click();
    await page.waitForTimeout(500);
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
  console.log('Speichere Cookies...');
  const cookies = await page.context().cookies();
  fs.writeFileSync('freelance_cookies.json', JSON.stringify(cookies, null, 2));
  console.log('Cookies gespeichert in freelance_cookies.json');
  await browser.close();
  console.log('Browser geschlossen.');
})(); 