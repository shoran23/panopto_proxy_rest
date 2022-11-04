from flask import Flask, request
from AuthenticatedClientFactory import AuthenticatedClientFactory
from ClientWrapper import ClientWrapper
from panopto_oauth2 import PanoptoOAuth2
from datetime import datetime, timedelta

import asyncio

server = "mitsloan.hosted.panopto.com"
client_id = "bbbbf279-f114-43b9-925c-adf2000adef8"      # id and secret to be stored elsewehere
client_secret = "mL5AX3gx3fzPO/Jy//IyYyCfKz2Kkn0NrsDq5dTAWp8=" 

oauth2 = PanoptoOAuth2(server, client_id, client_secret, False)
oauth_token = oauth2.get_access_token_authorization_code_grant()

cookie = None
username = 'admin'
password = '<password>'
auth = AuthenticatedClientFactory(
    server,
    cookie,
    oauth_token,
    username, password,
    verify_ssl=server != 'localhost')

RemoteRecorderManagement_client = auth.get_client('RemoteRecorderManagement')
SessionManagement_client = auth.get_client('SessionManagement')    

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

def get_recorder_dict():        # populate dict
    Grand_Dict_ListofRecorders = RemoteRecorderManagement_client.call_service("ListRecorders",pagination=50)
    ListofRecorders = Grand_Dict_ListofRecorders["PagedResults"]["RemoteRecorder"]
    DOR = {}
    for Recorders in ListofRecorders:
        Recorder_Name = Recorders["Name"]
        Recorder_ID = Recorders["Id"]
        DOR.update({Recorder_Name:Recorder_ID})
    return DOR
rooms = get_recorder_dict()
# print(rooms)

def get_room_name(Id):          # s
    keys=[k for k, v in rooms.items() if v == Id]
    if keys:
        return keys[0]
    return None

def get_room_id(RecorderName):
    return rooms[RecorderName]

async def get_room_state(room_name):    # include the soap request
    await asyncio.sleep(2) # simulation ~ will be removed
    RemoteRecorder = RemoteRecorderManagement_client.call_service("GetRemoteRecordersById",remoteRecorderIds=get_room_id(room_name))
    RR_Name = RemoteRecorder[0]['Name']
    RR_State = RemoteRecorder[0]['State']
    if RR_State == 'Recording':
        live_recording_id = RemoteRecorder[0]['ScheduledRecordings']['guid'][0]
        return {"name": RR_Name, "state": RR_State, "recording_id": live_recording_id}
    else:
        return {"name": RR_Name, "state": RR_State} # include next recording_id if available?
    return {"error": "room not found"}

@app.get("/room_state/<string:room_name>")
async def get_room_state_route(room_name):
    data = await get_room_state(room_name)
    return data

def Get_SR_by_ID(sessionId):
    ScheduledRecording_detail = SessionManagement_client.call_service('GetSessionsById',sessionIds=sessionId)
    SR_Name = ScheduledRecording_detail[0]["Name"]
    SR_StartTime = ScheduledRecording_detail[0]["StartTime"]
    SR_Duration = ScheduledRecording_detail[0]["Duration"]
    return {"Title": SR_Name,"Start Time": SR_StartTime,"Duration": SR_Duration}

async def get_recording_information(room_name):     # include the necessary soap requests and data processing
    # await asyncio.sleep(2)  # simulation ~ will be removed
    RemoteRecorder = RemoteRecorderManagement_client.call_service("GetRemoteRecordersById",remoteRecorderIds=get_room_id(room_name))
    if RemoteRecorder[0]['State'] == "Recording":
        recording_id = RemoteRecorder[0]['ScheduledRecordings']['guid'][0]
        return {"id": recording_id, "Recording Information": Get_SR_by_ID(recording_id)}
    # else:
    #     print(RemoteRecorder[0]['ScheduledRecordings']['guid'])
        # print(RemoteRecorder[0]['ScheduledRecordings']['guid'])
        # if RemoteRecorder[0]['ScheduledRecordings']['guid'] is not None:
        #     RR_Name = RemoteRecorder[0]['Name']
        #     RR_State = RemoteRecorder[0]['State']
        #     return {"name": RR_Name, "state": RR_State, "recording_id": upcoming_recording}
    return {"error": "room not found"}

@app.get("/recording_information/<string:room_name>")
async def get_recording_information_route(room_name):
    data = await get_recording_information(room_name)
    return data

def Start_Recording_By_RoomID(RoomID):
    SR_STARTTIME = datetime.datetime.now() + datetime.timedelta(hours=4)
    SR_ENDTIME = datetime.datetime.now() + datetime.timedelta(hours=4) + datetime.timedelta(hours=1)
    options = {"RecorderSettings":[{"RecorderId": RoomID}]}

    Test_ScheduleRecording = RemoteRecorderManagement_client.call_service(
        "ScheduleRecording",
        name="Title of Recording in " + get_room_name(RoomID),
        # folderId="418b7a1e-b39f-4f0e-8329-af32010abca9", # OPTIONAL, WILL USE DEFAULT FOLDER
        isBroadcast="True",
        start=SR_STARTTIME,
        end=SR_ENDTIME,
        recorderSettings=options)
    print(Test_ScheduleRecording)
    print("Recording has started.")

def Stop_Recording_By_RoomID(RoomID):
    # Check if a recording is taking place
    RemoteRecorder = RemoteRecorderManagement_client.call_service("GetRemoteRecordersById",remoteRecorderIds=RoomID)
    RR_State = RemoteRecorder[0]['State']
    if RR_State == 'Recording':
        SR_ENDTIME = datetime.datetime.now() + datetime.timedelta(hours=4)
        Current_Recording = RemoteRecorder[0]['ScheduledRecordings']['guid'][0]
        Test_ScheduleRecording = RemoteRecorderManagement_client.call_service(
            "UpdateRecordingTime",
            sessionId=Current_Recording,
            end=SR_ENDTIME)
        print(Test_ScheduleRecording)
        print("Recording has been stopped.")
    else:
        return get_room_state(RoomID)

def Extend_5_Recording_By_RoomID(RoomID):
    # Check if a recording is taking place
    RemoteRecorder = RemoteRecorderManagement_client.call_service("GetRemoteRecordersById",remoteRecorderIds=RoomID)
    RR_State = RemoteRecorder[0]['State']
    if RR_State == 'Recording':
        Current_Recording = RemoteRecorder[0]['ScheduledRecordings']['guid'][0]
        Calculated_EndTime = Get_SR_by_ID(Current_Recording)['Start Time'] + datetime.timedelta(seconds=Get_SR_by_ID(Current_Recording)['Duration'])
        print("Current EndTime: ", Calculated_EndTime)
        Test_ScheduleRecording = RemoteRecorderManagement_client.call_service(
            "UpdateRecordingTime",
            sessionId=Current_Recording,
            # start=SR_STARTTIME,
            end=Calculated_EndTime+datetime.timedelta(minutes=5))
        print(Test_ScheduleRecording)
        print("Recording extended 5 minutes.")
    else:
        return get_room_state(RoomID)


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

            
    