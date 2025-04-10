import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import socket
from typing import List, Dict
from pydantic import BaseModel
import os
from pymongo import MongoClient

PORT = 8181

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory="static"), name="static")

client = MongoClient('mongodb://localhost:27017/')
db = client['hotel_db']
rooms_collection = db['rooms']
bookings_collection = db['bookings']

if rooms_collection.count_documents({}) == 0:
    rooms_collection.insert_many([
        {"id": 1, "number": "101", "type": "Single", "price": 100},
        {"id": 2, "number": "102", "type": "Single", "price": 100},
        {"id": 3, "number": "201", "type": "Double", "price": 150},
        {"id": 4, "number": "202", "type": "Double", "price": 150},
        {"id": 5, "number": "301", "type": "Suite", "price": 250},
    ])

class Booking(BaseModel):
    room_id: int
    date: str
    guest_info: str

class BookingReview(BaseModel):
    stars: int

def get_client_ip(request: Request):
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "Unknown"

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/hotel")
async def hotel_page():
    return FileResponse("static/hotel.html")

@app.get("/stats")
async def stats_page():
    return FileResponse("static/stats.html")

@app.get("/api/ip")
async def get_ip(request: Request):
    client_ip = get_client_ip(request)
    try:
        hostname = socket.gethostbyaddr(client_ip)[0]
    except:
        hostname = "Unknown"
    
    return {
        "ip": client_ip,
        "hostname": hostname
    }

@app.get("/api/rooms")
async def get_rooms():
    rooms = list(rooms_collection.find({}, {"_id": 0}))
    return rooms

@app.get("/api/bookings")
async def get_bookings():
    bookings = list(bookings_collection.find({}, {"_id": 0}))
    return bookings

@app.get("/api/stats")
async def get_stats():
    total_rooms = rooms_collection.count_documents({})
    
    room_types = {
        "Single": rooms_collection.count_documents({"type": "Single"}),
        "Double": rooms_collection.count_documents({"type": "Double"}),
        "Suite": rooms_collection.count_documents({"type": "Suite"})
    }
    
    room_prices = [room["price"] for room in rooms_collection.find({}, {"price": 1, "_id": 0})]
    avg_price = sum(room_prices) / len(room_prices) if room_prices else 0
    
    total_bookings = bookings_collection.count_documents({})
    
    bookings_with_reviews = list(bookings_collection.find({"stars": {"$exists": True}}, {"stars": 1, "_id": 0}))
    total_reviews = len(bookings_with_reviews)
    
    review_stats = {
        "total_reviews": total_reviews,
        "average_rating": 0,
        "distribution": {
            "1": 0, "2": 0, "3": 0, "4": 0, "5": 0
        }
    }
    
    if total_reviews > 0:
        total_stars = sum(booking["stars"] for booking in bookings_with_reviews)
        review_stats["average_rating"] = total_stars / total_reviews
        
        for booking in bookings_with_reviews:
            stars = booking["stars"]
            if 1 <= stars <= 5:
                review_stats["distribution"][str(stars)] += 1
    
    return {
        "total_rooms": total_rooms,
        "total_bookings": total_bookings,
        "room_types": room_types,
        "average_room_price": avg_price,
        "server_status": "Online",
        "review_stats": review_stats
    }

@app.post("/api/bookings")
async def create_booking(booking: Booking):
    room = rooms_collection.find_one({"id": booking.room_id})
            
    if not room:
        return {"error": "Room not found"}
    
    booking_id = bookings_collection.count_documents({}) + 1
    
    new_booking = {
        "id": booking_id,
        "room_id": booking.room_id,
        "room_number": room["number"],
        "room_type": room["type"],
        "date": booking.date,
        "guest_info": booking.guest_info
    }
    
    bookings_collection.insert_one(new_booking)
    new_booking.pop("_id", None)
    return new_booking

@app.put("/api/bookings/{booking_id}")
async def update_booking_review(booking_id: int, review: BookingReview):
    if review.stars < 1 or review.stars > 5:
        raise HTTPException(status_code=400, detail="Star rating must be between 1 and 5")
    
    booking = bookings_collection.find_one({"id": booking_id})
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    result = bookings_collection.update_one(
        {"id": booking_id},
        {"$set": {"stars": review.stars}}
    )
    
    if result.modified_count == 0:
        return {"message": "No changes made to the booking"}
    
    updated_booking = bookings_collection.find_one({"id": booking_id}, {"_id": 0})
    return updated_booking

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
    )
