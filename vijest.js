async function ucitajVest() {
    const container = document.getElementById('article-container');
    
    // Uzimamo indeks iz URL-a (?i=5)
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
        container.innerHTML = '<p class="loading">Greška pri učitavanju vesti.</p>';
    }
}

function formatirajTekst(tekst) {
    if (!tekst) return '<p>Tekst nije dostupan.</p>';
    // Pretvaramo duple prelaze reda u pasuse
    return tekst
        .split(/\n\n+/)
        .map(p => `<p>${p.trim()}</p>`)
        .join('');
}

ucitajVest();