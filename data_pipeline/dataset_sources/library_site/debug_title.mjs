const html=await(await fetch('http://182.72.188.195/cgi-bin/koha/opac-detail.pl?biblionumber=3450')).text();
console.log([...html.matchAll(/<h1\b[^>]*class=["'][^"']*\btitle\b[^"']*["'][^>]*>([\s\S]*?)<\/h1>/gi)].map(m=>m[1]).slice(0,10));
console.log([...html.matchAll(/<h1\b[^>]*property=["']name["'][^>]*>([\s\S]*?)<\/h1>/gi)].map(m=>m[1]).slice(0,10));
