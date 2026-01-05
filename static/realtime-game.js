// ============================================
// BRAINRACE - Real-Time Multiplayer Game
// WebSocket-based live gameplay
// ============================================

class RealTimeGame {
    constructor() {
        this.playerName = sessionStorage.getItem('username') || 'Player';
        this.isHost = sessionStorage.getItem('isHost') === 'true';
        this.roomCode = ROOM_CODE;
        this.ws = null;
        this.answered = false;
        this.currentQuestion = null;

        // DOM Elements
        this.waitingRoom = document.getElementById('waiting-room');
        this.gameArea = document.getElementById('game-area');
        this.gameOver = document.getElementById('game-over');
        this.countdownOverlay = document.getElementById('countdown-overlay');
        this.answerOverlay = document.getElementById('answer-overlay');

        this.init();
    }

    init() {
        this.setupCopyButton();

        if (this.roomCode === 'create') {
            this.createRoom();
        } else {
            this.joinRoom();
        }
    }

    setupCopyButton() {
        const copyBtn = document.getElementById('copy-btn');
        const copyToast = document.getElementById('copy-toast');

        copyBtn.addEventListener('click', async () => {
            const code = document.getElementById('display-room-code').textContent;
            try {
                await navigator.clipboard.writeText(code);
                copyToast.classList.remove('hidden');
                setTimeout(() => copyToast.classList.add('hidden'), 2000);
            } catch (err) {
                const textArea = document.createElement('textarea');
                textArea.value = code;
                document.body.appendChild(textArea);
                textArea.select();
                document.execCommand('copy');
                document.body.removeChild(textArea);
                copyToast.classList.remove('hidden');
                setTimeout(() => copyToast.classList.add('hidden'), 2000);
            }
        });
    }

    createRoom() {
        const categories = sessionStorage.getItem('realtimeCategories') || '';
        const difficulty = sessionStorage.getItem('realtimeDifficulty') || 'progressive';

        this.connectWebSocket('create', () => {
            this.ws.send(JSON.stringify({
                type: 'create',
                categories: categories,
                difficulty: difficulty
            }));
        });

        // Show host controls
        document.getElementById('host-actions').style.display = 'block';
        document.getElementById('guest-notice').style.display = 'none';

        // Setup start button
        document.getElementById('start-btn').addEventListener('click', () => {
            this.ws.send(JSON.stringify({ type: 'start_game' }));
        });
    }

    joinRoom() {
        this.connectWebSocket(this.roomCode);

        // Show guest notice
        document.getElementById('host-actions').style.display = 'none';
        document.getElementById('guest-notice').style.display = 'block';
    }

    connectWebSocket(roomCode, onOpen = null) {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/${roomCode}/${encodeURIComponent(this.playerName)}`;

        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            if (onOpen) onOpen();
        };

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleMessage(data);
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            alert('Connection error. Please try again.');
            window.location.href = '/realtime';
        };

        this.ws.onclose = () => {
            console.log('WebSocket closed');
        };
    }

    handleMessage(data) {
        console.log('Received:', data.type, data);

        switch (data.type) {
            case 'room_created':
                this.roomCode = data.room_code;
                document.getElementById('display-room-code').textContent = data.room_code;
                history.replaceState(null, '', `/realtime/${data.room_code}`);
                this.updatePlayerList(data.players);
                break;

            case 'room_joined':
                document.getElementById('display-room-code').textContent = data.room_code;
                this.updatePlayerList(data.players);
                if (data.host === this.playerName) {
                    document.getElementById('host-actions').style.display = 'block';
                    document.getElementById('guest-notice').style.display = 'none';
                    this.isHost = true;
                }
                break;

            case 'player_joined':
            case 'player_left':
            case 'player_answered':
                this.updatePlayerList(data.players);
                break;

            case 'error':
                alert(data.message);
                window.location.href = '/realtime';
                break;

            case 'room_closed':
                alert(data.reason || 'Room was closed');
                window.location.href = '/realtime';
                break;

            case 'countdown':
                this.showCountdown(data.count);
                break;

            case 'game_start':
                this.startGame(data.total_questions);
                break;

            case 'question':
                this.showQuestion(data);
                break;

            case 'timer':
                this.updateTimer(data.remaining);
                break;

            case 'answer_result':
                this.showAnswerResult(data);
                break;

            case 'game_over':
                this.showGameOver(data);
                break;

            case 'chat':
                // Could implement chat display here
                break;
        }
    }

    updatePlayerList(players) {
        const playerList = document.getElementById('player-list');
        const playerCount = document.getElementById('player-count');

        playerCount.textContent = players.length;

        playerList.innerHTML = players.map(player => `
            <div class="waiting-player ${player.name === this.playerName ? 'you' : ''} ${player.is_host ? 'host' : ''}">
                <span class="player-avatar">${player.name[0].toUpperCase()}</span>
                <span class="player-name">${player.name}${player.is_host ? ' (Host)' : ''}${player.name === this.playerName ? ' (You)' : ''}</span>
                ${player.answered ? '<span class="answered-badge">&#x2705;</span>' : ''}
            </div>
        `).join('');

        // Enable start button if enough players
        const startBtn = document.getElementById('start-btn');
        if (startBtn) {
            startBtn.disabled = players.length < 2;
        }
    }

    showCountdown(count) {
        this.waitingRoom.classList.add('hidden');
        this.countdownOverlay.classList.remove('hidden');

        const countdownNumber = document.getElementById('countdown-number');
        countdownNumber.textContent = count;
        countdownNumber.style.animation = 'none';
        countdownNumber.offsetHeight;
        countdownNumber.style.animation = 'countdownPulse 1s ease-out';
    }

    startGame(totalQuestions) {
        this.countdownOverlay.classList.add('hidden');
        this.gameArea.classList.remove('hidden');
        this.totalQuestions = totalQuestions;
    }

    showQuestion(data) {
        this.answered = false;
        this.currentQuestion = data;
        this.answerOverlay.classList.add('hidden');

        // Update question display
        document.getElementById('question-number').textContent =
            `Question ${data.question_number}/${data.total_questions}`;
        document.getElementById('question-text').textContent = data.question;

        // Update difficulty badge
        const diffBadge = document.getElementById('difficulty-badge');
        diffBadge.textContent = data.difficulty.charAt(0).toUpperCase() + data.difficulty.slice(1);
        diffBadge.className = `rt-difficulty ${data.difficulty}`;

        // Generate choices
        const letters = ['A', 'B', 'C', 'D'];
        const choicesContainer = document.getElementById('choices-container');
        choicesContainer.innerHTML = data.choices.map((choice, index) => `
            <button class="rt-choice" data-index="${index}">
                <span class="choice-letter">${letters[index]}</span>
                <span class="choice-text">${choice}</span>
            </button>
        `).join('');

        // Add click handlers
        choicesContainer.querySelectorAll('.rt-choice').forEach(btn => {
            btn.addEventListener('click', () => this.submitAnswer(parseInt(btn.dataset.index)));
        });

        // Reset and start timer
        this.updateTimer(data.time_limit);

        // Animate card
        const card = document.getElementById('question-card');
        card.style.animation = 'none';
        card.offsetHeight;
        card.style.animation = 'fadeInUp 0.4s ease-out';
    }

    updateTimer(remaining) {
        const timerFill = document.getElementById('timer-fill');
        const timerText = document.getElementById('timer-text');

        timerText.textContent = remaining;
        const percentage = (remaining / 15) * 100;
        timerFill.style.width = `${percentage}%`;

        // Change color when low
        if (remaining <= 5) {
            timerFill.classList.add('low');
        } else {
            timerFill.classList.remove('low');
        }
    }

    submitAnswer(answerIndex) {
        if (this.answered) return;
        this.answered = true;

        // Highlight selected
        const buttons = document.querySelectorAll('.rt-choice');
        buttons.forEach(btn => btn.disabled = true);
        buttons[answerIndex].classList.add('selected');

        // Send to server
        this.ws.send(JSON.stringify({
            type: 'submit_answer',
            answer: answerIndex
        }));
    }

    showAnswerResult(data) {
        const buttons = document.querySelectorAll('.rt-choice');

        // Show correct/wrong
        buttons.forEach((btn, index) => {
            if (index === data.correct_answer) {
                btn.classList.add('correct');
            } else if (btn.classList.contains('selected')) {
                btn.classList.add('wrong');
            }
        });

        // Update live scoreboard
        this.updateScoreboard(data.standings);

        // Show answer overlay
        this.answerOverlay.classList.remove('hidden');

        // Correct answer display
        const correctAnswerDisplay = document.getElementById('correct-answer-display');
        correctAnswerDisplay.innerHTML = `
            <span class="correct-label">Correct Answer:</span>
            <span class="correct-text">${this.currentQuestion.choices[data.correct_answer]}</span>
        `;

        // Explanation
        document.getElementById('explanation-text').textContent = data.explanation;

        // Round results
        const roundResults = document.getElementById('round-results');
        roundResults.innerHTML = data.results.map(result => `
            <div class="round-result-row ${result.correct ? 'correct' : 'wrong'}">
                <span class="result-player">${result.name}</span>
                <span class="result-status">${result.correct ? '&#x2705;' : '&#x274C;'}</span>
                <span class="result-points">+${result.points_earned}</span>
                <span class="result-total">${result.score} pts</span>
            </div>
        `).join('');
    }

    updateScoreboard(standings) {
        const scoreboard = document.getElementById('live-scoreboard');

        scoreboard.innerHTML = standings
            .sort((a, b) => b.score - a.score)
            .map((player, idx) => `
                <div class="score-entry ${player.name === this.playerName ? 'you' : ''} ${idx === 0 ? 'first' : ''}">
                    <span class="score-rank">${idx === 0 ? '&#x1F451;' : idx + 1}</span>
                    <span class="score-name">${player.name}</span>
                    <span class="score-value">${player.score}</span>
                    ${player.streak >= 2 ? `<span class="streak-badge">&#x1F525;${player.streak}</span>` : ''}
                </div>
            `).join('');
    }

    showGameOver(data) {
        this.gameArea.classList.add('hidden');
        this.answerOverlay.classList.add('hidden');
        this.gameOver.classList.remove('hidden');

        const winner = data.standings[0];

        // Winner display
        document.getElementById('winner-name').textContent = `${winner.name} Wins!`;

        // Confetti for winner
        if (winner.name === this.playerName) {
            setTimeout(() => {
                confetti({ particleCount: 200, spread: 100, origin: { y: 0.6 } });
                setTimeout(() => confetti({ particleCount: 100, spread: 120, origin: { y: 0.5 } }), 300);
            }, 500);
        }

        // Final standings
        const finalStandings = document.getElementById('final-standings');
        finalStandings.innerHTML = data.standings.map((player, idx) => {
            const rankEmoji = idx === 0 ? '&#x1F947;' : idx === 1 ? '&#x1F948;' : idx === 2 ? '&#x1F949;' : `${idx + 1}`;
            return `
                <div class="final-standing-row ${player.name === this.playerName ? 'you' : ''} ${idx === 0 ? 'winner' : ''}">
                    <span class="final-rank">${rankEmoji}</span>
                    <span class="final-name">${player.name}</span>
                    <div class="final-stats">
                        <span class="final-score">${player.score} pts</span>
                        <span class="final-correct">${player.correct_count}/${data.total_questions}</span>
                    </div>
                </div>
            `;
        }).join('');
    }
}

// Initialize game when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new RealTimeGame();
});
