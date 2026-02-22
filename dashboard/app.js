document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

let gamesData = [];
let projectionsData = [];
let currentFilter = 'today';
let currentProjStat = 'PTS';
let searchQuery = '';

// Pagination State
let currentGamesPage = 1;
const GAMES_PER_PAGE = 5;
let gameSearchQuery = '';

// Slideshow State
const slideshowCategories = ['PTS', 'REB', 'AST', 'PRA'];
let currentSlideIndex = 0;
let slideshowInterval = null;

const teamNames = {
    "ATL": "Hawks", "BOS": "Celtics", "BKN": "Nets", "CHA": "Hornets", "CHI": "Bulls",
    "CLE": "Cavaliers", "DAL": "Mavericks", "DEN": "Nuggets", "DET": "Pistons",
    "GSW": "Warriors", "HOU": "Rockets", "IND": "Pacers", "LAC": "Clippers",
    "LAL": "Lakers", "MEM": "Grizzlies", "MIA": "Heat", "MIL": "Bucks",
    "MIN": "Timberwolves", "NOP": "Pelicans", "NYK": "Knicks", "OKC": "Thunder",
    "ORL": "Magic", "PHI": "76ers", "PHX": "Suns", "POR": "Trail Blazers",
    "SAC": "Kings", "SAS": "Spurs", "TOR": "Raptors", "UTA": "Jazz", "WAS": "Wizards"
};

const teamCities = {
    "ATL": "Atlanta", "BOS": "Boston", "BKN": "Brooklyn", "CHA": "Charlotte", "CHI": "Chicago",
    "CLE": "Cleveland", "DAL": "Dallas", "DEN": "Denver", "DET": "Detroit", "GSW": "Golden State",
    "HOU": "Houston", "IND": "Indiana", "LAC": "LA Los Angeles", "LAL": "LA Los Angeles",
    "MEM": "Memphis", "MIA": "Miami", "MIL": "Milwaukee", "MIN": "Minnesota", "NOP": "New Orleans",
    "NYK": "New York NY", "OKC": "Oklahoma City", "ORL": "Orlando", "PHI": "Philadelphia",
    "PHX": "Phoenix", "POR": "Portland", "SAC": "Sacramento", "SAS": "San Antonio",
    "TOR": "Toronto", "UTA": "Utah", "WAS": "Washington"
};

const espnLogos = {
    "GSW": "gs", "NOP": "no", "NYK": "ny", "SAS": "sa", "UTA": "utah", "WAS": "wsh"
};

async function initDashboard() {
    try {
        await Promise.all([
            loadGames(),
            loadProjections()
        ]);

        setupEventListeners();
        renderDashboard();
    } catch (err) {
        console.error("Error loading dashboard data:", err);
        document.getElementById('metrics-grid').innerHTML = `<p class="loading-state">Failed to load data. Ensure local node server is running.</p>`;
    }
}

async function loadGames() {
    return new Promise((resolve, reject) => {
        Papa.parse('../data/upcoming_games.csv?v=' + new Date().getTime(), {
            download: true,
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                // Filter out Unknown_None games
                gamesData = results.data.filter(g => g.HOME_TEAM !== 'Unknown_None');
                resolve();
            },
            error: reject
        });
    });
}

async function loadProjections() {
    return new Promise((resolve, reject) => {
        Papa.parse('../data/upcoming_projections.csv?v=' + new Date().getTime(), {
            download: true,
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                projectionsData = results.data;
                resolve();
            },
            error: reject
        });
    });
}

function setupEventListeners() {
    const tabs = document.querySelectorAll('.tab');
    tabs.forEach(tab => {
        tab.addEventListener('click', (e) => {
            tabs.forEach(t => t.classList.remove('active'));
            e.target.classList.add('active');
            currentFilter = e.target.dataset.filter;
            currentGamesPage = 1; // Reset page on tab switch
            renderGames();
        });
    });

    // Pagination Listeners
    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    if (prevBtn && nextBtn) {
        prevBtn.addEventListener('click', () => {
            if (currentGamesPage > 1) {
                currentGamesPage--;
                renderGames();
            }
        });
        nextBtn.addEventListener('click', () => {
            currentGamesPage++;
            renderGames();
        });
    }

    // Games Search Filter
    const gameSearchInput = document.getElementById('game-search');
    if (gameSearchInput) {
        gameSearchInput.addEventListener('input', (e) => {
            gameSearchQuery = e.target.value.toLowerCase();
            currentGamesPage = 1; // reset page on search
            renderGames();
        });
    }

    // SPA Navigation
    const navBtns = document.querySelectorAll('.nav-btn');
    navBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            navBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const targetId = btn.getAttribute('data-target');
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.getElementById(targetId).classList.add('active');
        });
    });

    // Projections Stat Filter
    const filterSelect = document.getElementById('full-proj-stat-filter');
    if (filterSelect) {
        filterSelect.addEventListener('change', (e) => {
            currentProjStat = e.target.value;
            renderProjections();
        });
    }

    // Player Search Filter
    const searchInput = document.getElementById('player-search');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            searchQuery = e.target.value.toLowerCase();
            renderProjections();
        });
    }
}

function renderDashboard() {
    renderMetrics();
    renderGames();
    renderProjections();
    startSlideshow();
}

// Dynamically pick the earliest date that has games as "Today"
function getEarliestDate() {
    if (gamesData.length > 0) {
        const dates = gamesData.map(g => g.GAME_DATE).filter(d => d);
        dates.sort();
        return dates[0];
    }

    // Fallback if no games exist (timezone safe)
    const today = new Date();
    const tzOffset = today.getTimezoneOffset() * 60000;
    return new Date(today - tzOffset).toISOString().split('T')[0];
}

function renderMetrics() {
    const todayStr = getEarliestDate();

    // 1. Games Today
    const gamesToday = gamesData.filter(g => g.GAME_DATE === todayStr).length;

    // 2. Upcoming Scheduled
    const upcomingGames = gamesData.filter(g => g.GAME_DATE > todayStr).length;

    // Clean projections
    const validProjections = projectionsData.filter(p => !isNaN(parseFloat(p.PREDICTED_PTS)));

    // 3. Top Projected Scorer
    const scorers = [...validProjections].sort((a, b) => parseFloat(b.PREDICTED_PTS) - parseFloat(a.PREDICTED_PTS));
    const topScorer = scorers.length > 0 ? scorers[0] : null;

    // 4. Top Projected PRA
    const praLeaders = [...validProjections].filter(p => !isNaN(parseFloat(p.PREDICTED_PRA))).sort((a, b) => parseFloat(b.PREDICTED_PRA) - parseFloat(a.PREDICTED_PRA));
    const topPra = praLeaders.length > 0 ? praLeaders[0] : null;

    const metricsGrid = document.getElementById('metrics-grid');
    metricsGrid.innerHTML = `
        <div class="metric-card">
            <div class="metric-icon">👥</div>
            <h3>Scheduled Games</h3>
            <div class="value">${gamesToday}</div>
            <div class="subtext">Games on ${todayStr}</div>
        </div>
        <div class="metric-card green">
            <div class="metric-icon">📅</div>
            <h3>Upcoming Matches</h3>
            <div class="value">${upcomingGames}</div>
            <div class="subtext">Total Scheduled Games</div>
        </div>
        <div class="metric-card purple">
            <div class="metric-icon">🔥</div>
            <h3>Top Proj. Scorer</h3>
            <div class="value" style="font-size: 1.6rem; padding-top: 0.5rem;">${topScorer ? topScorer.PLAYER_NAME : 'N/A'}</div>
            <div class="subtext">${topScorer ? parseFloat(topScorer.PREDICTED_PTS).toFixed(1) + ' PTS (' + (teamNames[topScorer.TEAM.trim().toUpperCase()] || topScorer.TEAM) + ')' : '--'}</div>
        </div>
        <div class="metric-card orange">
            <div class="metric-icon">⚡</div>
            <h3>Top Overall (PRA)</h3>
            <div class="value" style="font-size: 1.6rem; padding-top: 0.5rem;">${topPra ? topPra.PLAYER_NAME : 'N/A'}</div>
            <div class="subtext">${topPra ? parseFloat(topPra.PREDICTED_PRA).toFixed(1) + ' PRA (' + (teamNames[topPra.TEAM.trim().toUpperCase()] || topPra.TEAM) + ')' : '--'}</div>
        </div>
    `;
}

function renderGames() {
    const todayStr = getEarliestDate();
    const gamesList = document.getElementById('games-list');
    const subtitle = document.getElementById('schedule-subtitle');

    let filteredGames = [];
    if (currentFilter === 'today') {
        filteredGames = gamesData.filter(g => g.GAME_DATE === todayStr);
        subtitle.textContent = `${todayStr} • ${filteredGames.length} games scheduled`;
    } else {
        filteredGames = gamesData.filter(g => g.GAME_DATE > todayStr);
        subtitle.textContent = `Upcoming Schedule • ${filteredGames.length} games scheduled`;
    }

    if (filteredGames.length === 0) {
        gamesList.innerHTML = `<p class="loading-state">No games found.</p>`;
        return;
    }

    // Filter by Search Query
    if (gameSearchQuery) {
        const queryTokens = gameSearchQuery.toLowerCase().trim().split(/\s+/);
        filteredGames = filteredGames.filter(g => {
            const hClean = g.HOME_TEAM.trim().toUpperCase();
            const aClean = g.AWAY_TEAM.trim().toUpperCase();

            const hCity = (teamCities[hClean] || '').toLowerCase();
            const hName = (teamNames[hClean] || '').toLowerCase();
            const hTri = hClean.toLowerCase();

            const aCity = (teamCities[aClean] || '').toLowerCase();
            const aName = (teamNames[aClean] || '').toLowerCase();
            const aTri = aClean.toLowerCase();

            const combinedStr = `${hTri} ${hCity} ${hName} vs @ ${aTri} ${aCity} ${aName}`;

            return queryTokens.every(t => combinedStr.includes(t));
        });
    }

    // Sort games chronologically by date first, then by tip-off time
    filteredGames.sort((a, b) => {
        if (a.GAME_DATE !== b.GAME_DATE) {
            return a.GAME_DATE.localeCompare(b.GAME_DATE);
        }

        const parseTime = (timeStr) => {
            if (!timeStr || timeStr === 'TBD' || timeStr.includes('undefined')) return 2400;
            let match = timeStr.match(/(\d+):(\d+)\s*(am|pm)/i);
            if (!match) return 2400;
            let hours = parseInt(match[1]);
            let mins = parseInt(match[2]);
            let ampm = match[3].toLowerCase();
            if (ampm === 'pm' && hours < 12) hours += 12;
            if (ampm === 'am' && hours === 12) hours = 0;
            return hours * 60 + mins;
        };
        return parseTime(a.GAME_TIME) - parseTime(b.GAME_TIME);
    });

    // Pagination Logic
    const totalPages = Math.ceil(filteredGames.length / GAMES_PER_PAGE);
    if (currentGamesPage > totalPages && totalPages > 0) {
        currentGamesPage = totalPages;
    }

    const prevBtn = document.getElementById('prev-page');
    const nextBtn = document.getElementById('next-page');
    const pageIndicator = document.getElementById('page-indicator');

    if (prevBtn && nextBtn && pageIndicator) {
        prevBtn.disabled = currentGamesPage <= 1;
        nextBtn.disabled = currentGamesPage >= totalPages;
        pageIndicator.textContent = `${totalPages > 0 ? currentGamesPage : 0} / ${totalPages}`;
    }

    const startIndex = (currentGamesPage - 1) * GAMES_PER_PAGE;
    const paginatedGames = filteredGames.slice(startIndex, startIndex + GAMES_PER_PAGE);

    gamesList.innerHTML = paginatedGames.map(g => {
        const isToday = g.GAME_DATE === todayStr;
        return `
            <div class="game-card">
                <div class="team home">
                    <div style="display: flex; align-items: center; justify-content: flex-start; gap: 0.8rem;">
                        <img src="https://a.espncdn.com/i/teamlogos/nba/500/scoreboard/${(espnLogos[g.HOME_TEAM.trim().toUpperCase()] || g.HOME_TEAM.trim()).toLowerCase()}.png" alt="${g.HOME_TEAM}" style="width: 40px; height: 40px; object-fit: contain;">
                        <div>
                            <div class="team-name">${teamNames[g.HOME_TEAM.trim().toUpperCase()] || g.HOME_TEAM}</div>
                            <div class="team-role" style="text-align: left;">★ Home</div>
                        </div>
                    </div>
                </div>
                <div class="match-info">
                    <div class="time-badge" style="padding: 0.5rem 1rem; ${!isToday ? 'background: var(--accent-blue);' : ''}">
                        <div style="font-size: 1.1rem; font-weight: bold;">${g.GAME_TIME}</div>
                        <div style="font-size: 0.8rem; opacity: 0.8; margin-top: 0.1rem;">${g.GAME_DATE}</div>
                    </div>
                    <div class="vs">VS</div>
                </div>
                <div class="team away">
                    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 0.8rem;">
                        <img src="https://a.espncdn.com/i/teamlogos/nba/500/scoreboard/${(espnLogos[g.AWAY_TEAM.trim().toUpperCase()] || g.AWAY_TEAM.trim()).toLowerCase()}.png" alt="${g.AWAY_TEAM}" style="width: 40px; height: 40px; object-fit: contain;">
                        <div style="text-align: right;">
                            <div class="team-name">${teamNames[g.AWAY_TEAM.trim().toUpperCase()] || g.AWAY_TEAM}</div>
                            <div class="team-role">Away ↗</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderProjections() {
    renderProjectionList(document.getElementById('full-players-list'), 100);
}

function renderProjectionList(container, limit, overrideStat = null) {
    if (!container) return;

    const activeStat = overrideStat || currentProjStat;
    const statCol = `PREDICTED_${activeStat}`;

    // Ensure players have data for this stat
    let validPlayers = projectionsData.filter(p => !isNaN(parseFloat(p[statCol])));

    if (searchQuery && !overrideStat) { // Don't filter slideshow by search
        const queryTokens = searchQuery.toLowerCase().trim().split(/\s+/);
        validPlayers = validPlayers.filter(p => {
            const tClean = p.TEAM.trim().toUpperCase();
            const tCity = (teamCities[tClean] || '').toLowerCase();
            const tName = (teamNames[tClean] || '').toLowerCase();
            const tTri = tClean.toLowerCase();
            const combinedStr = `${p.PLAYER_NAME.toLowerCase()} ${tTri} ${tCity} ${tName}`;

            return queryTokens.every(t => combinedStr.includes(t));
        });
    }

    validPlayers.sort((a, b) => parseFloat(b[statCol]) - parseFloat(a[statCol]));

    const topPlayers = validPlayers.slice(0, limit);

    if (topPlayers.length === 0) {
        container.innerHTML = `<p class="loading-state">No projections found.</p>`;
        return;
    }

    container.innerHTML = topPlayers.map(p => {
        const pPts = parseFloat(p.PREDICTED_PTS).toFixed(1);
        const pReb = parseFloat(p.PREDICTED_REB).toFixed(1);
        const pAst = parseFloat(p.PREDICTED_AST).toFixed(1);
        const pPra = parseFloat(p.PREDICTED_PRA).toFixed(1);

        const ptsRatio = p.BASELINE_5G_PTS ? (parseFloat(p.BASELINE_5G_PTS) / parseFloat(p.PREDICTED_PTS)) : 1;
        const ptsBase = p.BASELINE_5G_PTS ? parseFloat(p.BASELINE_5G_PTS) : parseFloat(p.PREDICTED_PTS);
        const rebBase = parseFloat(p.PREDICTED_REB) * ptsRatio;
        const astBase = parseFloat(p.PREDICTED_AST) * ptsRatio;
        const praBase = parseFloat(p.PREDICTED_PRA) * ptsRatio;

        const ptsDiff = parseFloat((parseFloat(p.PREDICTED_PTS) - ptsBase).toFixed(1));
        const rebDiff = parseFloat((parseFloat(p.PREDICTED_REB) - rebBase).toFixed(1));
        const astDiff = parseFloat((parseFloat(p.PREDICTED_AST) - astBase).toFixed(1));
        const praDiff = parseFloat((parseFloat(p.PREDICTED_PRA) - praBase).toFixed(1));

        let primaryVal = 0, primaryLabel = '';
        let microStats = [];
        let activeDiff = 0;

        if (activeStat === 'PTS') {
            primaryVal = pPts; primaryLabel = 'PTS'; activeDiff = ptsDiff;
            microStats = [{ l: 'REB', v: pReb, d: rebDiff }, { l: 'AST', v: pAst, d: astDiff }, { l: 'PRA', v: pPra, d: praDiff }];
        } else if (activeStat === 'REB') {
            primaryVal = pReb; primaryLabel = 'REB'; activeDiff = rebDiff;
            microStats = [{ l: 'PTS', v: pPts, d: ptsDiff }, { l: 'AST', v: pAst, d: astDiff }, { l: 'PRA', v: pPra, d: praDiff }];
        } else if (activeStat === 'AST') {
            primaryVal = pAst; primaryLabel = 'AST'; activeDiff = astDiff;
            microStats = [{ l: 'PTS', v: pPts, d: ptsDiff }, { l: 'REB', v: pReb, d: rebDiff }, { l: 'PRA', v: pPra, d: praDiff }];
        } else {
            primaryVal = pPra; primaryLabel = 'PRA'; activeDiff = praDiff;
            microStats = [{ l: 'PTS', v: pPts, d: ptsDiff }, { l: 'REB', v: pReb, d: rebDiff }, { l: 'AST', v: pAst, d: astDiff }];
        }

        const upArrowSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; margin-top:2px;"><path d="M12 19V5M5 12l7-7 7 7"/></svg>`;
        const downArrowSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; margin-top:2px;"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>`;
        const dashSvg = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px; margin-top:2px;"><rect x="4" y="10" width="16" height="4" rx="2" ry="2"/></svg>`;

        let diffIndicator = '';
        if (activeDiff > 0) {
            diffIndicator = `<div class="proj-diff" style="color: var(--accent-green); display: flex; align-items: flex-start; margin-top: 0.8rem; font-size: 0.85rem; font-weight: 600;">${upArrowSvg}<span>${Math.abs(activeDiff).toFixed(1)} projected difference</span></div>`;
        } else if (activeDiff < 0) {
            diffIndicator = `<div class="proj-diff" style="color: #ef4444; display: flex; align-items: flex-start; margin-top: 0.8rem; font-size: 0.85rem; font-weight: 600;">${downArrowSvg}<span>${Math.abs(activeDiff).toFixed(1)} projected difference</span></div>`;
        } else {
            diffIndicator = `<div class="proj-diff" style="color: #3b82f6; display: flex; align-items: flex-start; margin-top: 0.8rem; font-size: 0.85rem; font-weight: 600;">${dashSvg}<span>Avg Match</span></div>`;
        }

        const microHtml = microStats.map(m => {
            let hue = 'white';
            let bd = 'var(--border-color)';
            if (m.d > 0) { hue = 'rgba(34, 197, 94, 0.08)'; bd = 'rgba(34, 197, 94, 0.3)'; }
            else if (m.d < 0) { hue = 'rgba(239, 68, 68, 0.08)'; bd = 'rgba(239, 68, 68, 0.3)'; }
            else { hue = 'rgba(59, 130, 246, 0.08)'; bd = 'rgba(59, 130, 246, 0.3)'; }
            return `<div class="micro-stat" style="background: ${hue}; border-color: ${bd};">${m.l} <strong>${m.v}</strong></div>`;
        }).join('');

        return `
            <div class="player-card">
                <div class="player-info">
                    <h4>${p.PLAYER_NAME}</h4>
                    <p>${teamNames[p.TEAM.trim().toUpperCase()] || p.TEAM} vs ${teamNames[p.OPPONENT.trim().toUpperCase()] || p.OPPONENT}</p>
                    <div class="stat-grid">
                        ${microHtml}
                    </div>
                    ${diffIndicator}
                </div>
                <div class="player-stats">
                    <div class="stat-primary">${primaryVal} <br/> <span style="font-size: 1.2rem; color: var(--accent-orange); opacity: 0.9;">${primaryLabel}</span></div>
                </div>
            </div>
        `;
    }).join('');
}

// --- Slideshow Logic ---
function startSlideshow() {
    if (slideshowInterval) clearInterval(slideshowInterval);
    renderSlideshowTick();
    slideshowInterval = setInterval(() => {
        currentSlideIndex = (currentSlideIndex + 1) % slideshowCategories.length;
        renderSlideshowTick();
    }, 5000); // Rotate every 5 seconds
}

function renderSlideshowTick() {
    const listEl = document.getElementById('slideshow-players-list');
    const titleEl = document.getElementById('slideshow-title');
    const progressEl = document.getElementById('slideshow-progress');

    if (!listEl || !titleEl) return;

    const stat = slideshowCategories[currentSlideIndex];
    let label = stat;
    if (stat === 'PTS') label = 'Points (PTS)';
    if (stat === 'REB') label = 'Rebounds (REB)';
    if (stat === 'AST') label = 'Assists (AST)';
    if (stat === 'PRA') label = 'PRA (Pts + Reb + Ast)';

    // Fade out
    listEl.style.opacity = '0';
    listEl.style.transform = 'translateY(5px)';

    // Reset progress bar animation
    if (progressEl) {
        progressEl.style.transition = 'none';
        progressEl.style.width = '0%';
    }

    setTimeout(() => {
        // Update Title & DOM
        titleEl.innerHTML = `Top 5 Projected <span>${label}</span>`;
        renderProjectionList(listEl, 5, stat);

        // Fade in
        listEl.style.opacity = '1';
        listEl.style.transform = 'translateY(0)';

        // Start progress bar animation
        if (progressEl) {
            // Force reflow to ensure transition runs from 0
            progressEl.offsetHeight;
            progressEl.style.transition = 'width 5s linear';
            progressEl.style.width = '100%';
        }
    }, 400); // 400ms CSS transition
}
