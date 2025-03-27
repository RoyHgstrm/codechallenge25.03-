import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import socket

PORT=8181

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "Unknown"

@app.get("/")
async def read_root():
    return FileResponse("static/index.html")

@app.get("/api/ip")
async def get_ip(request: Request):
    client_ip = get_client_ip(request)
    try:
        # Get hostname for the IP
        hostname = socket.gethostbyaddr(client_ip)[0]
    except:
        hostname = "Unknown"
    
    return {
        "ip": client_ip,
        "hostname": hostname
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        ssl_keyfile="/etc/letsencrypt/privkey.pem",
        ssl_certfile="/etc/letsencrypt/fullchain.pem",
    )
