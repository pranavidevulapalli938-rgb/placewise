import os #used to access environment variables from system
from datetime import datetime, timedelta
from dotenv import load_dotenv
from jose import JWTError, jwt #encode the jwt token
from passlib.context import CryptContext #used for hashing and verifying passwords

load_dotenv() #load the environment variables from the system environment

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

SECRET_KEY = os.getenv("SECRET_KEY") #read the secret key from .env file
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60))

if not SECRET_KEY:
    raise ValueError("SECRET_KEY not set in environment") #app creashes immediately if SECRET_KEY is not set, preventing the app from running without a secret key.

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire}) #If current time > exp → token is invalid. We add the expiration time to the token payload so that we can check it later when validating the token.

    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return token

def decode_access_token(token: str):
    try:
        # Decodes the token using your SECRET_KEY from .env
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload  # Returns the dictionary: {"user_id": X, "exp": Y}
    except JWTError:
        return None