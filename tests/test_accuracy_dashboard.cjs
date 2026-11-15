const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

class Element {
    constructor(tagName, id = '') {
        this.tagName = tagName.toUpperCase();
        this.id = id;
        this.children = [];
        this.parentElement = null;
        this.className = '';
        this.style = { setProperty() {}, removeProperty() {} };
        this.classList = {
            add: name => { this.className += ` ${name}`; },
            remove: name => {
                this.className = this.className.split(' ').filter(value => value !== name).join(' ');
            },
            contains: name => this.className.split(' ').includes(name)
        };
    }

    appendChild(child) {
        child.parentElement = this;
        this.children.push(child);
        return child;
    }

    replaceChildren(...children) {
        this.children.forEach(child => { child.parentElement = null; });
        this.children = [];
        children.forEach(child => this.appendChild(child));
    }

    set innerHTML(value) {
        this.replaceChildren();
        this.content = value;
    }

    get textContent() {
        return this.children.length
            ? this.children.map(child => child.textContent).join('')
            : this.content || '';
    }

    set textContent(value) {
        this.replaceChildren();
        this.content = value;
    }

    querySelectorAll(selector) {
        return this.children.flatMap(child => {
            const matches = selector.startsWith('.')
                ? child.classList.contains(selector.slice(1))
                : child.tagName.toLowerCase() === selector;
            return [...(matches ? [child] : []), ...child.querySelectorAll(selector)];
        });
    }

    querySelector(selector) {
        return this.querySelectorAll(selector)[0] || null;
    }

    insertRow() {
        return this.appendChild(new Element('tr'));
    }

    remove() {
        this.parentElement.children = this.parentElement.children.filter(child => child !== this);
        this.parentElement = null;
    }
}

function loadDashboard() {
    const body = new Element('body');
    for (const id of [
        'summaryCards', 'bestAlgorithmCard', 'bestPerformanceCard', 'bestTopPredictionCard',
        'bestWinningPredictionCard', 'bestPatternPredictionCard', 'bestUltimatePredictionCard',
        'evaluationTiming', 'loadingOverlay', 'gameTypeFilter'
    ]) {
        body.appendChild(new Element('div', id));
    }
    for (const id of ['matchDistributionChart', 'algorithmPerformanceChart']) {
        body.appendChild(new Element('div')).appendChild(new Element('canvas', id));
    }
    for (const id of ['gameBreakdownTable', 'recentSubmissionsTable']) {
        const table = body.appendChild(new Element('table', id));
        table.appendChild(new Element('thead'));
        table.appendChild(new Element('tbody'));
    }
    const document = {
        getElementById: id => {
            const find = element => element.id === id
                ? element : element.children.map(find).find(Boolean);
            return find(body) || null;
        },
        createElement: tagName => new Element(tagName),
        querySelectorAll: selector => body.querySelectorAll(selector),
        querySelector: selector => {
            const [id, child] = selector.split(' ');
            return document.getElementById(id.slice(1))?.querySelector(child) || null;
        },
        addEventListener() {}
    };
    const charts = [];
    const errors = [];
    const context = vm.createContext({
        document,
        console: { error: (...args) => errors.push(args) },
        escapeHtml: value => String(value),
        Chart: class {
            constructor(canvas) {
                assert.ok(canvas, 'The chart canvas must still exist after an empty filter');
                this.canvas = canvas;
                this.destroyed = false;
                charts.push(this);
            }
            destroy() {
                assert.equal(this.destroyed, false, 'A chart must be destroyed only once');
                this.destroyed = true;
            }
        }
    });
    const template = fs.readFileSync(
        path.join(__dirname, '..', 'app', 'templates', 'accuracy_dashboard.html'), 'utf8'
    );
    vm.runInContext(template.match(/<script>([\s\S]*?)<\/script>/)[1], context);
    return { context, document, charts, errors };
}

function analysis() {
    const prediction = { avg_matches_per_prediction: 1, total_predictions: 1 };
    return {
        evaluation_context: {
            snapshot_timing_counts: { earlier_day_snapshot: 0, retrospective_or_unverified: 1 }
        },
        total_submissions: 1,
        match_distribution: {
            total_predictions: 4,
            average_matches: 1,
            distribution: {
                '0_matches': 0, '1_match': 4, '2_matches': 0, '3_matches': 0,
                '4_matches': 0, '5_matches': 0, '6_matches_jackpot': 0
            }
        },
        best_algorithm: null,
        prediction_types: {
            top_predictions: prediction, winning_predictions: prediction,
            pattern_predictions: prediction, ultimate_predictions: prediction
        },
        game_breakdown: {
            'Grand Lotto 6/55': {
                submissions: 1, total_predictions: 4, avg_matches: 1,
                best_match: 1, expected_matches_per_ticket: 36 / 55
            }
        },
        recent_accuracy: [],
        best_performances: {}
    };
}

test('empty game filters preserve charts and table headers and recover on success or refresh', async () => {
    const { context, document, charts, errors } = loadDashboard();
    const responses = [analysis(), null, null, analysis(), analysis()];
    context.fetch = async () => {
        const data = responses.shift();
        return {
            status: data ? 200 : 404,
            json: async () => data
                ? { success: true, data } : { success: false, error: 'No accuracy data found' }
        };
    };
    const canvases = ['matchDistributionChart', 'algorithmPerformanceChart']
        .map(id => document.getElementById(id));
    const tables = ['gameBreakdownTable', 'recentSubmissionsTable']
        .map(id => document.getElementById(id));
    const headers = tables.map(table => table.querySelector('thead'));
    await context.loadAccuracyAnalysis();
    for (let emptyFilter = 0; emptyFilter < 2; emptyFilter++) {
        await context.loadAccuracyAnalysis();
        canvases.forEach(canvas => assert.equal(document.getElementById(canvas.id), canvas));
        tables.forEach((table, index) => {
            assert.equal(table.querySelector('thead'), headers[index]);
            assert.match(table.querySelector('tbody').textContent, /No accuracy data/);
        });
        assert.equal(charts.filter(chart => !chart.destroyed).length, 0);
        assert.equal(document.getElementById('evaluationTiming').textContent, '');
        assert.match(document.getElementById('bestUltimatePredictionCard').textContent, /No accuracy data/);
    }
    for (let successfulLoad = 0; successfulLoad < 2; successfulLoad++) {
        await context.loadAccuracyAnalysis();
        assert.match(document.getElementById('summaryCards').textContent, /Total Submissions/);
        assert.equal(document.querySelectorAll('.accuracy-empty-state').length, 0);
        assert.equal(tables[0].querySelector('tbody').children.length, 1);
        assert.equal(charts.filter(chart => !chart.destroyed).length, 2);
    }
    assert.deepEqual(errors, []);
});

test('failed requests show an error and can be retried without destroying the dashboard', async () => {
    const { context, document, charts, errors } = loadDashboard();
    context.fetch = async () => { throw new Error('Connection lost'); };
    await context.loadAccuracyAnalysis();
    assert.equal(errors.length, 1);
    assert.match(document.getElementById('summaryCards').textContent, /error|Unable/i);
    context.fetch = async () => ({ status: 200, json: async () => ({ success: true, data: analysis() }) });
    await context.loadAccuracyAnalysis();
    assert.match(document.getElementById('summaryCards').textContent, /Total Submissions/);
    assert.equal(charts.filter(chart => !chart.destroyed).length, 2);
    assert.equal(errors.length, 1);
});
