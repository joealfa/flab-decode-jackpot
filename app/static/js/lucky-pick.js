function luckyPickRandomIndex(limit) {
    const values = new Uint32Array(1);
    // Reject the uneven tail so each index has the same probability.
    const ceiling = 2 ** 32 - (2 ** 32 % limit);
    do {
        globalThis.crypto.getRandomValues(values);
    } while (values[0] >= ceiling);
    return values[0] % limit;
}

function generateLuckyPicks(maxNumber, count) {
    if (![42, 45, 49, 55, 58].includes(maxNumber)) {
        throw new RangeError('Please select a supported game.');
    }
    if (!Number.isInteger(count) || count < 1 || count > 20) {
        throw new RangeError('Enter a whole number from 1 to 20.');
    }

    return Array.from({ length: count }, () => {
        const pool = Array.from({ length: maxNumber }, (_, index) => index + 1);
        for (let index = 0; index < 6; index++) {
            const selected = index + luckyPickRandomIndex(maxNumber - index);
            [pool[index], pool[selected]] = [pool[selected], pool[index]];
        }
        return pool.slice(0, 6).sort((a, b) => a - b);
    });
}

(() => {
    const modal = document.getElementById('luckyPickModal');
    const form = document.getElementById('luckyPickForm');
    const game = document.getElementById('luckyPickGame');
    const count = document.getElementById('luckyPickCount');
    const results = document.getElementById('luckyPickResults');
    const summary = document.getElementById('luckyPickSummary');
    const error = document.getElementById('luckyPickError');

    function clearResults() {
        results.replaceChildren();
        summary.textContent = '';
        error.textContent = '';
    }

    document.getElementById('luckyPickOpen').addEventListener('click', () => modal.showModal());
    document.getElementById('luckyPickClose').addEventListener('click', () => modal.close());
    modal.addEventListener('keydown', event => {
        if (event.key === 'Escape') {
            event.preventDefault();
            modal.close();
        }
    });
    modal.addEventListener('click', event => {
        if (event.target !== modal) return;
        const bounds = modal.getBoundingClientRect();
        if (event.clientX < bounds.left || event.clientX > bounds.right ||
            event.clientY < bounds.top || event.clientY > bounds.bottom) {
            modal.close();
        }
    });
    modal.addEventListener('close', () => {
        clearResults();
        form.reset();
    });
    form.addEventListener('input', clearResults);
    form.addEventListener('submit', event => {
        event.preventDefault();
        clearResults();
        if (!form.reportValidity()) return;

        let picks;
        try {
            picks = generateLuckyPicks(Number(game.value), Number(count.value));
        } catch (failure) {
            console.error('Lucky Pick generation failed:', failure);
            error.textContent = failure instanceof RangeError
                ? failure.message
                : 'Unable to generate picks. Please try again in a browser with secure random support.';
            return;
        }

        const fragment = document.createDocumentFragment();
        for (const numbers of picks) {
            const row = document.createElement('li');
            const balls = document.createElement('div');
            balls.className = 'prediction-numbers';
            for (const number of numbers) {
                const ball = document.createElement('span');
                ball.className = 'number-ball small';
                ball.textContent = String(number).padStart(2, '0');
                balls.appendChild(ball);
            }
            row.appendChild(balls);
            fragment.appendChild(row);
        }
        results.appendChild(fragment);
        summary.textContent = `${game.selectedOptions[0].textContent}: ${picks.length} ${
            picks.length === 1 ? 'combination' : 'combinations'} generated.`;
    });
})();
