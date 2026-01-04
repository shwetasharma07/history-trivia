// ============================================
// HISTORY TRIVIA GAME - Game Logic
// ============================================

class HistoryTriviaGame {
    constructor() {
        this.questions = [];
        this.currentQuestionIndex = 0;
        this.score = 0;
        this.answered = false;

        // DOM Elements
        this.scoreDisplay = document.getElementById('score');
        this.progressFill = document.getElementById('progress-fill');
        this.progressText = document.getElementById('progress-text');
        this.eraBadge = document.getElementById('era-badge');
        this.questionNumber = document.getElementById('question-number');
        this.questionText = document.getElementById('question-text');
        this.choicesContainer = document.getElementById('choices-container');
        this.funFactContainer = document.getElementById('fun-fact-container');
        this.funFactText = document.getElementById('fun-fact-text');
        this.nextButton = document.getElementById('next-button');
        this.feedbackOverlay = document.getElementById('feedback-overlay');
        this.feedbackContent = document.getElementById('feedback-content');

        this.init();
    }

    async init() {
        await this.loadQuestions();
        this.displayQuestion();
        this.setupEventListeners();
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
        this.progressText.textContent = `${this.currentQuestionIndex + 1} / ${this.questions.length}`;

        // Update era badge
        this.updateEraBadge(question.era);

        // Generate choices
        this.generateChoices(question.choices);

        // Hide fun fact and next button
        this.funFactContainer.classList.add('hidden');
        this.nextButton.classList.add('hidden');

        // Animate question card
        const questionCard = document.getElementById('question-card');
        questionCard.style.animation = 'none';
        questionCard.offsetHeight; // Trigger reflow
        questionCard.style.animation = 'bounce-in 0.5s ease-out';
    }

    updateEraBadge(era) {
        const eraEmojis = {
            ancient: '\u{1F3FA}',
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

        // Disable all buttons
        const buttons = this.choicesContainer.querySelectorAll('.choice-button');
        buttons.forEach(btn => btn.disabled = true);

        // Check answer
        try {
            const response = await fetch(`/api/check-answer?question_id=${question.id}&answer=${selectedIndex}`, {
                method: 'POST'
            });
            const result = await response.json();

            // Mark correct/wrong
            if (result.correct) {
                selectedButton.classList.add('correct');
                this.score++;
                this.scoreDisplay.textContent = this.score;
                this.showFeedback(true);
            } else {
                selectedButton.classList.add('wrong');
                buttons[result.correct_answer].classList.add('correct');
                this.showFeedback(false);
            }

            // Show fun fact
            this.funFactText.textContent = result.fun_fact;
            this.funFactContainer.classList.remove('hidden');

            // Show next button or finish
            if (this.currentQuestionIndex < this.questions.length - 1) {
                this.nextButton.textContent = 'Next Question \u27A1';
            } else {
                this.nextButton.textContent = 'See Results \u{1F3C6}';
            }
            this.nextButton.classList.remove('hidden');

        } catch (error) {
            console.error('Error checking answer:', error);
        }
    }

    showFeedback(correct) {
        const feedbackEmoji = correct ? '\u2705' : '\u274C';
        this.feedbackContent.innerHTML = feedbackEmoji;
        this.feedbackOverlay.classList.remove('hidden');

        setTimeout(() => {
            this.feedbackOverlay.classList.add('hidden');
        }, 800);
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
        // Redirect to results page with score
        window.location.href = `/results?score=${this.score}&total=${this.questions.length}`;
    }
}

// Initialize game when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new HistoryTriviaGame();
});
