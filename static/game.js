// ============================================
// HISTORY TRIVIA GAME - Enhanced Game Logic
// ============================================

class HistoryTriviaGame {
    constructor() {
        this.questions = [];
        this.currentQuestionIndex = 0;
        this.score = 0;
        this.lives = 3;
        this.streak = 0;
        this.bestStreak = 0;
        this.answered = false;

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

        this.init();
    }

    async init() {
        await this.loadQuestions();
        this.displayQuestion();
        this.setupEventListeners();
        this.updateLivesDisplay();
    }

    async loadQuestions() {
        try {
            const response = await fetch('/api/questions?count=10');
            const data = await response.json();
            this.questions = data.questions;
        } catch (error) {
            console.error('Error loading questions:', error);
            this.questionText.textContent = 'Error loading questions. Please refresh the page.';
        }
    }

    setupEventListeners() {
        this.nextButton.addEventListener('click', () => this.nextQuestion());
    }

    displayQuestion() {
        const question = this.questions[this.currentQuestionIndex];
        if (!question) return;

        this.answered = false;

        // Update question number and text
        this.questionNumber.textContent = `Question ${this.currentQuestionIndex + 1}`;
        this.questionText.textContent = question.question;

        // Update progress
        const progress = ((this.currentQuestionIndex + 1) / this.questions.length) * 100;
        this.progressFill.style.width = `${progress}%`;
        this.progressText.textContent = `${this.currentQuestionIndex + 1} of ${this.questions.length}`;

        // Update era badge
        this.updateEraBadge(question.era);

        // Generate choices
        this.generateChoices(question.choices);

        // Hide answer result, fun fact and next button
        this.answerResult.classList.add('hidden');
        this.answerResult.classList.remove('correct', 'wrong');
        this.funFactContainer.classList.add('hidden');
        this.nextButton.classList.add('hidden');
        this.nextButton.classList.remove('finish');

        // Animate question card
        const questionCard = document.getElementById('question-card');
        questionCard.style.animation = 'none';
        questionCard.offsetHeight; // Trigger reflow
        questionCard.style.animation = 'fadeInUp 0.4s ease-out';
    }

    updateEraBadge(era) {
        const eraEmojis = {
            ancient: '\u{1F3DB}',
            medieval: '\u2694\uFE0F',
            modern: '\u{1F680}'
        };

        const eraNames = {
            ancient: 'Ancient',
            medieval: 'Medieval',
            modern: 'Modern'
        };

        this.eraBadge.className = `era-badge ${era}`;
        this.eraBadge.innerHTML = `
            <span class="era-icon">${eraEmojis[era] || '\u{1F4DA}'}</span>
            <span class="era-text">${eraNames[era] || 'History'}</span>
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

        // Add click listeners to choices
        const buttons = this.choicesContainer.querySelectorAll('.choice-button');
        buttons.forEach(button => {
            button.addEventListener('click', (e) => this.selectAnswer(e));
        });
    }

    async selectAnswer(event) {
        if (this.answered) return;
        this.answered = true;

        const selectedButton = event.currentTarget;
        const selectedIndex = parseInt(selectedButton.dataset.index);
        const question = this.questions[this.currentQuestionIndex];

        // Add selected state immediately
        selectedButton.classList.add('selected');

        // Disable all buttons
        const buttons = this.choicesContainer.querySelectorAll('.choice-button');
        buttons.forEach(btn => btn.disabled = true);

        // Check answer
        try {
            const response = await fetch(`/api/check-answer?question_id=${question.id}&answer=${selectedIndex}`, {
                method: 'POST'
            });
            const result = await response.json();

            // Small delay for suspense
            await new Promise(resolve => setTimeout(resolve, 300));

            // Remove selected state
            selectedButton.classList.remove('selected');

            // Mark correct/wrong and show result
            if (result.correct) {
                selectedButton.classList.add('correct');
                this.score++;
                this.streak++;
                if (this.streak > this.bestStreak) {
                    this.bestStreak = this.streak;
                }
                this.scoreDisplay.textContent = this.score;
                this.streakDisplay.textContent = this.streak;

                // Update streak display animation
                const streakItem = document.querySelector('.stat-streak');
                if (this.streak >= 2) {
                    streakItem.classList.add('on-fire');
                    setTimeout(() => streakItem.classList.remove('on-fire'), 500);
                }

                // Show streak popup for milestones
                if (this.streak === 3 || this.streak === 5 || this.streak === 7 || this.streak === 10) {
                    this.showStreakPopup(this.streak);
                }

                this.showFeedback(true);
                this.showAnswerResult(true);
            } else {
                selectedButton.classList.add('wrong');
                buttons[result.correct_answer].classList.add('correct');
                this.streak = 0;
                this.streakDisplay.textContent = this.streak;
                this.loseLife();
                this.showFeedback(false);
                this.showAnswerResult(false);
            }

            // Dim non-selected, non-correct buttons
            buttons.forEach((btn, index) => {
                if (index !== selectedIndex && index !== result.correct_answer) {
                    btn.classList.add('dimmed');
                }
            });

            // Show fun fact
            this.funFactText.textContent = result.fun_fact;
            this.funFactContainer.classList.remove('hidden');

            // Show next button or finish
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

    showAnswerResult(correct) {
        this.answerResult.classList.remove('hidden', 'correct', 'wrong');
        this.answerResult.classList.add(correct ? 'correct' : 'wrong');

        if (correct) {
            this.resultIcon.innerHTML = '\u2705';
            if (this.streak >= 3) {
                this.resultText.textContent = `Correct! ${this.streak} in a row!`;
            } else {
                this.resultText.textContent = 'Correct!';
            }
        } else {
            this.resultIcon.innerHTML = '\u274C';
            this.resultText.textContent = 'Not quite!';
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

        this.streakPopupText.textContent = messages[streak] || `${streak} in a row!`;
        this.streakPopup.classList.remove('hidden');

        // Reset animation
        this.streakPopup.style.animation = 'none';
        this.streakPopup.offsetHeight;
        this.streakPopup.style.animation = 'streakPop 1.5s ease-out forwards';

        setTimeout(() => {
            this.streakPopup.classList.add('hidden');
        }, 1500);
    }

    nextQuestion() {
        if (this.currentQuestionIndex < this.questions.length - 1) {
            this.currentQuestionIndex++;
            this.displayQuestion();
        } else {
            this.finishGame();
        }
    }

    finishGame() {
        // Redirect to results page with all stats
        const params = new URLSearchParams({
            score: this.score,
            total: this.questions.length,
            streak: this.bestStreak,
            lives: this.lives
        });
        window.location.href = `/results?${params.toString()}`;
    }
}

// Initialize game when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new HistoryTriviaGame();
});
