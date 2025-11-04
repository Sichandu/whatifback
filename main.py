# from fastapi import FastAPI, HTTPException, Depends, Header
# from fastapi.middleware.cors import CORSMiddleware
# from pymongo import MongoClient
# from pydantic import BaseModel
# from datetime import datetime, timedelta
# from typing import List, Optional
# import secrets
# import os
# from bson import ObjectId

# app = FastAPI(title="WhatIfVerse API")

# # CORS middleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # MongoDB connection
# MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
# client = MongoClient(MONGO_URI)
# db = client.whatifverse

# # Collections
# users_collection = db.users
# thoughts_collection = db.thoughts
# responses_collection = db.responses
# scores_collection = db.scores
# sessions_collection = db.sessions

# # Pydantic models
# class ThoughtCreate(BaseModel):
#     content: str

# class ResponseCreate(BaseModel):
#     thought_id: str
#     content: str

# class ScoreCreate(BaseModel):
#     response_id: str
#     score: int

# class UserCreate(BaseModel):
#     nickname: str

# # Helper function to convert ObjectId to string
# def convert_objectid(obj):
#     if isinstance(obj, ObjectId):
#         return str(obj)
#     elif isinstance(obj, dict):
#         return {k: convert_objectid(v) for k, v in obj.items()}
#     elif isinstance(obj, list):
#         return [convert_objectid(item) for item in obj]
#     return obj

# # Dependency to get current user from token
# async def get_current_user(authorization: str = Header(None)):
#     if not authorization:
#         raise HTTPException(status_code=401, detail="Authorization header missing")
    
#     session = sessions_collection.find_one({"token": authorization, "expires_at": {"$gt": datetime.utcnow()}})
#     if not session:
#         raise HTTPException(status_code=401, detail="Invalid or expired token")
#     return session["nickname"]

# # Routes
# @app.post("/register")
# async def register_user(user: UserCreate):
#     # Check if nickname exists
#     if users_collection.find_one({"nickname": user.nickname}):
#         raise HTTPException(status_code=400, detail="Nickname already exists")
    
#     # Create user
#     users_collection.insert_one({
#         "nickname": user.nickname,
#         "created_at": datetime.utcnow()
#     })
    
#     # Create session token (valid for 30 days)
#     token = secrets.token_urlsafe(32)
#     expires_at = datetime.utcnow() + timedelta(days=30)
    
#     sessions_collection.insert_one({
#         "token": token,
#         "nickname": user.nickname,
#         "created_at": datetime.utcnow(),
#         "expires_at": expires_at
#     })
    
#     return {"token": token, "expires_at": expires_at.isoformat()}

# @app.post("/thoughts")
# async def create_thought(thought: ThoughtCreate, nickname: str = Depends(get_current_user)):
#     thought_data = {
#         "content": thought.content,
#         "user_nickname": nickname,
#         "created_at": datetime.utcnow()
#     }
    
#     result = thoughts_collection.insert_one(thought_data)
#     return convert_objectid({**thought_data, "_id": str(result.inserted_id)})

# @app.get("/thoughts")
# async def get_all_thoughts():
#     thoughts = list(thoughts_collection.find().sort("created_at", -1))
    
#     for thought in thoughts:
#         thought["_id"] = str(thought["_id"])
#         # Get responses for this thought with their scores
#         responses = list(responses_collection.find({"thought_id": thought["_id"]}))
        
#         # Calculate total scores for each response
#         for response in responses:
#             response["_id"] = str(response["_id"])
#             scores = list(scores_collection.find({"response_id": response["_id"]}))
#             response["total_score"] = sum(score["score"] for score in scores)
#             response["score_count"] = len(scores)
        
#         # Sort responses by total score (descending)
#         responses.sort(key=lambda x: x["total_score"], reverse=True)
        
#         # Get top 2 responses
#         thought["top_responses"] = responses[:2]
        
#         # Get other responses (up to 5 initially)
#         thought["other_responses"] = responses[2:7]
        
#         # Total responses count
#         thought["total_responses"] = len(responses)
    
#     return convert_objectid(thoughts)

# @app.post("/responses")
# async def create_response(response: ResponseCreate, nickname: str = Depends(get_current_user)):
#     # Check if thought exists
#     if not thoughts_collection.find_one({"_id": ObjectId(response.thought_id)}):
#         raise HTTPException(status_code=404, detail="Thought not found")
    
#     response_data = {
#         "thought_id": response.thought_id,
#         "content": response.content,
#         "user_nickname": nickname,
#         "created_at": datetime.utcnow()
#     }
    
#     result = responses_collection.insert_one(response_data)
#     return convert_objectid({**response_data, "_id": str(result.inserted_id)})

# @app.post("/scores")
# async def add_score(score: ScoreCreate, nickname: str = Depends(get_current_user)):
#     # Check if response exists
#     response = responses_collection.find_one({"_id": ObjectId(score.response_id)})
#     if not response:
#         raise HTTPException(status_code=404, detail="Response not found")
    
#     # Validate score range
#     if not (-5 <= score.score <= 10):
#         raise HTTPException(status_code=400, detail="Score must be between -5 and 10")
    
#     # Check if user already scored this response
#     existing_score = scores_collection.find_one({
#         "response_id": score.response_id,
#         "user_nickname": nickname
#     })
    
#     if existing_score:
#         # Update existing score
#         scores_collection.update_one(
#             {"_id": existing_score["_id"]},
#             {"$set": {"score": score.score}}
#         )
#     else:
#         # Create new score
#         scores_collection.insert_one({
#             "response_id": score.response_id,
#             "user_nickname": nickname,
#             "score": score.score,
#             "created_at": datetime.utcnow()
#         })
    
#     # Calculate new total score for the response
#     scores = list(scores_collection.find({"response_id": score.response_id}))
#     total_score = sum(s["score"] for s in scores)
    
#     # Update response total score
#     responses_collection.update_one(
#         {"_id": ObjectId(score.response_id)},
#         {"$set": {"total_score": total_score}}
#     )
    
#     return {"total_score": total_score}

# @app.get("/search/{nickname}")
# async def search_by_nickname(nickname: str):
#     # Get thoughts by this user
#     user_thoughts = list(thoughts_collection.find({"user_nickname": {"$regex": f".*{nickname}.*", "$options": "i"}}).sort("created_at", -1))
    
#     for thought in user_thoughts:
#         thought["_id"] = str(thought["_id"])
#         # Get responses for this thought
#         responses = list(responses_collection.find({"thought_id": thought["_id"]}))
        
#         for response in responses:
#             response["_id"] = str(response["_id"])
#             scores = list(scores_collection.find({"response_id": response["_id"]}))
#             response["total_score"] = sum(score["score"] for score in scores)
        
#         responses.sort(key=lambda x: x["total_score"], reverse=True)
#         thought["responses"] = responses
    
#     return convert_objectid(user_thoughts)

# @app.get("/user/{nickname}/exists")
# async def check_nickname_exists(nickname: str):
#     user = users_collection.find_one({"nickname": nickname})
#     return {"exists": user is not None}

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)






from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Optional
import secrets
import os
from bson import ObjectId

app = FastAPI(title="WhatIfVerse API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection - using the same cluster but different database
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
client = MongoClient(MONGO_URI)

# Use a specific database for WhatIfVerse within the same cluster
db = client.whatifverse  # This creates/uses 'whatifverse' database

# Collections (these will be in the 'whatifverse' database)
users_collection = db.users
thoughts_collection = db.thoughts
responses_collection = db.responses
scores_collection = db.scores
sessions_collection = db.sessions

# Pydantic models
class ThoughtCreate(BaseModel):
    content: str

class ResponseCreate(BaseModel):
    thought_id: str
    content: str

class ScoreCreate(BaseModel):
    response_id: str
    score: int

class UserCreate(BaseModel):
    nickname: str

# Helper function to convert ObjectId to string
def convert_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    return obj

# Dependency to get current user from token
async def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Authorization header missing")
    
    session = sessions_collection.find_one({"token": authorization, "expires_at": {"$gt": datetime.utcnow()}})
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return session["nickname"]

# Routes
@app.post("/register")
async def register_user(user: UserCreate):
    # Check if nickname exists in users collection
    existing_user = users_collection.find_one({"nickname": user.nickname})
    
    # Create user if doesn't exist
    if not existing_user:
        users_collection.insert_one({
            "nickname": user.nickname,
            "created_at": datetime.utcnow()
        })
    
    # Create session token (valid for 30 days)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=30)
    
    # Remove any existing sessions for this user
    sessions_collection.delete_many({"nickname": user.nickname})
    
    # Create new session
    sessions_collection.insert_one({
        "token": token,
        "nickname": user.nickname,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at
    })
    
    return {"token": token, "expires_at": expires_at.isoformat()}

@app.post("/thoughts")
async def create_thought(thought: ThoughtCreate, nickname: str = Depends(get_current_user)):
    thought_data = {
        "content": thought.content,
        "user_nickname": nickname,
        "created_at": datetime.utcnow()
    }
    
    result = thoughts_collection.insert_one(thought_data)
    return convert_objectid({**thought_data, "_id": str(result.inserted_id)})

@app.get("/thoughts")
async def get_all_thoughts():
    thoughts = list(thoughts_collection.find().sort("created_at", -1))
    
    for thought in thoughts:
        thought["_id"] = str(thought["_id"])
        # Get responses for this thought
        responses = list(responses_collection.find({"thought_id": thought["_id"]}))
        
        # Calculate total scores for each response
        for response in responses:
            response["_id"] = str(response["_id"])
            scores = list(scores_collection.find({"response_id": response["_id"]}))
            total_score = sum(score["score"] for score in scores)
            response["total_score"] = total_score
            response["score_count"] = len(scores)
        
        # Sort responses by total score (descending)
        responses.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        
        # Get top 2 responses
        thought["top_responses"] = responses[:2]
        
        # Get other responses (up to 5 initially)
        thought["other_responses"] = responses[2:7]
        
        # Total responses count
        thought["total_responses"] = len(responses)
    
    return convert_objectid(thoughts)

@app.post("/responses")
async def create_response(response: ResponseCreate, nickname: str = Depends(get_current_user)):
    # Check if thought exists
    if not thoughts_collection.find_one({"_id": ObjectId(response.thought_id)}):
        raise HTTPException(status_code=404, detail="Thought not found")
    
    response_data = {
        "thought_id": response.thought_id,
        "content": response.content,
        "user_nickname": nickname,
        "created_at": datetime.utcnow()
    }
    
    result = responses_collection.insert_one(response_data)
    return convert_objectid({**response_data, "_id": str(result.inserted_id)})

# @app.post("/scores")
# async def add_score(score: ScoreCreate, nickname: str = Depends(get_current_user)):
#     # Check if response exists
#     response = responses_collection.find_one({"_id": ObjectId(score.response_id)})
#     if not response:
#         raise HTTPException(status_code=404, detail="Response not found")
    
#     # Validate score range
#     if not (-5 <= score.score <= 10):
#         raise HTTPException(status_code=400, detail="Score must be between -5 and 10")
    
#     # Check if user already scored this response
#     existing_score = scores_collection.find_one({
#         "response_id": score.response_id,
#         "user_nickname": nickname
#     })
    
#     if existing_score:
#         # Update existing score
#         scores_collection.update_one(
#             {"_id": existing_score["_id"]},
#             {"$set": {"score": score.score, "updated_at": datetime.utcnow()}}
#         )
#     else:
#         # Create new score
#         scores_collection.insert_one({
#             "response_id": score.response_id,
#             "user_nickname": nickname,
#             "score": score.score,
#             "created_at": datetime.utcnow()
#         })
    
#     # Calculate new total score for the response
#     scores = list(scores_collection.find({"response_id": score.response_id}))
#     total_score = sum(s["score"] for s in scores)
    
#     return {"total_score": total_score, "message": "Score updated successfully"}

@app.post("/scores")
async def add_score(score: ScoreCreate, nickname: str = Depends(get_current_user)):
    # Check if response exists
    response = responses_collection.find_one({"_id": ObjectId(score.response_id)})
    if not response:
        raise HTTPException(status_code=404, detail="Response not found")
    
    # Validate score range
    if not (-5 <= score.score <= 10):
        raise HTTPException(status_code=400, detail="Score must be between -5 and 10")
    
    # Check if user already scored this response
    existing_score = scores_collection.find_one({
        "response_id": score.response_id,
        "user_nickname": nickname
    })
    
    if existing_score:
        # Update existing score
        scores_collection.update_one(
            {"_id": existing_score["_id"]},
            {"$set": {"score": score.score, "updated_at": datetime.utcnow()}}
        )
        print(f"Updated score: User {nickname} changed from {existing_score['score']} to {score.score} for response {score.response_id}")
    else:
        # Create new score
        scores_collection.insert_one({
            "response_id": score.response_id,
            "user_nickname": nickname,
            "score": score.score,
            "created_at": datetime.utcnow()
        })
        print(f"New score: User {nickname} gave {score.score} to response {score.response_id}")
    
    # Calculate new total score for the response from ALL scores
    scores = list(scores_collection.find({"response_id": score.response_id}))
    total_score = sum(s["score"] for s in scores)
    
    print(f"All scores for response {score.response_id}: {[(s['user_nickname'], s['score']) for s in scores]}")
    print(f"Calculated total: {total_score}")
    
    return {"total_score": total_score, "message": "Score updated successfully"}

@app.get("/search/{nickname}")
async def search_by_nickname(nickname: str):
    # Get thoughts by this user
    user_thoughts = list(thoughts_collection.find({
        "user_nickname": {"$regex": f".*{nickname}.*", "$options": "i"}
    }).sort("created_at", -1))
    
    for thought in user_thoughts:
        thought["_id"] = str(thought["_id"])
        # Get responses for this thought
        responses = list(responses_collection.find({"thought_id": thought["_id"]}))
        
        for response in responses:
            response["_id"] = str(response["_id"])
            scores = list(scores_collection.find({"response_id": response["_id"]}))
            response["total_score"] = sum(score["score"] for score in scores)
        
        responses.sort(key=lambda x: x.get("total_score", 0), reverse=True)
        thought["responses"] = responses
    
    return convert_objectid(user_thoughts)

@app.get("/")
async def root():
    return {
        "message": "WhatIfVerse API is running!", 
        "status": "healthy",
        "database": "whatifverse",
        "cluster": "cluster0"
    }

@app.get("/health")
async def health_check():
    # Test database connection
    try:
        # Simple query to test connection
        thoughts_collection.find_one()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy", 
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)