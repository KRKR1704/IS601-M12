# Author: Roopesh Kumar Reddy Kaipa
# Date: 24/11/2025
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import List
from fastapi import Body, FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_active_user
from app.models.calculation import Calculation
from app.models.user import User
from app.schemas.calculation import CalculationBase, CalculationResponse, CalculationUpdate
from app.schemas.token import TokenResponse
from app.schemas.user import UserCreate, UserResponse, UserLogin
from app.database import Base, get_db, engine
from app.auth.jwt import decode_token, oauth2_scheme
from app.schemas.token import TokenType
from app.auth.redis import add_to_blacklist

# Create tables on startup
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")
    yield

app = FastAPI(
    title="Calculations API",
    description="API for managing calculations",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/health", tags=["health"])
def read_health():
    return {"status": "ok"}

@app.post(
    "/auth/register", 
    response_model=UserResponse, 
    status_code=status.HTTP_201_CREATED,
    tags=["auth"]
)
def register(user_create: UserCreate, db: Session = Depends(get_db)):
    # Exclude confirm_password before passing data to User.register
    user_data = user_create.dict(exclude={"confirm_password"})
    try:
        user = User.register(db, user_data)
        db.commit()
        db.refresh(user)
        return user
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@app.post("/auth/login", response_model=TokenResponse, tags=["auth"])
def login_json(user_login: UserLogin, db: Session = Depends(get_db)):
    """Login with JSON payload"""
    auth_result = User.authenticate(db, user_login.username, user_login.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = auth_result["user"]
    db.commit()  # Commit the last_login update

    # Ensure expires_at is timezone-aware
    expires_at = auth_result.get("expires_at")
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    return TokenResponse(
        access_token=auth_result["access_token"],
        refresh_token=auth_result["refresh_token"],
        token_type="bearer",
        expires_at=expires_at,
        user_id=user.id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_verified=user.is_verified
    )

@app.post("/auth/token", tags=["auth"])
def login_form(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login with form data for Swagger UI"""
    auth_result = User.authenticate(db, form_data.username, form_data.password)
    if auth_result is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "access_token": auth_result["access_token"],
        "token_type": "bearer"
    }

@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT, tags=["auth"])
async def logout(token: str = Depends(oauth2_scheme)):
    """
    Revoke a refresh or access token by adding its JTI to the Redis blacklist
    with an expiry matching the token's remaining lifetime.
    """
    # Try decode as refresh token first; if that fails, attempt access token
    try:
        payload = await decode_token(token, TokenType.REFRESH, verify_exp=False)
    except HTTPException:
        try:
            payload = await decode_token(token, TokenType.ACCESS, verify_exp=False)
        except HTTPException:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    jti = payload.get("jti")
    exp = payload.get("exp")
    if not jti or not exp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token payload")

    # compute seconds until expiry; payload 'exp' may be a numeric timestamp
    try:
        now_ts = datetime.now(timezone.utc).timestamp()
        ttl = int(exp - now_ts)
    except Exception:
        ttl = None

    # Add to blacklist with expiry if known
    if ttl and ttl > 0:
        await add_to_blacklist(jti, ttl)
    else:
        # Add without expiry to be safe
        await add_to_blacklist(jti, 0)

    return None

# Create (Add) Calculation – using CalculationBase so that 'user_id' from the client is ignored.
@app.post(
    "/calculations",
    response_model=CalculationResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["calculations"],
)
def create_calculation(
    calculation_data: CalculationBase,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Compute and persist a calculation.
    
    The endpoint reads the calculation type and inputs from the request (ignoring any extra fields),
    computes the result using the appropriate operation, and assigns the authenticated user's ID.
    """
    try:
        # Create the calculation using the factory method.
        new_calculation = Calculation.create(
            calculation_type=calculation_data.type,
            user_id=current_user.id,
            inputs=calculation_data.inputs,
        )
        new_calculation.result = new_calculation.get_result()

        # Persist the calculation to the database.
        db.add(new_calculation)
        db.commit()
        db.refresh(new_calculation)
        return new_calculation

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

# Browse / List Calculations (for the current user)
@app.get("/calculations", response_model=List[CalculationResponse], tags=["calculations"])
def list_calculations(
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    calculations = db.query(Calculation).filter(Calculation.user_id == current_user.id).all()
    return calculations

# Read / Retrieve a Specific Calculation by ID
@app.get("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def get_calculation(
    calc_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")
    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")
    return calculation

# Edit / Update a Calculation
@app.put("/calculations/{calc_id}", response_model=CalculationResponse, tags=["calculations"])
def update_calculation(
    calc_id: str,
    calculation_update: CalculationUpdate,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")
    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")

    new_type = getattr(calculation_update, "type", None)
    if new_type is not None:
        try:
            temp = Calculation.create(
                calculation_type=new_type,
                user_id=calculation.user_id,
                inputs=(calculation_update.inputs or calculation.inputs),
            )
            computed = temp.get_result()
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        new_calc = temp
        new_calc.id = calculation.id
        new_calc.created_at = calculation.created_at
        new_calc.updated_at = datetime.utcnow()
        new_calc.user_id = calculation.user_id
        new_calc.result = computed
        try:
            db.delete(calculation)
            db.flush()
            db.add(new_calc)
            db.commit()
            db.refresh(new_calc)
            return new_calc
        except Exception as e:  # pragma: no cover
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))
    elif calculation_update.inputs is not None:
        calculation.inputs = calculation_update.inputs
        calculation.result = calculation.get_result()
    calculation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(calculation)
    return calculation

# Delete a Calculation
@app.delete("/calculations/{calc_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["calculations"])
def delete_calculation(
    calc_id: str,
    current_user = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    try:
        calc_uuid = UUID(calc_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid calculation id format.")
    calculation = db.query(Calculation).filter(
        Calculation.id == calc_uuid,
        Calculation.user_id == current_user.id
    ).first()
    if not calculation:
        raise HTTPException(status_code=404, detail="Calculation not found.")
    db.delete(calculation)
    db.commit()
    return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, log_level="info")
