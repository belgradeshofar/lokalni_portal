async function ucitajVest() {
    const container = document.getElementById('article-container');
    
    const params = new URLSearchParams(window.location.search);
    const indeks = parseInt(params.get('i'), 10);
    
    if (isNaN(indeks) || indeks < 0) {
        container.innerHTML = '<p class="loading">Vest nije pronađena.</p>';
        return;
    }
    
    try {
        const response = await fetch('content/vesti.json?t=' + Date.now());
        const vesti = await response.json();
        
        if (!vesti || !vesti[indeks]) {
            container.innerHTML = '<p class="loading">Vest nije pronađena.</p>';
            return;
        }
        
        const vest = vesti[indeks];
        document.title = (vest.naslov || 'Vest') + ' - Lokalne Vesti';
        
        container.innerHTML = `
            <article class="single-article">
                <a href="index.html" class="back-link">← Nazad na naslovnu</a>
                <span class="kategorija">${vest.kategorija || 'Lokalno'}</span>
                <h1>${vest.naslov || 'Bez naslova'}</h1>
                <div class="article-meta">
                    <span>${formatDatum(vest.datum)}</span>
                    <span>·</span>
                    <span>Lokalne Vesti</span>
                </div>
                <figure class="article-image">
                    <img src="${slikaUrl(vest)}" alt="${vest.naslov}"
                         onerror="this.src='https://placehold.co/1200x600/1a3a5c/ffffff?text=Lokalne+Vesti'">
                </figure>
                <div class="article-body">
                    ${formatirajTekst(vest.tekst)}
                </div>
            </article>
        `;
        
    } catch (err) {
        console.error('Greška:', err);
        container.innerHTML = '<p class="loading">Greška pri učitavanju vesti.</p>';
    }
}

function slikaUrl(vest) {
    return vest.slika 
        ? `content/slike/${vest.slika}` 
        : 'https://placehold.co/1200x600/1a3a5c/ffffff?text=Lokalne+Vesti';
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
    return ociscen
        .split(/\n\n+/)
        .map(p => `<p>${p.trim()}</p>`)
        .join('');
}

ucitajVest();