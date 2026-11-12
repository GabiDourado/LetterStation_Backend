from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import engine, Base
import CriarTabela 

from auth import router as auth_router
from routers.usuarios import router as usuarios_router
from routers.reviews import router as reviews_router
from routers.jogos import router as jogos_router

Base.metadata.create_all(bind=engine)

app = FastAPI()

app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(reviews_router)
app.include_router(jogos_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)