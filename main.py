from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List
import random

from database import engine, get_db, Base
from models import Score
from questions import QUESTIONS, get_random_questions

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="History Trivia Game")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page - Start the game"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/play", response_class=HTMLResponse)
async def play(request: Request):
    """Game page"""
    return templates.TemplateResponse("game.html", {"request": request})


@app.get("/api/questions")
async def get_questions(count: int = 10):
    """Get random questions for a game"""
    questions = get_random_questions(min(count, len(QUESTIONS)))
    # Don't send correct answers to the client initially
    safe_questions = []
    for q in questions:
        safe_questions.append({
            "id": q["id"],
            "era": q["era"],
            "question": q["question"],
            "choices": q["choices"]
        })
    return {"questions": safe_questions}


@app.post("/api/check-answer")
async def check_answer(question_id: int, answer: int):
    """Check if an answer is correct and return the fun fact"""
    question = next((q for q in QUESTIONS if q["id"] == question_id), None)
    if not question:
        return JSONResponse({"error": "Question not found"}, status_code=404)

    is_correct = answer == question["correct"]
    return {
        "correct": is_correct,
        "correct_answer": question["correct"],
        "fun_fact": question["fun_fact"]
    }


@app.post("/api/save-score")
async def save_score(
    player_name: str,
    score: int,
    total_questions: int,
    db: Session = Depends(get_db)
):
    """Save a player's score to the leaderboard"""
    new_score = Score(
        player_name=player_name,
        score=score,
        total_questions=total_questions
    )
    db.add(new_score)
    db.commit()
    db.refresh(new_score)

    # Check if player made top 10
    top_scores = db.query(Score).order_by(Score.score.desc()).limit(10).all()
    made_leaderboard = any(s.id == new_score.id for s in top_scores)

    return {
        "success": True,
        "made_leaderboard": made_leaderboard,
        "rank": next((i + 1 for i, s in enumerate(top_scores) if s.id == new_score.id), None)
    }


@app.get("/api/leaderboard")
async def get_leaderboard(db: Session = Depends(get_db)):
    """Get top 10 scores"""
    scores = db.query(Score).order_by(Score.score.desc()).limit(10).all()
    return {
        "scores": [
            {
                "rank": i + 1,
                "player_name": s.player_name,
                "score": s.score,
                "total_questions": s.total_questions,
                "date": s.created_at.strftime("%Y-%m-%d")
            }
            for i, s in enumerate(scores)
        ]
    }


@app.get("/leaderboard", response_class=HTMLResponse)
async def leaderboard_page(request: Request, db: Session = Depends(get_db)):
    """Leaderboard page"""
    scores = db.query(Score).order_by(Score.score.desc()).limit(10).all()
    return templates.TemplateResponse(
        "leaderboard.html",
        {"request": request, "scores": scores}
    )


@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    """Results page after game ends"""
    return templates.TemplateResponse("results.html", {"request": request})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
