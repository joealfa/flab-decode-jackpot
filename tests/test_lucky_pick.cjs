const assert = require('node:assert/strict');
const { webcrypto } = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

function loadPicker(crypto = webcrypto) {
    const context = vm.createContext({
        crypto,
        document: { getElementById: () => ({ addEventListener() {} }) }
    });
    vm.runInContext(fs.readFileSync(
        path.join(__dirname, '..', 'app', 'static', 'js', 'lucky-pick.js'), 'utf8'
    ), context);
    return context;
}

test('each supported game generates the requested number of valid sorted picks', () => {
    const picker = loadPicker();
    for (const maximum of [42, 45, 49, 55, 58]) {
        for (const count of [1, 20]) {
            const picks = picker.generateLuckyPicks(maximum, count);
            assert.equal(picks.length, count);
            for (const pick of picks) {
                assert.equal(pick.length, 6);
                assert.equal(new Set(pick).size, 6);
                assert.ok(pick.every(number => Number.isInteger(number) &&
                    number >= 1 && number <= maximum));
                assert.ok(pick.every((number, index) => index === 0 || pick[index - 1] < number));
            }
        }
    }
});

test('unsupported games and invalid counts are rejected before using randomness', () => {
    const picker = loadPicker({
        getRandomValues() { throw new Error('Randomness should not be requested'); }
    });
    for (const maximum of [0, 6, 43, 59, '42', NaN]) {
        assert.throws(() => picker.generateLuckyPicks(maximum, 1), /supported game/);
    }
    for (const count of [0, -1, 21, 1.5, '2', NaN, Infinity]) {
        assert.throws(() => picker.generateLuckyPicks(42, count), /whole number from 1 to 20/);
    }
});

test('random selection rejects biased tail values and can choose both endpoints', () => {
    const values = [2 ** 32 - 1, 0, 41];
    let calls = 0;
    const picker = loadPicker({
        getRandomValues(buffer) {
            buffer[0] = values[calls++];
            return buffer;
        }
    });
    assert.equal(picker.luckyPickRandomIndex(42), 0);
    assert.equal(calls, 2);
    assert.equal(picker.luckyPickRandomIndex(42), 41);
});
