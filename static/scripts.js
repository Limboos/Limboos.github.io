document.addEventListener('DOMContentLoaded', () => {
    // Elementy DOM
    const scrapeBtn = document.getElementById('scrapeBtn');
    const loadBtn = document.getElementById('loadBtn');
    const aiAnalyzeBtn = document.getElementById('aiAnalyzeBtn');
    const pagesInput = document.getElementById('pages');
    const statisticsDiv = document.getElementById('statistics');
    const bikesTableDiv = document.getElementById('bikes-table');
    const brandFilter = document.getElementById('brand-filter');
    const sizeFilter = document.getElementById('size-filter');
    const priceMinInput = document.getElementById('price-min');
    const priceMaxInput = document.getElementById('price-max');
    const filterBtn = document.getElementById('filter-btn');
    const resetFilterBtn = document.getElementById('reset-filter-btn');
    const aiDetailsModal = document.getElementById('aiDetailsModal');
    const aiDetailsContent = document.getElementById('aiDetailsContent');
    const bikeDetailsModal = document.getElementById('bikeDetailsModal');
    const bikeDetailsContent = document.getElementById('bikeDetailsContent');
    
    // Globalne zmienne
    let allBikes = [];
    let filteredBikes = [];
    let sortField = 'price';
    let sortDirection = 'asc';
    let brandChart = null;
    let priceChart = null;
    
    // Pobieranie danych z OLX
    scrapeBtn.addEventListener('click', async () => {
        const pages = pagesInput.value;
        statisticsDiv.innerHTML = '<div class="loading">Pobieranie danych...</div>';
        bikesTableDiv.innerHTML = '<div class="loading">Pobieranie danych...</div>';
        
        // Wyłącz przycisk podczas pobierania
        scrapeBtn.disabled = true;
        scrapeBtn.innerHTML = 'Pobieranie danych...';
        
        try {
            const response = await fetch(`/api/scrape?pages=${pages}`);
            if (!response.ok) {
                throw new Error('Błąd podczas pobierania danych');
            }
            
            await loadData();
        } catch (error) {
            alert(`Błąd: ${error.message}`);
            statisticsDiv.innerHTML = '<div class="loading">Wystąpił błąd</div>';
            bikesTableDiv.innerHTML = '<div class="loading">Wystąpił błąd</div>';
        } finally {
            // Włącz przycisk ponownie
            scrapeBtn.disabled = false;
            scrapeBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg> Pobierz dane z OLX';
        }
    });
    
    // Ładowanie zapisanych danych
    loadBtn.addEventListener('click', loadData);
    
    // Obsługa filtrowania
    filterBtn.addEventListener('click', applyFilters);
    resetFilterBtn.addEventListener('click', resetFilters);
    
    // Obsługa analizy AI
    aiAnalyzeBtn.addEventListener('click', analyzeWithAI);
    
    // Obsługa modalu
    const closeModalBtn = document.querySelector('.close');
    closeModalBtn.addEventListener('click', () => {
        aiDetailsModal.style.display = 'none';
    });
    
    window.addEventListener('click', (event) => {
        if (event.target === aiDetailsModal) {
            aiDetailsModal.style.display = 'none';
        }
        if (event.target === bikeDetailsModal) {
            bikeDetailsModal.style.display = 'none';
        }
    });
    
    // Dodanie obsługi przycisku zamykającego modal z parametrami technicznymi
    const closeTechModalBtn = document.querySelector('#bikeDetailsModal .close');
    if (closeTechModalBtn) {
        closeTechModalBtn.addEventListener('click', () => {
            bikeDetailsModal.style.display = 'none';
        });
    }
    
    // Funkcja ładująca dane
    async function loadData() {
        try {
            console.log('Starting data loading process...');
            
            // Ładowanie statystyk
            console.log('Fetching statistics...');
            const statsResponse = await fetch('/api/data/statistics');
            if (!statsResponse.ok) {
                throw new Error('Błąd podczas ładowania statystyk');
            }
            const stats = await statsResponse.json();
            console.log('Statistics loaded:', stats);
            displayStatistics(stats);
            
            let shouldLoadBasicData = true;
                        
            // Ładowanie podstawowych danych o rowerach (jeśli nie ma wzbogaconych)
            if (shouldLoadBasicData) {
                console.log('Loading basic bike data...');
                const bikesResponse = await fetch('/api/data/bikes');
                if (!bikesResponse.ok) {
                    throw new Error('Błąd podczas ładowania danych o rowerach');
                }
                allBikes = await bikesResponse.json();
                console.log('Basic bikes data loaded:', allBikes);
                
                if (!allBikes || !Array.isArray(allBikes)) {
                    throw new Error('Nieprawidłowy format danych');
                }
                
                filteredBikes = [...allBikes];
                
                // Aktualizacja filtrów
                updateFilterOptions();
                
                // Wyświetlanie danych
                displayBikes(filteredBikes);
                
                // Generowanie wykresów
                generateCharts(allBikes, stats);
            }
            
            // // Najpierw sprawdź, czy są dostępne wzbogacone dane
            // console.log('Checking for enriched data...');
            // const enrichedResponse = await fetch('/api/data/enriched-bikes');
            // if (enrichedResponse.ok) {
            //     const enrichedBikes = await enrichedResponse.json();
            //     console.log('Enriched bikes data:', enrichedBikes);
            //     if (enrichedBikes && Array.isArray(enrichedBikes) && enrichedBikes.length > 0) {
            //         console.log(`Found ${enrichedBikes.length} enriched bikes`);
            //         // Jeśli są wzbogacone dane, używamy ich
            //         allBikes = enrichedBikes;
            //         filteredBikes = [...allBikes];
                    
            //         // Aktualizacja filtrów
            //         updateFilterOptions();
                    
            //         // Wyświetlanie danych
            //         displayBikes(filteredBikes);
                    
            //         // Generowanie wykresów
            //         generateCharts(allBikes, stats);
                    
            //         shouldLoadBasicData = false; // Nie ładuj podstawowych danych
            //     } else {
            //         console.log('No valid enriched bikes found, will load basic data');
            //     }
            // } else {
            //     console.log('Enriched bikes endpoint returned error:', enrichedResponse.status);
            // }


        } catch (error) {
            console.error('Error loading data:', error);
            bikesTableDiv.innerHTML = `<div class="loading">Błąd podczas ładowania danych: ${error.message}</div>`;
        }
    }
    
    // Aktualizacja opcji filtrów
    function updateFilterOptions() {
        // Pobieranie unikalnych marek i rozmiarów
        const brands = [...new Set(allBikes
            .map(bike => bike.brand)
            .filter(Boolean)
            .sort())];
        
        const sizes = [...new Set(allBikes
            .map(bike => bike.size)
            .filter(Boolean)
            .sort())];
        
        // Aktualizacja opcji filtrów
        brandFilter.innerHTML = '<option value="">Wszystkie</option>';
        brands.forEach(brand => {
            const option = document.createElement('option');
            option.value = brand;
            option.textContent = brand;
            brandFilter.appendChild(option);
        });
        
        sizeFilter.innerHTML = '<option value="">Wszystkie</option>';
        sizes.forEach(size => {
            const option = document.createElement('option');
            option.value = size;
            option.textContent = size;
            sizeFilter.appendChild(option);
        });
    }
    
    // Funkcja filtrowania
    function applyFilters() {
        const selectedBrand = brandFilter.value;
        const selectedSize = sizeFilter.value;
        const minPrice = priceMinInput.value ? parseFloat(priceMinInput.value) : 0;
        const maxPrice = priceMaxInput.value ? parseFloat(priceMaxInput.value) : Infinity;
        
        filteredBikes = allBikes.filter(bike => {
            const matchesBrand = !selectedBrand || bike.brand === selectedBrand;
            const matchesSize = !selectedSize || bike.size === selectedSize;
            const matchesPrice = bike.price >= minPrice && bike.price <= maxPrice;
            
            return matchesBrand && matchesSize && matchesPrice;
        });
        
        sortBikes();
        displayBikes(filteredBikes);
    }
    
    // Resetowanie filtrów
    function resetFilters() {
        brandFilter.value = '';
        sizeFilter.value = '';
        priceMinInput.value = '';
        priceMaxInput.value = '';
        
        filteredBikes = [...allBikes];
        sortBikes();
        displayBikes(filteredBikes);
    }
    
    // Funkcja sortowania
    function sortBikes() {
        filteredBikes.sort((a, b) => {
            const valueA = a[sortField] || 0;
            const valueB = b[sortField] || 0;
            
            if (sortDirection === 'asc') {
                return valueA > valueB ? 1 : -1;
            } else {
                return valueA < valueB ? 1 : -1;
            }
        });
    }
    
    // Obsługa sortowania po kliknięciu nagłówka
    function handleSort(field) {
        if (sortField === field) {
            sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        } else {
            sortField = field;
            sortDirection = 'asc';
        }
        
        sortBikes();
        displayBikes(filteredBikes);
    }
    
    // Wyświetlanie statystyk
    function displayStatistics(stats) {
        if (Object.keys(stats).length === 0) {
            statisticsDiv.innerHTML = '<div class="loading">Brak dostępnych statystyk</div>';
            return;
        }
        
        let html = '';
        
        if (stats.price_stats) {
            html += `
                <div class="stat-card">
                    <h3>Statystyki cen</h3>
                    <p><strong>Średnia:</strong> ${stats.price_stats.mean.toFixed(2)} zł</p>
                    <p><strong>Mediana:</strong> ${stats.price_stats.median.toFixed(2)} zł</p>
                    <p><strong>Min:</strong> ${stats.price_stats.min.toFixed(2)} zł</p>
                    <p><strong>Max:</strong> ${stats.price_stats.max.toFixed(2)} zł</p>
                </div>
            `;
        }
        
        if (stats.total_listings) {
            html += `
                <div class="stat-card">
                    <h3>Ogłoszenia</h3>
                    <p><strong>Liczba ogłoszeń:</strong> ${stats.total_listings}</p>
                    <p><strong>Z rozpoznaną marką:</strong> ${stats.identified_brands || 0}</p>
                    <p><strong>Z rozpoznanym rozmiarem:</strong> ${stats.identified_sizes || 0}</p>
                    ${stats.identified_bike_types ? `<p><strong>Z rozpoznanym typem roweru:</strong> ${stats.identified_bike_types}</p>` : ''}
                    ${stats.identified_condition ? `<p><strong>Z rozpoznanym stanem:</strong> ${stats.identified_condition}</p>` : ''}
                </div>
            `;
        }
        
        if (stats.brand_counts) {
            html += `
                <div class="stat-card">
                    <h3>Najpopularniejsze marki</h3>
                    <ul>
                        ${Object.entries(stats.brand_counts)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 5)
                            .map(([brand, count]) => `<li><strong>${brand}:</strong> ${count}</li>`)
                            .join('')}
                    </ul>
                </div>
            `;
        }
        
        if (stats.location_counts) {
            html += `
                <div class="stat-card">
                    <h3>Najpopularniejsze lokalizacje</h3>
                    <ul>
                        ${Object.entries(stats.location_counts)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 5)
                            .map(([location, count]) => `<li><strong>${location}:</strong> ${count}</li>`)
                            .join('')}
                    </ul>
                </div>
            `;
        }
        
        // Nowe statystyki:
        
        // Statystyki typów rowerów
        if (stats.bicycle_type_counts) {
            html += `
                <div class="stat-card">
                    <h3>Typy rowerów</h3>
                    <ul>
                        ${Object.entries(stats.bicycle_type_counts)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 5)
                            .map(([type, count]) => `<li><strong>${type}:</strong> ${count}</li>`)
                            .join('')}
                    </ul>
                </div>
            `;
        }
        
        // Średnie ceny według typów
        if (stats.avg_price_by_type) {
            html += `
                <div class="stat-card">
                    <h3>Średnie ceny według typu</h3>
                    <ul>
                        ${Object.entries(stats.avg_price_by_type)
                            .sort((a, b) => b[1] - a[1])
                            .map(([type, price]) => `<li><strong>${type}:</strong> ${price.toFixed(2)} zł</li>`)
                            .join('')}
                    </ul>
                </div>
            `;
        }
        
        // Średnie ceny według marek
        if (stats.avg_price_by_brand) {
            html += `
                <div class="stat-card">
                    <h3>Średnie ceny według marki</h3>
                    <ul>
                        ${Object.entries(stats.avg_price_by_brand)
                            .sort((a, b) => b[1] - a[1])
                            .slice(0, 8)
                            .map(([brand, price]) => `<li><strong>${brand}:</strong> ${price.toFixed(2)} zł</li>`)
                            .join('')}
                    </ul>
                </div>
            `;
        }
        
        // Materiały ram
        if (stats.frame_material_counts) {
            html += `
                <div class="stat-card">
                    <h3>Materiały ram</h3>
                    <ul>
                        ${Object.entries(stats.frame_material_counts)
                            .sort((a, b) => b[1] - a[1])
                            .map(([material, count]) => `<li><strong>${material}:</strong> ${count}</li>`)
                            .join('')}
                    </ul>
                </div>
            `;
        }
        
        // Rozmiary kół
        if (stats.wheel_size_counts) {
            html += `
                <div class="stat-card">
                    <h3>Rozmiary kół</h3>
                    <ul>
                        ${Object.entries(stats.wheel_size_counts)
                            .sort((a, b) => b[1] - a[1])
                            .map(([size, count]) => `<li><strong>${size}:</strong> ${count}</li>`)
                            .join('')}
                    </ul>
                </div>
            `;
        }
        
        // Stan techniczny
        if (stats.condition_counts) {
            html += `
                <div class="stat-card">
                    <h3>Stan techniczny</h3>
                    <ul>
                        ${Object.entries(stats.condition_counts)
                            .sort((a, b) => b[1] - a[1])
                            .map(([condition, count]) => `<li><strong>${condition}:</strong> ${count}</li>`)
                            .join('')}
                    </ul>
                </div>
            `;
        }
        
        // Porównanie używane vs nowe
        if (stats.used_vs_new) {
            html += `
                <div class="stat-card">
                    <h3>Używane vs Nowe</h3>
                    <p><strong>Nowe rowery:</strong> ${stats.used_vs_new.new} (${((stats.used_vs_new.new / stats.total_listings) * 100).toFixed(1)}%)</p>
                    <p><strong>Używane rowery:</strong> ${stats.used_vs_new.used} (${((stats.used_vs_new.used / stats.total_listings) * 100).toFixed(1)}%)</p>
                    ${stats.used_vs_new.avg_price_new ? `<p><strong>Średnia cena nowych:</strong> ${stats.used_vs_new.avg_price_new.toFixed(2)} zł</p>` : ''}
                    ${stats.used_vs_new.avg_price_used ? `<p><strong>Średnia cena używanych:</strong> ${stats.used_vs_new.avg_price_used.toFixed(2)} zł</p>` : ''}
                </div>
            `;
        }
        
        // Ocena wartości (z analizy AI)
        if (stats.value_assessment_counts) {
            html += `
                <div class="stat-card">
                    <h3>Ocena wartości (AI)</h3>
                    <p><strong>Uczciwa cena:</strong> ${stats.value_assessment_counts.fair || 0}</p>
                    <p><strong>Zawyżona cena:</strong> ${stats.value_assessment_counts.overpriced || 0}</p>
                    <p><strong>Zaniżona cena:</strong> ${stats.value_assessment_counts.underpriced || 0}</p>
                </div>
            `;
        }
        
        // Sezonowość
        if (stats.monthly_counts) {
            html += `
                <div class="stat-card">
                    <h3>Sezonowość ogłoszeń</h3>
                    <ul>
                        ${Object.entries(stats.monthly_counts)
                            .map(([month, count]) => `<li><strong>${month}:</strong> ${count}</li>`)
                            .join('')}
                    </ul>
                </div>
            `;
        }
        
        statisticsDiv.innerHTML = html || '<div class="loading">Brak dostępnych statystyk</div>';
    }
    
    // Wyświetlanie danych o rowerach
    function displayBikes(bikes) {
        console.log('displayBikes called with:', bikes);
        
        if (!bikes || bikes.length === 0) {
            console.log('No bikes data to display');
            bikesTableDiv.innerHTML = '<div class="loading">Brak dostępnych danych o rowerach</div>';
            return;
        }
        
        console.log(`Displaying ${bikes.length} bikes`);
        
        // Helper function to get value from either direct property or parameters
        const getValue = (bike, propertyName, parameterName) => {
            if (bike[propertyName]) return bike[propertyName];
            if (bike.parameters && bike.parameters[parameterName]) return bike.parameters[parameterName];
            return '-';
        };
        
        // Sprawdzenie, czy jakikolwiek rower ma dane analizy AI
        const hasAiData = bikes.some(bike => bike.ai_analysis);
        console.log('Has AI data:', hasAiData);
        
        // Sprawdzenie, czy jakikolwiek rower ma parametry techniczne
        const hasCondition = bikes.some(bike => bike.condition || (bike.parameters && bike.parameters['Stan']));
        const hasFrameMaterial = bikes.some(bike => bike.frame_material || (bike.parameters && bike.parameters['Materiał ramy']));
        const hasBrakeType = bikes.some(bike => bike.brake_type || (bike.parameters && bike.parameters['Typ hamulca']));
        const hasWheelSize = bikes.some(bike => bike.wheel_size || (bike.parameters && bike.parameters['Rozmiar koła']));
        
        console.log('Technical parameters:', { hasCondition, hasFrameMaterial, hasBrakeType, hasWheelSize });
        
        // Log the first bike to see its structure
        if (bikes.length > 0) {
            console.log('First bike data:', bikes[0]);
        }
        
        let html = `
            <table>
                <thead>
                    <tr>
                        <th onclick="handleSort('title')">Tytuł ${sortField === 'title' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('price')">Cena (zł) ${sortField === 'price' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('brand')">Marka ${sortField === 'brand' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('size')">Rozmiar ${sortField === 'size' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('year')">Rok ${sortField === 'year' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('condition')">Stan ${sortField === 'condition' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('frame_material')">Materiał ${sortField === 'frame_material' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('brake_type')">Hamulce ${sortField === 'brake_type' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('wheel_size')">Koła ${sortField === 'wheel_size' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('location')">Lokalizacja ${sortField === 'location' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th onclick="handleSort('date_added')">Data dodania ${sortField === 'date_added' ? `<span class="sort-icon">${sortDirection === 'asc' ? '↑' : '↓'}</span>` : ''}</th>
                        <th>Akcje</th>
                    </tr>
                </thead>
                <tbody>
        `;
        
        // Limit the number of bikes to display to avoid performance issues
        const bikesToDisplay = bikes.slice(0, 100);
        console.log(`Displaying first ${bikesToDisplay.length} bikes out of ${bikes.length}`);
        
        bikesToDisplay.forEach((bike, index) => {
            // Log every 10th bike to avoid console spam
            if (index % 10 === 0) {
                console.log(`Processing bike ${index}:`, bike.title);
            }
            
            html += `
                <tr>
                    <td>${bike.title || '-'}</td>
                    <td class="price">${bike.price ? bike.price.toLocaleString() + ' zł' : '-'}</td>
                    <td>${getValue(bike, 'brand', 'Marka') ? `<span class="badge">${getValue(bike, 'brand', 'Marka')}</span>` : '-'}</td>
                    <td>${getValue(bike, 'size', 'Rozmiar ramy')}</td>
                    <td>${bike.year || '-'}</td>
                    <td>${getValue(bike, 'condition', 'Stan')}</td>
                    <td>${getValue(bike, 'frame_material', 'Materiał ramy')}</td>
                    <td>${getValue(bike, 'brake_type', 'Typ hamulca')}</td>
                    <td>${getValue(bike, 'wheel_size', 'Rozmiar koła')}</td>
                    <td>${bike.location || '-'}</td>
                    <td>${bike.date_added || '-'}</td>
                    <td>
                        <a href="${bike.url}" target="_blank" class="action-button">Zobacz ogłoszenie</a>
                        ${bike.parameters ? `<button class="action-button details-button" onclick="showBikeDetails('${encodeURIComponent(JSON.stringify(bike))}')">Szczegóły tech.</button>` : ''}
                        ${bike.ai_analysis ? `<button class="action-button ai-button" onclick="showAiDetails('${encodeURIComponent(JSON.stringify(bike.ai_analysis))}')">Analiza AI</button>` : ''}
                    </td>
                </tr>
            `;
        });
        
        html += `
                </tbody>
            </table>
            ${bikes.length > 100 ? `<div class="pagination-info">Wyświetlono pierwsze 100 z ${bikes.length} rowerów</div>` : ''}
        `;
        
        console.log('Setting bikesTableDiv.innerHTML with generated HTML');
        bikesTableDiv.innerHTML = html;
        
        // Dodanie nasłuchiwania zdarzeń dla sortowania
        document.querySelectorAll('th').forEach(th => {
            th.addEventListener('click', function() {
                if (this.getAttribute('onclick')) {
                    const field = this.getAttribute('onclick').match(/handleSort\('(.+?)'\)/)[1];
                    handleSort(field);
                }
            });
        });
    }
    
    // Generowanie wykresów
    function generateCharts(bikes, stats) {
        const brandCtx = document.getElementById('brandChart').getContext('2d');
        const priceCtx = document.getElementById('priceChart').getContext('2d');
        
        // Wykres marek
        if (stats.brand_counts && brandChart === null) {
            const brandData = Object.entries(stats.brand_counts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10);
            
            brandChart = new Chart(brandCtx, {
                type: 'bar',
                data: {
                    labels: brandData.map(item => item[0]),
                    datasets: [{
                        label: 'Liczba ogłoszeń',
                        data: brandData.map(item => item[1]),
                        backgroundColor: 'rgba(52, 152, 219, 0.7)',
                        borderColor: 'rgba(52, 152, 219, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: {
                            position: 'top',
                        },
                        title: {
                            display: false,
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Liczba ogłoszeń'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: 'Marka'
                            }
                        }
                    }
                }
            });
        } else if (brandChart !== null) {
            const brandData = Object.entries(stats.brand_counts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 10);
            
            brandChart.data.labels = brandData.map(item => item[0]);
            brandChart.data.datasets[0].data = brandData.map(item => item[1]);
            brandChart.update();
        }
        
        // Analiza cen dla wykresu histogramu
        if (bikes.length > 0 && priceChart === null) {
            const prices = bikes.map(bike => bike.price).filter(Boolean);
            
            if (prices.length > 0) {
                const min = Math.min(...prices);
                const max = Math.max(...prices);
                const range = max - min;
                const binCount = 10;
                const binSize = range / binCount;
                
                const bins = Array(binCount).fill(0);
                const binLabels = [];
                
                for (let i = 0; i < binCount; i++) {
                    const binMin = min + i * binSize;
                    const binMax = min + (i + 1) * binSize;
                    binLabels.push(`${binMin.toFixed(0)}-${binMax.toFixed(0)}`);
                }
                
                prices.forEach(price => {
                    const binIndex = Math.min(Math.floor((price - min) / binSize), binCount - 1);
                    bins[binIndex]++;
                });
                
                priceChart = new Chart(priceCtx, {
                    type: 'bar',
                    data: {
                        labels: binLabels,
                        datasets: [{
                            label: 'Liczba ogłoszeń',
                            data: bins,
                            backgroundColor: 'rgba(46, 204, 113, 0.7)',
                            borderColor: 'rgba(46, 204, 113, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: {
                        responsive: true,
                        plugins: {
                            legend: {
                                position: 'top',
                            },
                            title: {
                                display: false,
                            }
                        },
                        scales: {
                            y: {
                                beginAtZero: true,
                                title: {
                                    display: true,
                                    text: 'Liczba ogłoszeń'
                                }
                            },
                            x: {
                                title: {
                                    display: true,
                                    text: 'Przedział cenowy (zł)'
                                }
                            }
                        }
                    }
                });
            }
        } else if (priceChart !== null && bikes.length > 0) {
            const prices = bikes.map(bike => bike.price).filter(Boolean);
            
            if (prices.length > 0) {
                const min = Math.min(...prices);
                const max = Math.max(...prices);
                const range = max - min;
                const binCount = 10;
                const binSize = range / binCount;
                
                const bins = Array(binCount).fill(0);
                const binLabels = [];
                
                for (let i = 0; i < binCount; i++) {
                    const binMin = min + i * binSize;
                    const binMax = min + (i + 1) * binSize;
                    binLabels.push(`${binMin.toFixed(0)}-${binMax.toFixed(0)}`);
                }
                
                prices.forEach(price => {
                    const binIndex = Math.min(Math.floor((price - min) / binSize), binCount - 1);
                    bins[binIndex]++;
                });
                
                priceChart.data.labels = binLabels;
                priceChart.data.datasets[0].data = bins;
                priceChart.update();
            }
        }
    }
    
    // Przypisanie funkcji obsługi sortowania do globalnego obiektu window
    window.handleSort = handleSort;
    window.showAiDetails = showAiDetails;
    window.showBikeDetails = showBikeDetails;
    
    // Automatyczne ładowanie danych przy starcie
    loadData();
});

// Funkcja obsługująca analizę AI
async function analyzeWithAI() {
    try {
        // Zmień tekst przycisku i zablokuj go
        const aiAnalyzeBtn = document.getElementById('aiAnalyzeBtn');
        const bikesTableDiv = document.getElementById('bikes-table');
        const progressContainer = document.getElementById('progress-container');
        const progressBar = document.getElementById('progress-bar');
        const progressPercentage = document.getElementById('progress-percentage');
        const progressStatus = document.getElementById('progress-status');
        
        aiAnalyzeBtn.disabled = true;
        aiAnalyzeBtn.innerHTML = 'Analizuję...';
        
        // Pokaż kontener postępu
        progressContainer.style.display = 'block';
        progressBar.style.width = '0%';
        progressPercentage.textContent = '0%';
        progressStatus.textContent = 'Inicjalizacja analizy...';
        
        // Ustaw EventSource do nasłuchiwania aktualizacji postępu
        const eventSource = new EventSource('/api/ai-analyze/progress');
        
        eventSource.onmessage = function(event) {
            const data = JSON.parse(event.data);
            const { current, total, status } = data;
            
            // Aktualizuj pasek postępu
            const percentage = Math.round((current / total) * 100);
            progressBar.style.width = `${percentage}%`;
            progressPercentage.textContent = `${percentage}%`;
            progressStatus.textContent = status;
            
            // Jeśli zakończono, zamknij połączenie
            if (current >= total) {
                eventSource.close();
            }
        };
        
        eventSource.onerror = function() {
            // W przypadku błędu zamknij połączenie
            eventSource.close();
        };
        
        // Wywołaj endpoint analizy AI
        const response = await fetch('/api/ai-analyze');
        
        if (!response.ok) {
            throw new Error(`Błąd HTTP: ${response.status}`);
        }
        
        // Pobierz wzbogacone dane
        const enrichedBikes = await response.json();
        
        // Sprawdź czy otrzymane dane są tablicą
        if (!Array.isArray(enrichedBikes)) {
            throw new Error('Otrzymane dane nie są tablicą');
        }
        
        // Zaktualizuj dane lokalne
        allBikes = enrichedBikes;
        filteredBikes = [...allBikes];
        
        // Aktualizacja filtrów
        updateFilterOptions();
        
        // Wyświetl dane
        displayBikes(filteredBikes);
        
        // Ukryj kontener postępu po zakończeniu
        progressContainer.style.display = 'none';
        
    } catch (error) {
        console.error('Błąd analizy AI:', error);
        alert(`Błąd analizy AI: ${error.message}`);
        document.getElementById('bikes-table').innerHTML = '<div class="loading">Wystąpił błąd podczas analizy AI</div>';
        document.getElementById('progress-container').style.display = 'none';
    } finally {
        // Odblokuj przycisk
        const aiAnalyzeBtn = document.getElementById('aiAnalyzeBtn');
        aiAnalyzeBtn.disabled = false;
        aiAnalyzeBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 16v-4"></path>
                <path d="M12 8h.01"></path>
            </svg>
            Analiza AI
        `;
    }
}

// Funkcja wyświetlająca szczegóły analizy AI
function showAiDetails(encodedData) {
    try {
        const aiAnalysis = JSON.parse(decodeURIComponent(encodedData));
        const aiDetailsContent = document.getElementById('aiDetailsContent');
        const aiDetailsModal = document.getElementById('aiDetailsModal');
        
        // Tworzy zawartość modalu
        let content = '';
        
        // Sekcja szczegółów analizy
        if (aiAnalysis.parsed_details) {
            const details = aiAnalysis.parsed_details;
            content += `
                <div class="ai-details-section">
                    <h3>Rozpoznane szczegóły</h3>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Typ roweru:</div>
                        <div class="ai-detail-value">${details.bicycle_type || 'Nierozpoznany'}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Marka i model:</div>
                        <div class="ai-detail-value">${details.brand || 'Nierozpoznana'} ${details.model || ''}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Rozmiar ramy:</div>
                        <div class="ai-detail-value">${details.frame_size || 'Nierozpoznany'}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Materiał ramy:</div>
                        <div class="ai-detail-value">${details.frame_material || 'Nierozpoznany'}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Rozmiar kół:</div>
                        <div class="ai-detail-value">${details.wheel_size || 'Nierozpoznany'}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Osprzęt:</div>
                        <div class="ai-detail-value">${details.groupset || 'Nierozpoznany'}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Rok produkcji:</div>
                        <div class="ai-detail-value">${details.year || 'Nierozpoznany'}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Stan:</div>
                        <div class="ai-detail-value">${details.condition || 'Nierozpoznany'}</div>
                    </div>
                    
                    ${details.accessories && details.accessories.length > 0 ? `
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Dołączone akcesoria:</div>
                        <div class="ai-detail-value">
                            <ul class="ai-list">
                                ${details.accessories.map(item => `<li>${item}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                    ` : ''}
                </div>
            `;
        }
        
        // Sekcja kategoryzacji
        if (aiAnalysis.category && !aiAnalysis.category.error) {
            const category = aiAnalysis.category;
            content += `
                <div class="ai-details-section">
                    <h3>Kategoryzacja</h3>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Główna kategoria:</div>
                        <div class="ai-detail-value">${category.primary_category || 'Nierozpoznana'}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Podkategoria:</div>
                        <div class="ai-detail-value">${category.subcategory || 'Nierozpoznana'}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Przeznaczenie:</div>
                        <div class="ai-detail-value">${category.intended_use || 'Nierozpoznane'}</div>
                    </div>
                    
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Kategoria cenowa:</div>
                        <div class="ai-detail-value">${category.price_category || 'Nierozpoznana'}</div>
                    </div>
                </div>
            `;
        }
        
        // Sekcja analizy wartości
        if (aiAnalysis.value && !aiAnalysis.value.error) {
            const value = aiAnalysis.value;
            content += `
                <div class="ai-details-section">
                    <h3>Analiza wartości</h3>
                    
                    ${value.value_analysis && value.value_analysis.estimated_value_range ? `
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Szacowana wartość:</div>
                        <div class="ai-detail-value">
                            ${value.value_analysis.estimated_value_range.low} - ${value.value_analysis.estimated_value_range.high} 
                            ${value.value_analysis.estimated_value_range.currency || 'PLN'}
                        </div>
                    </div>
                    ` : ''}
                    
                    ${value.value_analysis && value.value_analysis.value_assessment ? `
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Ocena ceny:</div>
                        <div class="ai-detail-value">
                            <span class="badge ${
                                value.value_analysis.value_assessment === 'fair' ? 'badge-fair' : 
                                value.value_analysis.value_assessment === 'overpriced' ? 'badge-over' : 
                                value.value_analysis.value_assessment === 'underpriced' ? 'badge-under' : ''
                            }">${value.value_analysis.value_assessment}</span>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${value.selling_points && value.selling_points.length > 0 ? `
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Główne zalety:</div>
                        <div class="ai-detail-value">
                            <ul class="ai-list">
                                ${value.selling_points.map(item => `<li>${item}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${value.concerns && value.concerns.length > 0 ? `
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Potencjalne problemy:</div>
                        <div class="ai-detail-value">
                            <ul class="ai-list">
                                ${value.concerns.map(item => `<li>${item}</li>`).join('')}
                            </ul>
                        </div>
                    </div>
                    ` : ''}
                    
                    ${value.overall_recommendation ? `
                    <div class="ai-detail-item">
                        <div class="ai-detail-label">Rekomendacja:</div>
                        <div class="ai-detail-value">${value.overall_recommendation}</div>
                    </div>
                    ` : ''}
                </div>
            `;
        }
        
        // Wypełnij zawartość modalu
        aiDetailsContent.innerHTML = content || '<p>Brak szczegółowych danych analizy AI</p>';
        
        // Wyświetl modal
        aiDetailsModal.style.display = 'block';
        
    } catch (error) {
        console.error('Błąd wyświetlania szczegółów AI:', error);
        alert('Wystąpił błąd podczas wyświetlania szczegółów analizy AI');
    }
}

// Dodajemy funkcję do wyświetlania szczegółów technicznych roweru
function showBikeDetails(encodedData) {
    const bikeDetails = JSON.parse(decodeURIComponent(encodedData));
    const detailsModal = document.getElementById('bikeDetailsModal');
    const detailsContent = document.getElementById('bikeDetailsContent');
    
    let content = `
        <h3>${bikeDetails.title || 'Szczegóły techniczne roweru'}</h3>
        <div class="tech-details-grid">
    `;
    
    // Dodanie opisu
    if (bikeDetails.description) {
        content += `
            <div class="tech-description">
                <h4>Opis</h4>
                <p>${bikeDetails.description}</p>
            </div>
        `;
    }
    
    // Mapowanie kluczy z parameters na nazwy właściwości
    const parameterMapping = {
        'Marka': 'brand',
        'Stan': 'condition',
        'Kolor': 'color',
        'Materiał ramy': 'frame_material',
        'Typ hamulca': 'brake_type',
        'Rodzaj przerzutki': 'derailleur_type',
        'Rozmiar koła': 'wheel_size',
        'Typ sprzedawcy': 'seller_type',
        'Rozmiar ramy': 'frame_size_desc'
    };

    // Funkcja pomocnicza do sprawdzania czy wartość jest pusta
    const hasValue = (value) => value !== null && value !== undefined && value !== '';

    // Najpierw sprawdzamy parametry z obiektu parameters
    if (bikeDetails.parameters) {
        for (const [key, value] of Object.entries(bikeDetails.parameters)) {
            if (hasValue(value)) {
                const propertyName = parameterMapping[key];
                if (propertyName) {
                    // Jeśli parametr ma odpowiadającą właściwość, używamy wartości z parameters
                    content += `<div class="tech-label">${key}:</div><div class="tech-value">${value}</div>`;
                } else {
                    // Jeśli to nowy parametr, dodajemy go
                    content += `<div class="tech-label">${key}:</div><div class="tech-value">${value}</div>`;
                }
            }
        }
    }

    // Następnie sprawdzamy pozostałe właściwości, które nie zostały jeszcze wyświetlone
    const displayedProperties = new Set(Object.values(parameterMapping));
    
    // Dodanie podstawowych informacji, które nie są w parameters
    if (hasValue(bikeDetails.price)) content += `<div class="tech-label">Cena:</div><div class="tech-value">${bikeDetails.price.toLocaleString()} zł</div>`;
    if (hasValue(bikeDetails.year)) content += `<div class="tech-label">Rok:</div><div class="tech-value">${bikeDetails.year}</div>`;
    if (hasValue(bikeDetails.weight)) content += `<div class="tech-label">Waga:</div><div class="tech-value">${bikeDetails.weight}</div>`;
    if (hasValue(bikeDetails.gears)) content += `<div class="tech-label">Przerzutki:</div><div class="tech-value">${bikeDetails.gears}</div>`;
    if (hasValue(bikeDetails.suspension)) content += `<div class="tech-label">Amortyzacja:</div><div class="tech-value">${bikeDetails.suspension}</div>`;
    if (hasValue(bikeDetails.bike_type)) content += `<div class="tech-label">Typ roweru:</div><div class="tech-value">${bikeDetails.bike_type}</div>`;
    
    content += `</div>`;

    // Dodanie sekcji analizy AI, jeśli jest dostępna
    if (bikeDetails.ai_analysis) {
        content += `
            <div class="ai-analysis-section">
                <h4>Analiza AI</h4>
                <div class="ai-details-grid">
        `;

        // Szczegóły rozpoznane przez AI
        if (bikeDetails.ai_analysis.parsed_details) {
            const details = bikeDetails.ai_analysis.parsed_details;
            if (details.bicycle_type) content += `<div class="ai-label">Typ roweru:</div><div class="ai-value">${details.bicycle_type}</div>`;
            if (details.brand) content += `<div class="ai-label">Marka:</div><div class="ai-value">${details.brand}</div>`;
            if (details.model) content += `<div class="ai-label">Model:</div><div class="ai-value">${details.model}</div>`;
            if (details.frame_size) content += `<div class="ai-label">Rozmiar ramy:</div><div class="ai-value">${details.frame_size}</div>`;
            if (details.frame_material) content += `<div class="ai-label">Materiał ramy:</div><div class="ai-value">${details.frame_material}</div>`;
            if (details.wheel_size) content += `<div class="ai-label">Rozmiar kół:</div><div class="ai-value">${details.wheel_size}</div>`;
            if (details.groupset) content += `<div class="ai-label">Osprzęt:</div><div class="ai-value">${details.groupset}</div>`;
            if (details.year) content += `<div class="ai-label">Rok produkcji:</div><div class="ai-value">${details.year}</div>`;
            if (details.condition) content += `<div class="ai-label">Stan:</div><div class="ai-value">${details.condition}</div>`;
        }

        // Analiza wartości
        if (bikeDetails.ai_analysis.value && bikeDetails.ai_analysis.value.value_analysis) {
            const value = bikeDetails.ai_analysis.value.value_analysis;
            if (value.estimated_value_range) {
                content += `
                    <div class="ai-label">Szacowana wartość:</div>
                    <div class="ai-value">${value.estimated_value_range.low} - ${value.estimated_value_range.high} ${value.estimated_value_range.currency || 'PLN'}</div>
                `;
            }
            if (value.value_assessment) {
                content += `
                    <div class="ai-label">Ocena ceny:</div>
                    <div class="ai-value">
                        <span class="badge ${
                            value.value_assessment === 'fair' ? 'badge-fair' : 
                            value.value_assessment === 'overpriced' ? 'badge-over' : 
                            value.value_assessment === 'underpriced' ? 'badge-under' : ''
                        }">${value.value_assessment}</span>
                    </div>
                `;
            }
        }

        // Główne zalety i problemy
        if (bikeDetails.ai_analysis.value) {
            if (bikeDetails.ai_analysis.value.selling_points && bikeDetails.ai_analysis.value.selling_points.length > 0) {
                content += `
                    <div class="ai-label">Główne zalety:</div>
                    <div class="ai-value">
                        <ul class="ai-list">
                            ${bikeDetails.ai_analysis.value.selling_points.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }
            if (bikeDetails.ai_analysis.value.concerns && bikeDetails.ai_analysis.value.concerns.length > 0) {
                content += `
                    <div class="ai-label">Potencjalne problemy:</div>
                    <div class="ai-value">
                        <ul class="ai-list">
                            ${bikeDetails.ai_analysis.value.concerns.map(item => `<li>${item}</li>`).join('')}
                        </ul>
                    </div>
                `;
            }
            if (bikeDetails.ai_analysis.value.overall_recommendation) {
                content += `
                    <div class="ai-label">Rekomendacja:</div>
                    <div class="ai-value">${bikeDetails.ai_analysis.value.overall_recommendation}</div>
                `;
            }
        }

        content += `
                </div>
            </div>
        `;
    }
    
    content += `
        <div class="tech-details-actions">
            <a href="${bikeDetails.url}" target="_blank" class="tech-btn">Zobacz ogłoszenie</a>
            <button class="tech-btn close-btn" onclick="document.getElementById('bikeDetailsModal').style.display='none'">Zamknij</button>
        </div>
    `;
    
    detailsContent.innerHTML = content;
    detailsModal.style.display = 'block';
} 