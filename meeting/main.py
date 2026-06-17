import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from meeting.handle_meeting_router import router  # your Recall AI webhook router

app = FastAPI()

# Include Recall AI webhook router
app.include_router(router)

# Store current status in memory
current_status = "Waiting for participants."

# Data model for POST requests
class StatusUpdate(BaseModel):
    status: str

# Serve frontend files
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))

@app.get("/status")
async def get_status():
    return {"status": current_status}

@app.post("/status")
async def set_status(update: StatusUpdate):
    global current_status
    current_status = update.status
    return {"message": "Status updated", "status": current_status}

if __name__ == "__main__":
    uvicorn.run("meeting.main:app", host="0.0.0.0", port=3000, reload=True)

