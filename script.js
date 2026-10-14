let sveVesti = [];
let trenutnaKategorija = 'sve';

async function ucitajVesti() {
    const featuredContainer = document.getElementById('featured-container');
    const container = document.getElementById('news-container');
    
    try {
        const response = await fetch('content/vesti.json?t=' + Date.now());
        sveVesti = await response.json();
        
        if (!sveVesti || sveVesti.length === 0) {
            container.innerHTML = '<p class="loading">Trenutno nema vesti.</p>';
            return;
        }

        sveVesti.forEach((v, i) => v._idx = i);
        sveVesti.sort((a, b) => (b.datum || '').localeCompare(a.datum || ''));

        prikaziVesti();
        podesiFiltere();
        
    } catch (err) {
        console.error('Greska:', err);
        document.getElementById('news-container').innerHTML = 
            '<p class="loading">Greska pri ucitavanju vesti.</p>';
    }
}

function prikaziVesti() {
    const featuredContainer = document.getElementById('featured-container');
    const container = document.getElementById('news-container');
    
    const filtrirane = trenutnaKategorija === 'sve' 
        ? sveVesti 
        : sveVesti.filter(v => v.kategorija === trenutnaKategorija);
    
    if (filtrirane.length === 0) {
        featuredContainer.innerHTML = '';
        container.innerHTML = '<p class="loading">Nema vesti u ovoj kategoriji.</p>';
        return;
    }
    
    if (trenutnaKategorija === 'sve' && filtrirane.length > 1) {
        const f = filtrirane[0];
        featuredContainer.innerHTML = `
            <a href="vijest.html?i=${f._idx}" class="featured-card">
                <div class="featured-image">
                    <img src="${slikaUrl(f)}" alt="${f.naslov}" 
                         onerror="this.src='https://placehold.co/1200x600/1a3a5c/ffffff?text=Lokalne+Vesti'">
                </div>
                <div class="featured-body">
                    <span class="kategorija">${f.kategorija || 'Društvo'}</span>
                    <h1>${f.naslov || 'Bez naslova'}</h1>
                    <p>${kratakTekst(f.tekst, 220)}</p>
                    <div class="featured-meta">
                        <span>${formatDatum(f.datum)}</span>
                        <span class="vise">Procitaj celu vest →</span>
                    </div>
                </div>
            </a>
        `;
    } else {
        featuredContainer.innerHTML = '';
    }
    
    const ostale = (trenutnaKategorija === 'sve' && filtrirane.length > 1)
        ? filtrirane.slice(1)
        : filtrirane;
    
    container.innerHTML = '';
    ostale.forEach(vest => {
        const article = document.createElement('a');
        article.className = 'card-link';
        article.href = `vijest.html?i=${vest._idx}`;
        
        article.innerHTML = `
            <div class="card-image">
                <img src="${slikaUrl(vest)}" alt="${vest.naslov}" 
                     onerror="this.src='https://placehold.co/400x250/1a3a5c/ffffff?text=Vesti'">
            </div>
            <div class="card-body">
                <span class="kategorija">${vest.kategorija || 'Društvo'}</span>
                <h2>${vest.naslov || 'Bez naslova'}</h2>
                <p>${kratakTekst(vest.tekst, 140)}</p>
                <div class="card-meta">
                    <span>${formatDatum(vest.datum)}</span>
                </div>
            </div>
        `;
        
        container.appendChild(article);
    });
}

function podesiFiltere() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            trenutnaKategorija = btn.dataset.kategorija;
            prikaziVesti();
        });
    });
}

function slikaUrl(vest) {
    if (!vest.slika) {
        return 'https://placehold.co/400x250/1a3a5c/ffffff?text=Vesti';
    }
    return vest.slika;
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