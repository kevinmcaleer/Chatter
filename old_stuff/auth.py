from datetime import datetime, timedelta
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session 
from starlette import status
from database import SessionLocal