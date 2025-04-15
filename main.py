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

PORT = 8181 # Portnummer för servern

app = FastAPI() # Skapa FastAPI-appen

# Tillåt alla ursprung (CORS)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Servera statiska filer från 'static' mappen
app.mount("/static", StaticFiles(directory="static"), name="static")

# Anslut till MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['hotel_db'] # Välj databas
rooms_collection = db['rooms'] # Välj 'rooms' collection
bookings_collection = db['bookings'] # Välj 'bookings' collection

# Skapa exempelrum om collection är tom
if rooms_collection.count_documents({}) == 0:
    initial_rooms = [
        {"id": 1, "number": "101", "type": "Single", "price": 100},
        {"id": 2, "number": "102", "type": "Single", "price": 100},
        {"id": 3, "number": "201", "type": "Double", "price": 150},
        {"id": 4, "number": "202", "type": "Double", "price": 150},
        {"id": 5, "number": "301", "type": "Suite", "price": 250},
    ]
    rooms_collection.insert_many(initial_rooms)

# Datamodell för en bokning (inkommande data)
class Booking(BaseModel):
    room_id: int
    date: str
    guest_info: str

# Datamodell för en recension (inkommande data)
class BookingReview(BaseModel):
    stars: int

# Hämta klientens IP-adress
def get_client_ip(request: Request):
    forwarded_for = request.headers.get("X-Forwarded-For")
    client_ip = "Unknown"
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    elif request.client:
        client_ip = request.client.host
    return client_ip

# Servera huvudsidan (index.html)
@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

# Servera hotellsidan (hotel.html)
@app.get("/hotel")
async def hotel_page():
    return FileResponse("static/hotel.html")

# Servera statistiksidan (stats.html)
@app.get("/stats")
async def stats_page():
    return FileResponse("static/stats.html")

# API-endpoint för att hämta IP och värdnamn
@app.get("/api/ip")
async def get_ip(request: Request):
    client_ip = get_client_ip(request)
    hostname = "Unknown"
    try:
        hostname = socket.gethostbyaddr(client_ip)[0]
    except socket.herror:
        hostname = "Unknown Hostname"
    except Exception:
        hostname = "Resolution Error"

    return {
        "ip": client_ip,
        "hostname": hostname
    }

# API-endpoint för att hämta alla rum
@app.get("/api/rooms")
async def get_rooms():
    all_rooms = list(rooms_collection.find({}, {"_id": 0}))
    return all_rooms

# API-endpoint för att hämta alla bokningar
@app.get("/api/bookings")
async def get_bookings():
    all_bookings = list(bookings_collection.find({}, {"_id": 0}))
    return all_bookings

# API-endpoint för att hämta statistik
@app.get("/api/stats")
async def get_stats():
    total_rooms = rooms_collection.count_documents({}) # Räkna totalt antal rum

    # Räkna antal rum per typ
    room_types_count = {
        "Single": rooms_collection.count_documents({"type": "Single"}),
        "Double": rooms_collection.count_documents({"type": "Double"}),
        "Suite": rooms_collection.count_documents({"type": "Suite"})
    }

    # Beräkna genomsnittspris
    total_price = 0
    room_count_for_price = 0
    for room in rooms_collection.find({}, {"price": 1, "_id": 0}):
         if "price" in room:
             total_price += room["price"]
             room_count_for_price += 1

    average_room_price = 0
    if room_count_for_price > 0:
        average_room_price = total_price / room_count_for_price

    total_bookings = bookings_collection.count_documents({}) # Räkna totalt antal bokningar

    # Beräkna recensionsstatistik
    total_reviews = 0
    total_stars = 0
    star_distribution = { "1": 0, "2": 0, "3": 0, "4": 0, "5": 0 }
    
    reviews_cursor = bookings_collection.find({"stars": {"$exists": True}}, {"stars": 1, "_id": 0})
    for booking in reviews_cursor:
         stars = booking.get("stars")
         if stars is not None and 1 <= stars <= 5:
             total_reviews += 1
             total_stars += stars
             star_distribution[str(stars)] += 1

    average_rating = 0
    if total_reviews > 0:
         average_rating = total_stars / total_reviews

    review_stats_data = {
         "total_reviews": total_reviews,
         "average_rating": average_rating,
         "distribution": star_distribution
    }

    # Returnera all statistik
    return {
        "total_rooms": total_rooms,
        "total_bookings": total_bookings,
        "room_types": room_types_count,
        "average_room_price": average_room_price,
        "server_status": "Online",
        "review_stats": review_stats_data
    }

# API-endpoint för att skapa en ny bokning
@app.post("/api/bookings")
async def create_booking(booking: Booking):
    room = rooms_collection.find_one({"id": booking.room_id}) # Hitta rummet

    if not room:
        raise HTTPException(status_code=404, detail="Room not found") # Fel om rum inte finns

    current_bookings_count = bookings_collection.count_documents({})
    new_booking_id = current_bookings_count + 1 # Skapa nytt boknings-ID

    # Skapa bokningsdata
    new_booking_data = {
        "id": new_booking_id,
        "room_id": booking.room_id,
        "room_number": room.get("number", "N/A"),
        "room_type": room.get("type", "N/A"),
        "date": booking.date,
        "guest_info": booking.guest_info
    }

    bookings_collection.insert_one(new_booking_data) # Spara i databasen
    
    new_booking_data.pop("_id", None) # Ta bort MongoDB-specifikt _id
    return new_booking_data

# API-endpoint för att uppdatera en bokning med en recension (stjärnor)
@app.put("/api/bookings/{booking_id}")
async def update_booking_review(booking_id: int, review: BookingReview):
    if not (1 <= review.stars <= 5):
        raise HTTPException(status_code=400, detail="Star rating must be between 1 and 5") # Fel om stjärnor är ogiltiga

    find_query = {"id": booking_id}
    update_query = {"$set": {"stars": review.stars}}

    result = bookings_collection.update_one(find_query, update_query) # Uppdatera i databasen

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found") # Fel om bokning inte finns

    if result.modified_count == 0:
        updated_booking = bookings_collection.find_one(find_query, {"_id": 0})
        return updated_booking # Returnera befintlig data om inget ändrades
    
    updated_booking = bookings_collection.find_one(find_query, {"_id": 0}) # Hämta uppdaterad bokning
    return updated_booking

# Kör appen om skriptet körs direkt
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0", 
        port=PORT,
    )
