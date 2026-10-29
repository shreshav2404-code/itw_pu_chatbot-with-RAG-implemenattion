const html=await(await fetch('http://182.72.188.195/cgi-bin/koha/opac-detail.pl?biblionumber=3450')).text();
const authorSection=(html.match(/<span\b[^>]*class=["'][^"']*\bauthor\b[^"']*["'][^>]*>[\s\S]*?(?=<span\b[^>]*class=["'][^"']*\btype\b)/i)||[,''])[1];
const table=(html.match(/<table\b[^>]*id=["']holdingst["'][^>]*>([\s\S]*?)<\/table>/i)||[,''])[1];
console.log('html',html.length,'author',typeof authorSection,authorSection?.length,'table',typeof table,table?.length);
const authors=[...authorSection.matchAll(/<span\b[^>]*property=["']name["'][^>]*>([\s\S]*?)<\/span>/gi)];
const headers=[...table.matchAll(/<th\b[^>]*>([\s\S]*?)<\/th>/gi)];
const trs=[...table.matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)];
console.log(authors.length,headers.length,trs.length);
