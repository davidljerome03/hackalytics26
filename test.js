const fs = require('fs');
const Papa = require('papaparse');

const csvData = fs.readFileSync('data/upcoming_projections.csv', 'utf8');
const results = Papa.parse(csvData, { header: true, skipEmptyLines: true });
const projectionsData = results.data;

let currentProjStat = 'PTS';
let searchQuery = '';

const statCol = `PREDICTED_${currentProjStat}`;
let validPlayers = projectionsData.filter(p => !isNaN(parseFloat(p[statCol])));

if (searchQuery) {
    validPlayers = validPlayers.filter(p => p.PLAYER_NAME.toLowerCase().includes(searchQuery));
}

validPlayers.sort((a, b) => parseFloat(b[statCol]) - parseFloat(a[statCol]));
const topPlayers = validPlayers.slice(0, 100);

try {
    topPlayers.map(p => {
        const pPts = parseFloat(p.PREDICTED_PTS).toFixed(1);
        const pReb = parseFloat(p.PREDICTED_REB).toFixed(1);
        const pAst = parseFloat(p.PREDICTED_AST).toFixed(1);
        const pPra = parseFloat(p.PREDICTED_PRA).toFixed(1);

        const baseline = p.BASELINE_5G_PTS ? parseFloat(p.BASELINE_5G_PTS).toFixed(1) : pPts;
        const diff = (parseFloat(p.PREDICTED_PTS) - baseline).toFixed(1);
    });
    console.log("No rendering crash!");
} catch (e) {
    console.error(e);
}
