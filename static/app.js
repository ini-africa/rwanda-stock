document.addEventListener('DOMContentLoaded', () => {
    const stockSelect = document.getElementById('stock-select');
    let mainChart = null;
    let currentSymbol = null;

    // Initialize Chart
    const ctx = document.getElementById('mainChart').getContext('2d');
    
    function initChart() {
        mainChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Price (RWF)',
                    data: [],
                    borderColor: '#38bdf8',
                    backgroundColor: 'rgba(56, 189, 248, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#94a3b8',
                            maxTicksLimit: 8
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
            }
        });
    }

    async function fetchStocks() {
        try {
            const [stocksRes, statsRes, bondsRes] = await Promise.all([
                fetch('/api/stocks'),
                fetch('/api/market-stats'),
                fetch('/api/bonds')
            ]);

            const stocks = await stocksRes.json();
            const stats = await statsRes.json();
            const bonds = await bondsRes.json();

            updateDashboard(stocks, stats, bonds);
            
            // Set initial selection if null
            if (!currentSymbol && stocks.length > 0) {
                currentSymbol = stocks[0].symbol;
                updateChart(currentSymbol);
            }
        } catch (error) {
            console.error('Error fetching data:', error);
        }
    }

    function updateDashboard(stocks, stats, bonds) {
        const tableBody = document.querySelector('#stocks-table tbody');
        const topMovers = document.getElementById('top-movers');
        const statsGrid = document.getElementById('market-stats');
        const bondsBody = document.querySelector('#bonds-table tbody');
        
        // Clear existing
        tableBody.innerHTML = '';
        topMovers.innerHTML = '';
        stockSelect.innerHTML = '';
        statsGrid.innerHTML = '';
        bondsBody.innerHTML = '';

        // Update Market Stats
        if (stats) {
            stats.forEach(stat => {
                const card = document.createElement('div');
                card.className = 'card';
                card.style.padding = '1rem';
                card.innerHTML = `
                    <div style="color: var(--text-secondary); font-size: 0.875rem; margin-bottom: 0.5rem;">${stat.key}</div>
                    <div style="font-size: 1.25rem; font-weight: 600; color: var(--accent-color);">${stat.value}</div>
                `;
                statsGrid.appendChild(card);
            });
        }

        // Update Bonds
        if (bonds) {
            bonds.forEach(bond => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td style="font-weight: 600;">${bond.security}</td>
                    <td>${bond.coupon}</td>
                    <td>${bond.maturity}</td>
                    <td>${bond.price.toFixed(2)}</td>
                    <td>${bond.yield_percentage.toFixed(2)}%</td>
                `;
                bondsBody.appendChild(row);
            });
        }

        // Sort by absolute change for "Top Movers" (just taking first 3 for demo)
        const sortedStocks = [...stocks].sort((a, b) => Math.abs(b.change) - Math.abs(a.change));

        // Update Select
        stocks.forEach(stock => {
            const option = document.createElement('option');
            option.value = stock.symbol;
            option.textContent = `${stock.symbol} - ${stock.name}`;
            if (stock.symbol === currentSymbol) option.selected = true;
            stockSelect.appendChild(option);
        });

        // Update Top Movers (Top 3)
        sortedStocks.slice(0, 3).forEach(stock => {
            const card = document.createElement('div');
            card.className = 'card';
            const isPositive = stock.change >= 0;
            const changeClass = isPositive ? 'positive' : 'negative';
            const changeSign = isPositive ? '+' : '';
            
            card.innerHTML = `
                <div class="stock-header">
                    <div>
                        <div class="stock-symbol">${stock.symbol}</div>
                        <div class="stock-name">${stock.name}</div>
                    </div>
                    <div class="stock-change ${changeClass}">
                        ${changeSign}${stock.change.toFixed(2)}%
                    </div>
                </div>
                <div class="stock-price">RWF ${stock.current_price.toFixed(2)}</div>
            `;
            topMovers.appendChild(card);
        });

        // Update Table
        stocks.forEach(stock => {
            const row = document.createElement('tr');
            const isPositive = stock.change >= 0;
            const changeClass = isPositive ? 'positive' : 'negative';
            const changeSign = isPositive ? '+' : '';
            
            // Availability Logic
            // If volume > 0 or high/low exists, assume active
            const isAvailable = stock.volume > 0 || (stock.high && stock.high > 0);
            const availabilityText = isAvailable ? 'Active' : 'Inactive';
            const availabilityColor = isAvailable ? 'var(--positive-color)' : 'var(--text-secondary)';

            row.innerHTML = `
                <td style="font-weight: 600; color: var(--accent-color);">${stock.symbol}</td>
                <td>${stock.name}</td>
                <td>${stock.current_price.toFixed(2)}</td>
                <td><span class="stock-change ${changeClass}">${changeSign}${stock.change.toFixed(2)}%</span></td>
                <td>${stock.volume.toLocaleString()}</td>
                <td style="color: ${availabilityColor}; font-weight: 500;">${availabilityText}</td>
                <td><a href="https://www.rse.rw/RSE-Members-2/RSE-Members/" target="_blank" class="buy-btn">Buy</a></td>
            `;
            tableBody.appendChild(row);
        });
    }

    async function updateChart(symbol) {
        try {
            const response = await fetch(`/api/history/${symbol}`);
            const history = await response.json();
            
            const labels = history.map(h => new Date(h.timestamp).toLocaleTimeString());
            const data = history.map(h => h.price);

            mainChart.data.labels = labels;
            mainChart.data.datasets[0].data = data;
            mainChart.update();
        } catch (error) {
            console.error('Error fetching history:', error);
        }
    }

    // Event Listeners
    stockSelect.addEventListener('change', (e) => {
        currentSymbol = e.target.value;
        updateChart(currentSymbol);
    });

    // Init
    initChart();
    fetchStocks();

    // Auto-refresh every 5 seconds
    setInterval(fetchStocks, 5000);
    setInterval(() => {
        if (currentSymbol) updateChart(currentSymbol);
    }, 5000);

    // Calculator Logic
    const calcAmount = document.getElementById('calc-amount');
    const calcDuration = document.getElementById('calc-duration');
    const calcRate = document.getElementById('calc-rate');
    const calcInterest = document.getElementById('calc-interest');
    const calcMonthly = document.getElementById('calc-monthly');
    const calcTotal = document.getElementById('calc-total');

    function calculateReturns() {
        const amount = parseFloat(calcAmount.value) || 0;
        const duration = parseFloat(calcDuration.value) || 0;
        const rate = parseFloat(calcRate.value) || 0;

        // Simple Interest Formula: I = P * R * T
        const totalInterest = amount * (rate / 100) * duration;
        const totalReturn = amount + totalInterest;
        
        // Monthly Income (Interest / Months)
        const months = duration * 12;
        const monthlyIncome = months > 0 ? totalInterest / months : 0;

        calcInterest.textContent = `${totalInterest.toLocaleString()} RWF`;
        calcMonthly.textContent = `${monthlyIncome.toLocaleString(undefined, {maximumFractionDigits: 0})} RWF`;
        calcTotal.textContent = `${totalReturn.toLocaleString()} RWF`;
    }

    if (calcAmount && calcDuration && calcRate) {
        calcAmount.addEventListener('input', calculateReturns);
        calcDuration.addEventListener('input', calculateReturns);
        calcRate.addEventListener('input', calculateReturns);
        
        // Initial Calc
        calculateReturns();
    }
});
