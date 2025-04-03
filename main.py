import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import socket
from typing import List, Dict
from pydantic import BaseModel
import os

PORT = 8181

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

app.mount("/static", StaticFiles(directory="static"), name="static")

rooms = [
    {"id": 1, "number": "101", "type": "Single", "price": 100},
    {"id": 2, "number": "102", "type": "Single", "price": 100},
    {"id": 3, "number": "201", "type": "Double", "price": 150},
    {"id": 4, "number": "202", "type": "Double", "price": 150},
    {"id": 5, "number": "301", "type": "Suite", "price": 250},
]

bookings = []

class Booking(BaseModel):
    room_id: int
    date: str
    guest_info: str

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
    return rooms

@app.get("/api/bookings")
async def get_bookings():
    return bookings

@app.post("/api/bookings")
async def create_booking(booking: Booking):
    room = None
    for r in rooms:
        if r["id"] == booking.room_id:
            room = r
            break
            
    if not room:
        return {"error": "Room not found"}
    
    new_booking = {
        "id": len(bookings) + 1,
        "room_id": booking.room_id,
        "room_number": room["number"],
        "room_type": room["type"],
        "date": booking.date,
        "guest_info": booking.guest_info
    }
    
    bookings.append(new_booking)
    return new_booking

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
    )
