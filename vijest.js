async function ucitajVest() {
    const container = document.getElementById('article-container');
    
    // Debug - prikazujemo sta vidimo
    const puni_url = window.location.href;
    const params = new URLSearchParams(window.location.search);
    const indeks_str = params.get('i');
    
    console.log('URL:', puni_url);
    console.log('Indeks string:', indeks_str);
    
    const indeks = parseInt(indeks_str, 10);
    console.log('Indeks broj:', indeks);
    
    if (isNaN(indeks) || indeks < 0) {
        container.innerHTML = `
            <p class="loading">Vest nije pronađena.</p>
            <p style="text-align:center; color:#888; font-size:0.8rem;">
                Debug: URL je ${puni_url}, indeks = "${indeks_str}"
            </p>
        `;
        return;
    }
    
    try {
        const response = await fetch('content/vesti.json?t=' + Date.now());
        const vesti = await response.json();
        
        console.log('Broj vesti u JSON-u:', vesti.length);
        
        if (!vesti || !vesti[indeks]) {
            container.innerHTML = `<p class="loading">Vest pod brojem ${indeks} ne postoji. Ukupno vesti: ${vesti.length}.</p>`;
            return;
        }
        
        const vest = vesti[indeks];
        
        document.title = (vest.naslov || 'Vest') + ' - Lokalne Vesti';
        
        const slikaUrl = vest.slika 
            ? `content/slike/${vest.slika}` 
            : 'https://placehold.co/800x400/1a3a5c/ffffff?text=Lokalne+Vesti';
        
        const datumPrikaz = vest.datum || '';
        
        container.innerHTML = `
            <article class="single-article">
                <a href="index.html" class="back-link">← Nazad na sve vesti</a>
                <h1>${vest.naslov || 'Bez naslova'}</h1>
                <div class="meta-single">
                    <span>${datumPrikaz}</span>
                </div>
                <img src="${slikaUrl}" alt="${vest.naslov || 'Vest'}"
                     onerror="this.src='https://placehold.co/800x400/1a3a5c/ffffff?text=Lokalne+Vesti'">
                <div class="tekst-single">
                    ${formatirajTekst(vest.tekst)}
                </div>
                <div class="izvor-box">
                    <a href="${vest.link}" target="_blank" rel="noopener" class="izvor-link">
                        Pročitaj originalnu vest na izvoru →
                    </a>
                </div>
            </article>
        `;
        
    } catch (err) {
        console.error('Greška:', err);
        container.innerHTML = '<p class="loading">Greška pri učitavanju vesti: ' + err.message + '</p>';
    }
}

function formatirajTekst(tekst) {
    if (!tekst) return '<p>Tekst nije dostupan.</p>';
    return tekst
        .split(/\n\n+/)
        .map(p => `<p>${p.trim()}</p>`)
        .join('');
}

ucitajVest();