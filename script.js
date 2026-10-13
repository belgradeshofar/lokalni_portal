async function ucitajVesti() {
    const container = document.getElementById('news-container');
    
    try {
        const response = await fetch('content/vesti.json?t=' + Date.now());
        const vesti = await response.json();
        
        if (!vesti || vesti.length === 0) {
            container.innerHTML = '<p class="loading">Trenutno nema vesti. Proverite kasnije.</p>';
            return;
        }

        // ZAPAMTI originalni indeks PRE sortiranja
        vesti.forEach((v, i) => v._idx = i);

        // Sortiraj po datumu (najnovije prvo)
        vesti.sort((a, b) => (b.datum || '').localeCompare(a.datum || ''));

        container.innerHTML = '';
        
        vesti.forEach((vest) => {
            const article = document.createElement('a');
            article.className = 'card-link';
            // Koristimo ZAPAMCENI originalni indeks
            article.href = `vijest.html?i=${vest._idx}`;
            
            const slikaUrl = vest.slika 
                ? `content/slike/${vest.slika}` 
                : 'https://placehold.co/400x200/1a3a5c/ffffff?text=Lokalne+Vesti';
            
            const kratakTekst = vest.tekst 
                ? vest.tekst.substring(0, 180) + (vest.tekst.length > 180 ? '...' : '')
                : 'Klikni za više informacija.';
            
            const datumPrikaz = vest.datum ? vest.datum.split(' ')[0] : '';
            
            article.innerHTML = `
                <img src="${slikaUrl}" alt="${vest.naslov || 'Vest'}" 
                     onerror="this.src='https://placehold.co/400x200/1a3a5c/ffffff?text=Lokalne+Vesti'">
                <div class="content">
                    <h2>${vest.naslov || 'Bez naslova'}</h2>
                    <p class="tekst">${kratakTekst}</p>
                    <div class="meta">
                        <span>${datumPrikaz}</span>
                        <span class="vise">Pročitaj →</span>
                    </div>
                </div>
            `;
            
            container.appendChild(article);
        });
        
    } catch (err) {
        console.error('Greška:', err);
        container.innerHTML = '<p class="loading">Greška pri učitavanju vesti. Pokušajte ponovo.</p>';
    }
}

ucitajVesti();