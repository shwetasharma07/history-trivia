// ============================================
// BRAINRACE - Enhanced Game Logic
// Supports Solo and Local Multiplayer
// With Power-ups, Hints, and Timed Mode
// ============================================

// Simple sound manager using Web Audio API
class SoundManager {
    constructor() {
        this.enabled = localStorage.getItem('soundEnabled') !== 'false';
        this.audioContext = null;
    }

    initContext() {
        if (!this.audioContext) {
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        }
    }

    playTone(frequency, duration, type = 'sine', volume = 0.3) {
        if (!this.enabled) return;
        this.initContext();

        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        oscillator.type = type;
        oscillator.frequency.setValueAtTime(frequency, this.audioContext.currentTime);

        gainNode.gain.setValueAtTime(volume, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + duration);

        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + duration);
    }

    correct() {
        // Happy ascending arpeggio
        this.playTone(523.25, 0.1, 'sine', 0.2); // C5
        setTimeout(() => this.playTone(659.25, 0.1, 'sine', 0.2), 80); // E5
        setTimeout(() => this.playTone(783.99, 0.15, 'sine', 0.25), 160); // G5
    }

    wrong() {
        // Descending buzz
        this.playTone(200, 0.15, 'sawtooth', 0.15);
        setTimeout(() => this.playTone(150, 0.2, 'sawtooth', 0.1), 100);
    }

    streak() {
        // Triumphant fanfare
        this.playTone(523.25, 0.1, 'sine', 0.2);
        setTimeout(() => this.playTone(659.25, 0.1, 'sine', 0.2), 100);
        setTimeout(() => this.playTone(783.99, 0.1, 'sine', 0.2), 200);
        setTimeout(() => this.playTone(1046.50, 0.3, 'sine', 0.3), 300);
    }

    click() {
        this.playTone(800, 0.05, 'sine', 0.1);
    }

    timeWarning() {
        this.playTone(440, 0.1, 'square', 0.1);
    }

    toggle() {
        this.enabled = !this.enabled;
        localStorage.setItem('soundEnabled', this.enabled);
        if (this.enabled) this.click();
        return this.enabled;
    }
}

const soundManager = new SoundManager();

class BrainRaceGame {
    constructor() {
        this.questions = [];
        this.currentQuestionIndex = 0;
        this.answered = false;
        this.sounds = soundManager;

        // Game mode
        this.gameMode = sessionStorage.getItem('gameMode') || 'solo';
        this.isMultiplayer = this.gameMode === 'local';

        // Timed mode
        this.timedMode = sessionStorage.getItem('timedMode') === 'timed';
        this.timePerQuestion = 15;
        this.timeRemaining = this.timePerQuestion;
        this.timerInterval = null;
        this.questionStartTime = null;

        // Power-ups state
        this.powerUps = {
            fiftyFifty: 1,
            skip: 1,
            doublePoints: 1
        };
        this.doublePointsActive = false;

        // Hints state
        this.hintsRemaining = 2;
        this.hintUsedThisQuestion = false;

        // Player management
        if (this.isMultiplayer) {
            this.players = JSON.parse(sessionStorage.getItem('players') || '[]');
            this.playerCount = this.players.length;
            this.currentPlayerIndex = 0;
            this.playerScores = this.players.map(() => ({ score: 0, streak: 0, bestStreak: 0, correct: 0 }));
        } else {
            this.players = [sessionStorage.getItem('username') || 'Player'];
            this.playerCount = 1;
            this.currentPlayerIndex = 0;
            this.playerScores = [{ score: 0, streak: 0, bestStreak: 0, correct: 0 }];
        }

        this.lives = 3;

        // DOM Elements
        this.scoreDisplay = document.getElementById('score');
        this.livesDisplay = document.getElementById('lives-display');
        this.streakDisplay = document.getElementById('streak');
        this.progressFill = document.getElementById('progress-fill');
        this.progressText = document.getElementById('progress-text');
        this.eraBadge = document.getElementById('era-badge');
        this.questionNumber = document.getElementById('question-number');
        this.questionText = document.getElementById('question-text');
        this.choicesContainer = document.getElementById('choices-container');
        this.answerResult = document.getElementById('answer-result');
        this.resultIcon = document.getElementById('result-icon');
        this.resultText = document.getElementById('result-text');
        this.funFactContainer = document.getElementById('fun-fact-container');
        this.funFactText = document.getElementById('fun-fact-text');
        this.nextButton = document.getElementById('next-button');
        this.feedbackOverlay = document.getElementById('feedback-overlay');
        this.feedbackContent = document.getElementById('feedback-content');
        this.streakPopup = document.getElementById('streak-popup');
        this.streakPopupText = document.getElementById('streak-popup-text');

        // Power-up and timer DOM elements
        this.timerDisplay = document.getElementById('timer-display');
        this.timerFill = document.getElementById('timer-fill');
        this.fiftyFiftyBtn = document.getElementById('powerup-5050');
        this.skipBtn = document.getElementById('powerup-skip');
        this.doublePointsBtn = document.getElementById('powerup-double');
        this.hintBtn = document.getElementById('hint-button');

        this.init();
    }

    get currentPlayer() {
        return this.players[this.currentPlayerIndex];
    }

    get currentPlayerScore() {
        return this.playerScores[this.currentPlayerIndex];
    }

    async init() {
        await this.loadQuestions();
        this.setupMultiplayerUI();
        this.setupTimedModeUI();
        this.setupPowerUpListeners();
        this.displayQuestion();
        this.setupEventListeners();
        this.updateLivesDisplay();
        this.updatePowerUpButtons();
    }

    setupTimedModeUI() {
        const timerContainer = document.getElementById('timer-container');
        if (timerContainer) {
            if (this.timedMode) {
                timerContainer.classList.remove('hidden');
            } else {
                timerContainer.classList.add('hidden');
            }
        }
    }

    setupPowerUpListeners() {
        if (this.fiftyFiftyBtn) {
            this.fiftyFiftyBtn.addEventListener('click', () => this.useFiftyFifty());
        }
        if (this.skipBtn) {
            this.skipBtn.addEventListener('click', () => this.useSkip());
        }
        if (this.doublePointsBtn) {
            this.doublePointsBtn.addEventListener('click', () => this.useDoublePoints());
        }
        if (this.hintBtn) {
            this.hintBtn.addEventListener('click', () => this.useHint());
        }
    }

    updatePowerUpButtons() {
        if (this.fiftyFiftyBtn) {
            this.fiftyFiftyBtn.disabled = this.powerUps.fiftyFifty <= 0 || this.answered;
            this.fiftyFiftyBtn.querySelector('.powerup-count').textContent = this.powerUps.fiftyFifty;
        }
        if (this.skipBtn) {
            this.skipBtn.disabled = this.powerUps.skip <= 0 || this.answered;
            this.skipBtn.querySelector('.powerup-count').textContent = this.powerUps.skip;
        }
        if (this.doublePointsBtn) {
            this.doublePointsBtn.disabled = this.powerUps.doublePoints <= 0 || this.answered || this.doublePointsActive;
            this.doublePointsBtn.querySelector('.powerup-count').textContent = this.powerUps.doublePoints;
            if (this.doublePointsActive) {
                this.doublePointsBtn.classList.add('active');
            } else {
                this.doublePointsBtn.classList.remove('active');
            }
        }
        if (this.hintBtn) {
            this.hintBtn.disabled = this.hintsRemaining <= 0 || this.answered || this.hintUsedThisQuestion;
            this.hintBtn.querySelector('.powerup-count').textContent = this.hintsRemaining;
        }
    }

    useFiftyFifty() {
        if (this.powerUps.fiftyFifty <= 0 || this.answered) return;

        const question = this.questions[this.currentQuestionIndex];
        const correctIndex = question.answer;
        const buttons = this.choicesContainer.querySelectorAll('.choice-button');

        // Find wrong answers
        const wrongIndices = [];
        buttons.forEach((btn, index) => {
            if (index !== correctIndex && !btn.classList.contains('eliminated')) {
                wrongIndices.push(index);
            }
        });

        // Remove 2 wrong answers
        const toRemove = wrongIndices.sort(() => Math.random() - 0.5).slice(0, 2);
        toRemove.forEach(index => {
            buttons[index].classList.add('eliminated');
            buttons[index].disabled = true;
        });

        this.powerUps.fiftyFifty--;
        this.updatePowerUpButtons();
    }

    useSkip() {
        if (this.powerUps.skip <= 0 || this.answered) return;

        this.powerUps.skip--;
        this.stopTimer();
        this.updatePowerUpButtons();

        // Skip without losing life
        if (this.currentQuestionIndex < this.questions.length - 1) {
            this.currentQuestionIndex++;
            this.displayQuestion();
        } else {
            this.finishGame();
        }
    }

    useDoublePoints() {
        if (this.powerUps.doublePoints <= 0 || this.answered || this.doublePointsActive) return;

        this.doublePointsActive = true;
        this.powerUps.doublePoints--;
        this.updatePowerUpButtons();

        // Show activation feedback
        this.showPowerUpFeedback('2x Points Active!');
    }

    useHint() {
        if (this.hintsRemaining <= 0 || this.answered || this.hintUsedThisQuestion) return;

        this.hintsRemaining--;
        this.hintUsedThisQuestion = true;
        this.updatePowerUpButtons();

        // Show the fun fact/explanation early (costs 50% points)
        const question = this.questions[this.currentQuestionIndex];
        this.funFactText.textContent = question.fun_fact || 'Think carefully about this one!';
        this.funFactContainer.classList.remove('hidden');

        // Mark that hint was used (for point reduction)
        this.showPowerUpFeedback('Hint used! (50% point penalty)');
    }

    showPowerUpFeedback(message) {
        const feedback = document.createElement('div');
        feedback.className = 'powerup-feedback';
        feedback.textContent = message;
        document.body.appendChild(feedback);

        setTimeout(() => {
            feedback.classList.add('fade-out');
            setTimeout(() => feedback.remove(), 500);
        }, 1500);
    }

    startTimer() {
        if (!this.timedMode) return;

        this.timeRemaining = this.timePerQuestion;
        this.questionStartTime = Date.now();
        this.updateTimerDisplay();

        this.timerInterval = setInterval(() => {
            this.timeRemaining--;
            this.updateTimerDisplay();

            if (this.timeRemaining <= 0) {
                this.stopTimer();
                this.handleTimeUp();
            }
        }, 1000);
    }

    stopTimer() {
        if (this.timerInterval) {
            clearInterval(this.timerInterval);
            this.timerInterval = null;
        }
    }

    updateTimerDisplay() {
        if (!this.timerDisplay || !this.timerFill) return;

        this.timerDisplay.textContent = this.timeRemaining;
        const percentage = (this.timeRemaining / this.timePerQuestion) * 100;
        this.timerFill.style.width = `${percentage}%`;

        // Change color based on time remaining
        if (this.timeRemaining <= 5) {
            this.timerFill.classList.add('danger');
            this.timerFill.classList.remove('warning');
        } else if (this.timeRemaining <= 10) {
            this.timerFill.classList.add('warning');
            this.timerFill.classList.remove('danger');
        } else {
            this.timerFill.classList.remove('warning', 'danger');
        }
    }

    handleTimeUp() {
        if (this.answered) return;
        this.answered = true;

        const question = this.questions[this.currentQuestionIndex];
        const buttons = this.choicesContainer.querySelectorAll('.choice-button');

        buttons.forEach(btn => btn.disabled = true);
        buttons[question.answer].classList.add('correct');

        const playerScore = this.currentPlayerScore;
        playerScore.streak = 0;
        this.streakDisplay.textContent = playerScore.streak;

        if (!this.isMultiplayer) {
            this.loseLife();
        }

        this.showFeedback(false);
        this.showAnswerResult(false, true); // true = timeout

        if (this.isMultiplayer) {
            this.updateScoreboard();
        }

        this.funFactText.textContent = question.fun_fact || 'Time ran out!';
        this.funFactContainer.classList.remove('hidden');

        const nextText = this.nextButton.querySelector('.next-text');
        const nextArrow = this.nextButton.querySelector('.next-arrow');

        if (this.currentQuestionIndex < this.questions.length - 1) {
            nextText.textContent = 'Next Question';
            nextArrow.innerHTML = '\u2192';
        } else {
            nextText.textContent = 'See Results';
            nextArrow.innerHTML = '\u{1F3C6}';
            this.nextButton.classList.add('finish');
        }
        this.nextButton.classList.remove('hidden');
    }

    calculateTimeBonus() {
        if (!this.timedMode || !this.questionStartTime) return 0;

        const timeTaken = (Date.now() - this.questionStartTime) / 1000;
        if (timeTaken < 5) {
            return 5; // Bonus for fast answers
        }
        return 0;
    }

    setupMultiplayerUI() {
        if (this.isMultiplayer) {
            // Add player indicator to the header
            const header = document.querySelector('.game-header');
            const playerIndicator = document.createElement('div');
            playerIndicator.id = 'player-indicator';
            playerIndicator.className = 'player-indicator';
            header.insertBefore(playerIndicator, header.firstChild);

            // Add scoreboard
            const scoreboard = document.createElement('div');
            scoreboard.id = 'multiplayer-scoreboard';
            scoreboard.className = 'multiplayer-scoreboard';
            header.parentNode.insertBefore(scoreboard, header.nextSibling);

            this.updatePlayerIndicator();
            this.updateScoreboard();
        }
    }

    updatePlayerIndicator() {
        if (!this.isMultiplayer) return;
        const indicator = document.getElementById('player-indicator');
        if (indicator) {
            indicator.innerHTML = `
                <span class="current-player-label">Current Turn:</span>
                <span class="current-player-name">${this.currentPlayer}</span>
            `;
        }
    }

    updateScoreboard() {
        if (!this.isMultiplayer) return;
        const scoreboard = document.getElementById('multiplayer-scoreboard');
        if (scoreboard) {
            scoreboard.innerHTML = this.players.map((player, idx) => `
                <div class="scoreboard-player ${idx === this.currentPlayerIndex ? 'active' : ''}">
                    <span class="player-name">${player}</span>
                    <span class="player-score">${this.playerScores[idx].score}</span>
                </div>
            `).join('');
        }
    }

    async loadQuestions() {
        try {
            const categories = sessionStorage.getItem('selectedCategories') || '';
            const difficulty = sessionStorage.getItem('difficulty') || 'progressive';

            // For multiplayer, get more questions (questionsPerPlayer * playerCount)
            const questionCount = this.isMultiplayer ? Math.min(this.playerCount * 5, 20) : 10;

            let url = `/api/questions?count=${questionCount}`;
            if (categories) {
                url += `&categories=${encodeURIComponent(categories)}`;
            }
            url += `&difficulty=${encodeURIComponent(difficulty)}`;

            const response = await fetch(url);
            const data = await response.json();
            this.questions = data.questions;
        } catch (error) {
            console.error('Error loading questions:', error);
            this.questionText.textContent = 'Error loading questions. Please refresh the page.';
        }
    }

    setupEventListeners() {
        this.nextButton.addEventListener('click', () => this.nextQuestion());

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => this.handleKeyPress(e));
    }

    handleKeyPress(event) {
        // Ignore if user is typing in an input field
        if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
            return;
        }

        const key = event.key;

        // Answer selection: 1-4 or A-D
        if (!this.answered) {
            let answerIndex = -1;

            if (key >= '1' && key <= '4') {
                answerIndex = parseInt(key) - 1;
            } else if (key.toLowerCase() >= 'a' && key.toLowerCase() <= 'd') {
                answerIndex = key.toLowerCase().charCodeAt(0) - 'a'.charCodeAt(0);
            }

            if (answerIndex >= 0 && answerIndex < 4) {
                const buttons = this.choicesContainer.querySelectorAll('.choice-button');
                if (buttons[answerIndex] && !buttons[answerIndex].disabled) {
                    buttons[answerIndex].click();
                }
            }
        }

        // Enter or Space for next question
        if ((key === 'Enter' || key === ' ') && this.answered && !this.nextButton.classList.contains('hidden')) {
            event.preventDefault();
            this.nextQuestion();
        }

        // Power-up shortcuts: Q for 50/50, W for skip, E for double points, H for hint
        if (!this.answered) {
            if (key.toLowerCase() === 'q' && this.fiftyFiftyBtn && !this.fiftyFiftyBtn.disabled) {
                this.useFiftyFifty();
            } else if (key.toLowerCase() === 'w' && this.skipBtn && !this.skipBtn.disabled) {
                this.useSkip();
            } else if (key.toLowerCase() === 'e' && this.doublePointsBtn && !this.doublePointsBtn.disabled) {
                this.useDoublePoints();
            } else if (key.toLowerCase() === 'h' && this.hintBtn && !this.hintBtn.disabled) {
                this.useHint();
            }
        }
    }

    displayQuestion() {
        const question = this.questions[this.currentQuestionIndex];
        if (!question) return;

        this.answered = false;
        this.hintUsedThisQuestion = false;

        // Stop any existing timer and start new one
        this.stopTimer();
        this.startTimer();

        // Update player indicator for multiplayer
        if (this.isMultiplayer) {
            this.updatePlayerIndicator();
        }

        // Update question number and text
        this.questionNumber.textContent = `Question ${this.currentQuestionIndex + 1}`;
        this.questionText.textContent = question.question;

        // Update progress
        const progress = ((this.currentQuestionIndex + 1) / this.questions.length) * 100;
        this.progressFill.style.width = `${progress}%`;
        this.progressText.textContent = `${this.currentQuestionIndex + 1} of ${this.questions.length}`;

        // Update era badge
        this.updateEraBadge(question.category, question.difficulty);

        // Generate choices
        this.generateChoices(question.choices);

        // Hide answer result, fun fact and next button
        this.answerResult.classList.add('hidden');
        this.answerResult.classList.remove('correct', 'wrong');
        this.funFactContainer.classList.add('hidden');
        this.nextButton.classList.add('hidden');
        this.nextButton.classList.remove('finish');

        // Update score display for current player
        this.scoreDisplay.textContent = this.currentPlayerScore.score;
        this.streakDisplay.textContent = this.currentPlayerScore.streak;

        // Update power-up buttons
        this.updatePowerUpButtons();

        // Animate question card
        const questionCard = document.getElementById('question-card');
        questionCard.style.animation = 'none';
        questionCard.offsetHeight;
        questionCard.style.animation = 'fadeInUp 0.4s ease-out';
    }

    updateEraBadge(category, difficulty) {
        const categoryEmojis = {
            'ancient-civilizations': '\u{1F3FA}',
            'medieval-europe': '\u2694\uFE0F',
            'world-wars': '\u{1F3C6}',
            'cold-war': '\u2744\uFE0F',
            'ancient-philosophy': '\u{1F4DC}',
            'revolutionary-periods': '\u{1F525}',
            'science': '\u{1F52C}'
        };

        const categoryNames = {
            'ancient-civilizations': 'Ancient',
            'medieval-europe': 'Medieval',
            'world-wars': 'World Wars',
            'cold-war': 'Cold War',
            'ancient-philosophy': 'Philosophy',
            'revolutionary-periods': 'Revolution',
            'science': 'Science'
        };

        const difficultyColors = {
            'easy': 'easy-diff',
            'medium': 'medium-diff',
            'hard': 'hard-diff'
        };

        this.eraBadge.className = `era-badge ${difficultyColors[difficulty] || ''}`;
        this.eraBadge.innerHTML = `
            <span class="era-icon">${categoryEmojis[category] || '\u{1F4DA}'}</span>
            <span class="era-text">${categoryNames[category] || 'History'}</span>
            <span class="difficulty-tag ${difficulty}">${difficulty}</span>
        `;
    }

    updateLivesDisplay() {
        const hearts = this.livesDisplay.querySelectorAll('.life-heart');
        hearts.forEach((heart, index) => {
            if (index < this.lives) {
                heart.classList.remove('lost');
            } else {
                heart.classList.add('lost');
            }
        });
    }

    loseLife() {
        const hearts = this.livesDisplay.querySelectorAll('.life-heart');
        const heartToLose = hearts[this.lives - 1];
        if (heartToLose) {
            heartToLose.classList.add('losing');
            setTimeout(() => {
                heartToLose.classList.remove('losing');
                heartToLose.classList.add('lost');
            }, 400);
        }
        this.lives--;
    }

    generateChoices(choices) {
        const letters = ['A', 'B', 'C', 'D'];
        this.choicesContainer.innerHTML = choices.map((choice, index) => `
            <button class="choice-button" data-index="${index}">
                <span class="choice-letter">${letters[index]}</span>
                <span class="choice-text">${choice}</span>
            </button>
        `).join('');

        const buttons = this.choicesContainer.querySelectorAll('.choice-button');
        buttons.forEach(button => {
            button.addEventListener('click', (e) => this.selectAnswer(e));
        });
    }

    async selectAnswer(event) {
        if (this.answered) return;
        this.answered = true;

        // Stop the timer
        this.stopTimer();

        const selectedButton = event.currentTarget;
        const selectedIndex = parseInt(selectedButton.dataset.index);
        const question = this.questions[this.currentQuestionIndex];

        selectedButton.classList.add('selected');

        const buttons = this.choicesContainer.querySelectorAll('.choice-button');
        buttons.forEach(btn => btn.disabled = true);

        // Disable power-ups after answering
        this.updatePowerUpButtons();

        try {
            const response = await fetch(`/api/check-answer?question_id=${question.id}&answer=${selectedIndex}`, {
                method: 'POST'
            });
            const result = await response.json();

            await new Promise(resolve => setTimeout(resolve, 300));

            selectedButton.classList.remove('selected');

            const playerScore = this.currentPlayerScore;

            if (result.correct) {
                selectedButton.classList.add('correct');
                this.sounds.correct();
                let points = result.points || 10;

                // Apply hint penalty (50% reduction)
                if (this.hintUsedThisQuestion) {
                    points = Math.floor(points * 0.5);
                }

                // Apply double points
                if (this.doublePointsActive) {
                    points *= 2;
                    this.doublePointsActive = false;
                    this.updatePowerUpButtons();
                }

                // Add time bonus for fast answers
                const timeBonus = this.calculateTimeBonus();
                if (timeBonus > 0) {
                    points += timeBonus;
                    this.showPowerUpFeedback(`+${timeBonus} Speed Bonus!`);
                }

                playerScore.score += points;
                playerScore.streak++;
                playerScore.correct++;
                if (playerScore.streak > playerScore.bestStreak) {
                    playerScore.bestStreak = playerScore.streak;
                }
                this.scoreDisplay.textContent = playerScore.score;
                this.streakDisplay.textContent = playerScore.streak;

                const streakItem = document.querySelector('.stat-streak');
                if (playerScore.streak >= 2) {
                    streakItem.classList.add('on-fire');
                    setTimeout(() => streakItem.classList.remove('on-fire'), 500);
                }

                if (playerScore.streak === 3 || playerScore.streak === 5 || playerScore.streak === 7 || playerScore.streak === 10) {
                    this.sounds.streak();
                    this.showStreakPopup(playerScore.streak);
                }

                this.showFeedback(true);
                this.showAnswerResult(true);
            } else {
                selectedButton.classList.add('wrong');
                this.sounds.wrong();
                buttons[result.correct_answer].classList.add('correct');
                playerScore.streak = 0;
                this.streakDisplay.textContent = playerScore.streak;

                // Reset double points if answer was wrong
                if (this.doublePointsActive) {
                    this.doublePointsActive = false;
                    this.updatePowerUpButtons();
                }

                if (!this.isMultiplayer) {
                    this.loseLife();
                }
                this.showFeedback(false);
                this.showAnswerResult(false);
            }

            // Update scoreboard
            if (this.isMultiplayer) {
                this.updateScoreboard();
            }

            buttons.forEach((btn, index) => {
                if (index !== selectedIndex && index !== result.correct_answer) {
                    btn.classList.add('dimmed');
                }
            });

            this.funFactText.textContent = result.fun_fact;
            this.funFactContainer.classList.remove('hidden');

            const nextText = this.nextButton.querySelector('.next-text');
            const nextArrow = this.nextButton.querySelector('.next-arrow');

            if (this.currentQuestionIndex < this.questions.length - 1) {
                nextText.textContent = 'Next Question';
                nextArrow.innerHTML = '\u2192';
            } else {
                nextText.textContent = 'See Results';
                nextArrow.innerHTML = '\u{1F3C6}';
                this.nextButton.classList.add('finish');
            }
            this.nextButton.classList.remove('hidden');

        } catch (error) {
            console.error('Error checking answer:', error);
        }
    }

    showAnswerResult(correct, timeout = false) {
        this.answerResult.classList.remove('hidden', 'correct', 'wrong');
        this.answerResult.classList.add(correct ? 'correct' : 'wrong');

        const playerScore = this.currentPlayerScore;
        if (correct) {
            this.resultIcon.innerHTML = '\u2705';
            if (playerScore.streak >= 3) {
                this.resultText.textContent = `Correct! ${playerScore.streak} in a row!`;
            } else {
                this.resultText.textContent = this.isMultiplayer ? `${this.currentPlayer} got it!` : 'Correct!';
            }
        } else {
            this.resultIcon.innerHTML = timeout ? '\u23F0' : '\u274C';
            if (timeout) {
                this.resultText.textContent = this.isMultiplayer ? `${this.currentPlayer} ran out of time!` : 'Time\'s up!';
            } else {
                this.resultText.textContent = this.isMultiplayer ? `${this.currentPlayer} missed it!` : 'Not quite!';
            }
        }
    }

    showFeedback(correct) {
        const feedbackEmoji = correct ? '\u2705' : '\u274C';
        this.feedbackContent.innerHTML = feedbackEmoji;
        this.feedbackOverlay.classList.remove('hidden');

        setTimeout(() => {
            this.feedbackOverlay.classList.add('hidden');
        }, 600);
    }

    showStreakPopup(streak) {
        const messages = {
            3: '3 in a row!',
            5: '5 streak! On fire!',
            7: '7 streak! Unstoppable!',
            10: 'PERFECT 10!'
        };

        const prefix = this.isMultiplayer ? `${this.currentPlayer}: ` : '';
        this.streakPopupText.textContent = prefix + (messages[streak] || `${streak} in a row!`);
        this.streakPopup.classList.remove('hidden');

        this.streakPopup.style.animation = 'none';
        this.streakPopup.offsetHeight;
        this.streakPopup.style.animation = 'streakPop 1.5s ease-out forwards';

        setTimeout(() => {
            this.streakPopup.classList.add('hidden');
        }, 1500);
    }

    nextQuestion() {
        // Rotate to next player in multiplayer
        if (this.isMultiplayer) {
            this.currentPlayerIndex = (this.currentPlayerIndex + 1) % this.playerCount;
        }

        if (this.currentQuestionIndex < this.questions.length - 1) {
            this.currentQuestionIndex++;
            this.displayQuestion();
        } else {
            this.finishGame();
        }
    }

    finishGame() {
        // Check for Perfect Round Bonus (all questions correct)
        const playerScore = this.playerScores[0];
        const isPerfect = !this.isMultiplayer && playerScore.correct === this.questions.length;

        if (isPerfect) {
            // Award 50 bonus points for perfect round
            playerScore.score += 50;
            this.showPowerUpFeedback('PERFECT ROUND! +50 Bonus!');
            this.sounds.streak(); // Play victory sound
        }

        if (this.isMultiplayer) {
            // Check for multiplayer perfect rounds and apply bonuses
            this.playerScores.forEach((ps, idx) => {
                const questionsPerPlayer = Math.ceil(this.questions.length / this.playerCount);
                if (ps.correct === questionsPerPlayer) {
                    ps.score += 50;
                }
            });

            // Store multiplayer results
            const results = this.players.map((player, idx) => ({
                name: player,
                score: this.playerScores[idx].score,
                correct: this.playerScores[idx].correct,
                bestStreak: this.playerScores[idx].bestStreak
            }));
            // Sort by score descending
            results.sort((a, b) => b.score - a.score);
            sessionStorage.setItem('multiplayerResults', JSON.stringify(results));
            sessionStorage.setItem('totalQuestions', this.questions.length);
            window.location.href = '/results?mode=multiplayer';
        } else {
            // Small delay if perfect to show the bonus message
            const delay = isPerfect ? 800 : 0;
            setTimeout(() => {
                const params = new URLSearchParams({
                    score: playerScore.score,
                    total: this.questions.length,
                    streak: playerScore.bestStreak,
                    lives: this.lives,
                    perfect: isPerfect ? '1' : '0'
                });
                window.location.href = `/results?${params.toString()}`;
            }, delay);
        }
    }
}

// Initialize game when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new BrainRaceGame();
});
