async function ucitajVest() {
    const container = document.getElementById('article-container');
    const params = new URLSearchParams(window.location.search);
    const arhiva = params.get('arhiva');
    const indeks = parseInt(params.get('i'), 10);
    
    if (isNaN(indeks) || indeks < 0) {
        container.innerHTML = '<p class="loading">Vest nije pronadjena.</p>';
        return;
    }
    
    let url;
    if (arhiva) {
        url = `content/arhiva/vesti-${arhiva}.json?t=` + Date.now();
    } else {
        url = 'content/vesti.json?t=' + Date.now();
    }
    
    try {
        const r = await fetch(url);
        const vesti = await r.json();
        
        if (!vesti || !vesti[indeks]) {
            container.innerHTML = '<p class="loading">Vest nije pronadjena.</p>';
            return;
        }
        
        const vest = vesti[indeks];
        document.title = (vest.naslov || 'Vest') + ' - Vesti Srbija';
        
        container.innerHTML = `
            <article class="single-article">
                <a href="${arhiva ? 'arhiva.html?d=' + arhiva : 'index.html'}" class="back-link">
                    ← ${arhiva ? 'Nazad na arhivu' : 'Nazad na naslovnu'}
                </a>
                <span class="kategorija">${vest.kategorija || 'Društvo'}</span>
                <h1>${vest.naslov || 'Bez naslova'}</h1>
                <div class="article-meta">
                    <span>${formatDatum(vest.datum)}</span>
                    <span>·</span>
                    <span>Vesti Srbija</span>
                </div>
                <figure class="article-image">
                    <img src="${vest.slika ? 'content/slike/' + vest.slika : 'https://placehold.co/1200x600/1a3a5c/ffffff?text=Vesti'}" 
                         alt="${vest.naslov}"
                         onerror="this.src='https://placehold.co/1200x600/1a3a5c/ffffff?text=Vesti'">
                </figure>
                <div class="article-body">
                    ${formatirajTekst(vest.tekst)}
                </div>
            </article>
        `;
    } catch (e) {
        console.error(e);
        container.innerHTML = '<p class="loading">Greska pri ucitavanju vesti.</p>';
    }
}

function formatDatum(datum) {
    if (!datum) return '';
    const delovi = datum.split(' ')[0].split('-');
    if (delovi.length !== 3) return datum;
    const meseci = ['januar', 'februar', 'mart', 'april', 'maj', 'jun', 'jul', 'avgust', 'septembar', 'oktobar', 'novembar', 'decembar'];
    return `${parseInt(delovi[2])}. ${meseci[parseInt(delovi[1]) - 1]} ${delovi[0]}.`;
}

function formatirajTekst(tekst) {
    if (!tekst) return '<p>Tekst nije dostupan.</p>';
    const ociscen = tekst.replace(/<[^>]+>/g, '').trim();
    return ociscen.split(/\n\n+/).map(p => `<p>${p.trim()}</p>`).join('');
}

ucitajVest();