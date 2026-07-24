from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from pydantic import BaseModel

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])

# Modelos Pydantic aquí...
# Endpoints de clientes aquí...