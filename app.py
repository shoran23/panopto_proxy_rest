from flask import Flask, request
import asyncio

app = Flask(__name__)

recordings = [
    {   
        "id": 123456, 
        "Recording Information": {
            "Title": "Room E52-164 Classroom Recording",
            "Start Time": "11 1 2022 6 27",
            "Duration": "5400"
        }
    },
        {   
        "id": 654321, 
        "Recording Information": {
            "Title": "Room E52-221 Classroom Recording",
            "Start Time": "11 2 2022 6 8",
            "Duration": "5400"
        }
    }
]

rooms = [
    {
        "name": "E52-164",
        "state": "Recording",
        "recording_id": 123456
    },
        {
        "name": "E52-221",
        "state": "Recording",
        "recording_id": 654321
    }
]


async def get_room_state(room_name):    # include the soap request
    await asyncio.sleep(2) # simulation ~ will be removed
    for room in rooms:
        if room["name"] == room_name:
            return room
    return {"error": "room not found"}

@app.get("/room_state/<string:room_name>")
async def get_room_state_route(room_name):
    data = await get_room_state(room_name)
    return data




async def get_recording_information(room_name):     # include the necessary soap requests and data processing
    await asyncio.sleep(2)  # simulation ~ will be removed
    for room in rooms:
        if room["name"] == room_name:
            for recording in recordings:
                if recording["id"] == room["recording_id"]:
                    return recording
    return {"error": "room not found"}

@app.get("/recording_information/<string:room_name>")
async def get_recording_information_route(room_name):
    data = await get_recording_information(room_name)
    return data




async def post_recording_state(room_name, data_request):
    await asyncio.sleep(2) # simulation ~ will be removed
    for room in rooms:
        if room["name"] == room_name:
            # send soap API request with room["id"] and the request data
            room = await get_room_state(room_name)
            if room["state"] == "Recording":
                recording = await get_recording_information(room_name)
                return {"room": room, "recording": recording}
            else:
                return room  
    return {"error": "room not found"}
    
@app.post("/recording_state/<string:room_name>")
async def post_recording_state_route(room_name):
    data_request = request.get_data()
    print(data_request)
    #data = await post_recording_state(room_name,data_request)
    return data_request

            
    