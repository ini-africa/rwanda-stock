from fastapi import FastAPI, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import models
from database import engine, get_db
from contextlib import asynccontextmanager
import scheduler
import threading

models.Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start scheduler in background
    scheduler_thread = threading.Thread(target=scheduler.start_scheduler, daemon=True)
    scheduler_thread.start()
    yield
    # Cleanup if needed

app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/")
def read_root(request: Request, db: Session = Depends(get_db)):
    stocks = db.query(models.Stock).all()
    market_stats = db.query(models.MarketStat).all()
    bonds = db.query(models.Bond).all()
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "stocks": stocks,
        "market_stats": market_stats,
        "bonds": bonds
    })

@app.get("/api/stocks")
def get_stocks(db: Session = Depends(get_db)):
    return db.query(models.Stock).all()

@app.get("/api/history/{symbol}")
def get_history(symbol: str, db: Session = Depends(get_db)):
    stock = db.query(models.Stock).filter(models.Stock.symbol == symbol).first()
    if not stock:
        return []
    return stock.history

@app.get("/api/market-stats")
def get_market_stats(db: Session = Depends(get_db)):
    return db.query(models.MarketStat).all()

@app.get("/api/bonds")
def get_bonds(db: Session = Depends(get_db)):
    return db.query(models.Bond).all()
