async function ucitajVesti() {
    const featuredContainer = document.getElementById('featured-container');
    const container = document.getElementById('news-container');
    
    try {
        const response = await fetch('content/vesti.json?t=' + Date.now());
        const vesti = await response.json();
        
        if (!vesti || vesti.length === 0) {
            container.innerHTML = '<p class="loading">Trenutno nema vesti.</p>';
            return;
        }

        // Zapamti originalni indeks PRE sortiranja
        vesti.forEach((v, i) => v._idx = i);

        // Sortiraj po datumu (najnovije prvo)
        vesti.sort((a, b) => (b.datum || '').localeCompare(a.datum || ''));

        // Prva vest = featured
        const featured = vesti[0];
        const ostale = vesti.slice(1);

        // Prikaz featured vesti
        featuredContainer.innerHTML = `
            <a href="vijest.html?i=${featured._idx}" class="featured-card">
                <div class="featured-image">
                    <img src="${slikaUrl(featured)}" alt="${featured.naslov}" 
                         onerror="this.src='https://placehold.co/1200x600/1a3a5c/ffffff?text=Lokalne+Vesti'">
                </div>
                <div class="featured-body">
                    <span class="kategorija">${featured.kategorija || 'Lokalno'}</span>
                    <h1>${featured.naslov || 'Bez naslova'}</h1>
                    <p>${kratakTekst(featured.tekst, 220)}</p>
                    <div class="featured-meta">
                        <span>${formatDatum(featured.datum)}</span>
                        <span class="vise">Pročitaj celu vest →</span>
                    </div>
                </div>
            </a>
        `;

        // Prikaz ostalih vesti
        container.innerHTML = '';
        ostale.forEach(vest => {
            const article = document.createElement('a');
            article.className = 'card-link';
            article.href = `vijest.html?i=${vest._idx}`;
            
            article.innerHTML = `
                <div class="card-image">
                    <img src="${slikaUrl(vest)}" alt="${vest.naslov}" 
                         onerror="this.src='https://placehold.co/400x250/1a3a5c/ffffff?text=Lokalne+Vesti'">
                </div>
                <div class="card-body">
                    <span class="kategorija">${vest.kategorija || 'Lokalno'}</span>
                    <h2>${vest.naslov || 'Bez naslova'}</h2>
                    <p>${kratakTekst(vest.tekst, 140)}</p>
                    <div class="card-meta">
                        <span>${formatDatum(vest.datum)}</span>
                    </div>
                </div>
            `;
            
            container.appendChild(article);
        });
        
    } catch (err) {
        console.error('Greška:', err);
        container.innerHTML = '<p class="loading">Greška pri učitavanju vesti.</p>';
    }
}

function slikaUrl(vest) {
    return vest.slika 
        ? `content/slike/${vest.slika}` 
        : 'https://placehold.co/400x250/1a3a5c/ffffff?text=Lokalne+Vesti';
}

function kratakTekst(tekst, duzina) {
    if (!tekst) return '';
    const ociscen = tekst.replace(/<[^>]+>/g, '').trim();
    return ociscen.substring(0, duzina) + (ociscen.length > duzina ? '...' : '');
}

function formatDatum(datum) {
    if (!datum) return '';
    const delovi = datum.split(' ')[0].split('-');
    if (delovi.length !== 3) return datum;
    const meseci = ['jan', 'feb', 'mar', 'apr', 'maj', 'jun', 'jul', 'avg', 'sep', 'okt', 'nov', 'dec'];
    return `${parseInt(delovi[2])}. ${meseci[parseInt(delovi[1]) - 1]} ${delovi[0]}.`;
}

ucitajVesti();