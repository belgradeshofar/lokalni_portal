async function ucitajArhivu() {
    const container = document.getElementById('arhiva-container');
    const params = new URLSearchParams(window.location.search);
    const datum = params.get('d');
    
    if (datum) {
        // Prikazi vesti za taj datum
        await prikaziDan(datum, container);
    } else {
        // Prikazi listu svih datuma
        await prikaziListu(container);
    }
}

async function prikaziListu(container) {
    try {
        const r = await fetch('content/arhiva/index.json?t=' + Date.now());
        const datumi = await r.json();
        
        if (!datumi || datumi.length === 0) {
            container.innerHTML = '<p class="loading">Arhiva je prazna.</p>';
            return;
        }
        
        container.innerHTML = '<div class="arhiva-lista"></div>';
        const lista = container.querySelector('.arhiva-lista');
        
        datumi.forEach(d => {
            const a = document.createElement('a');
            a.href = `arhiva.html?d=${d.datum}`;
            a.className = 'arhiva-item';
            a.innerHTML = `
                <span class="arhiva-datum">${formatDatum(d.datum)}</span>
                <span class="arhiva-broj">${d.broj} vesti</span>
            `;
            lista.appendChild(a);
        });
    } catch (e) {
        console.error(e);
        container.innerHTML = '<p class="loading">Greska pri ucitavanju arhive.</p>';
    }
}

async function prikaziDan(datum, container) {
    try {
        const r = await fetch(`content/arhiva/vesti-${datum}.json?t=` + Date.now());
        const vesti = await r.json();
        
        if (!vesti || vesti.length === 0) {
            container.innerHTML = '<p class="loading">Nema vesti za ovaj datum.</p>';
            return;
        }
        
        container.innerHTML = `
            <a href="arhiva.html" class="back-link">← Nazad na arhivu</a>
            <h1 style="color: #1a3a5c; margin: 1rem 0;">${formatDatum(datum)}</h1>
            <div class="news-grid" id="dan-grid"></div>
        `;
        
        const grid = document.getElementById('dan-grid');
        // Napomena: za arhivu, indeksi su unutar tog fajla
        vesti.forEach((vest, i) => {
            const a = document.createElement('a');
            a.className = 'card-link';
            a.href = `vijest.html?arhiva=${datum}&i=${i}`;
            a.innerHTML = `
                <div class="card-image">
                    <img src="${vest.slika ? 'content/slike/' + vest.slika : 'https://placehold.co/400x250/1a3a5c/ffffff?text=Vesti'}" 
                         alt="${vest.naslov}" onerror="this.src='https://placehold.co/400x250/1a3a5c/ffffff?text=Vesti'">
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
            grid.appendChild(a);
        });
    } catch (e) {
        console.error(e);
        container.innerHTML = '<p class="loading">Greska pri ucitavanju vesti za taj dan.</p>';
    }
}

function kratakTekst(tekst, duzina) {
    if (!tekst) return '';
    const ociscen = tekst.replace(/<[^>]+>/g, '').trim();
    return ociscen.substring(0, duzina) + (ociscen.length > duzina ? '...' : '');
}

function formatDatum(datum) {
    if (!datum) return '';
    const delovi = datum.split('-');
    if (delovi.length !== 3) return datum;
    const meseci = ['januar', 'februar', 'mart', 'april', 'maj', 'jun', 'jul', 'avgust', 'septembar', 'oktobar', 'novembar', 'decembar'];
    return `${parseInt(delovi[2])}. ${meseci[parseInt(delovi[1]) - 1]} ${delovi[0]}.`;
}

ucitajArhivu();