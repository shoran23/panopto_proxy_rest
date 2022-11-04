from flask import Flask, request
from AuthenticatedClientFactory import AuthenticatedClientFactory
from ClientWrapper import ClientWrapper
from panopto_oauth2 import PanoptoOAuth2
from datetime import datetime, timedelta

import datetime
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

def get_recorder_dict():        # populate recorder:recorder_id dict
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

def get_room_name(Id):          # swap from room_name to room_id
    keys=[k for k, v in rooms.items() if v == Id]
    if keys:
        return keys[0]
    return None

def get_room_id(RecorderName):  # swap from room_id to room_name
    return rooms[RecorderName]

async def get_room_state(room_name):    # include the soap request
    await asyncio.sleep(2) # simulation ~ will be removed
    RemoteRecorder = RemoteRecorderManagement_client.call_service("GetRemoteRecordersById",remoteRecorderIds=get_room_id(room_name))
    RR_Name = RemoteRecorder[0]['Name']
    RR_State = RemoteRecorder[0]['State']
    if RR_State == 'Recording' and RemoteRecorder[0]['ScheduledRecordings'] is not None:
        live_recording_id = RemoteRecorder[0]['ScheduledRecordings']['guid'][0]
        return {"name": RR_Name, "state": RR_State, "recording_id": live_recording_id}
    elif RemoteRecorder[0]['ScheduledRecordings'] is not None:
        upcoming_recording = RemoteRecorder[0]['ScheduledRecordings']['guid'][0]
        return {"name": RR_Name, "state": RR_State, "recording_id": upcoming_recording}
    else:
        return {"name": RR_Name, "state": RR_State}
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
    RR_Name = RemoteRecorder[0]['Name']
    RR_State = RemoteRecorder[0]['State']
    # print(RemoteRecorder[0]['ScheduledRecordings'])
    # print(RemoteRecorder[0]['ScheduledRecordings']==None)
    if RemoteRecorder[0]['State'] == "Recording":
        recording_id = RemoteRecorder[0]['ScheduledRecordings']['guid'][0]
        return {"id": recording_id, "Recording Information": Get_SR_by_ID(recording_id)}
    elif RemoteRecorder[0]['ScheduledRecordings'] is not None:
        upcoming_recording = RemoteRecorder[0]['ScheduledRecordings']['guid'][0]
        return {"name": RR_Name, "state": RR_State, "recording_id": upcoming_recording}
    else:
        return {"name": RR_Name, "state": RR_State}
    return {"error": "room not found"}

@app.get("/recording_information/<string:room_name>")
async def get_recording_information_route(room_name):
    data = await get_recording_information(room_name)
    return data

def Start_Recording_By_RoomID(RoomID):
    SR_STARTTIME = datetime.datetime.now() + datetime.timedelta(hours=4)
    SR_ENDTIME = datetime.datetime.now() + datetime.timedelta(hours=4) + datetime.timedelta(hours=1)
    options = {"RecorderSettings":[{"RecorderId": RoomID}]}
    RemoteRecorder = RemoteRecorderManagement_client.call_service("GetRemoteRecordersById",remoteRecorderIds=RoomID)
    if RemoteRecorder[0]['State'] != "Recording":
        Test_ScheduleRecording = RemoteRecorderManagement_client.call_service(
            "ScheduleRecording",
            name="Title of Recording in " + get_room_name(RoomID),
            # folderId="418b7a1e-b39f-4f0e-8329-af32010abca9", # OPTIONAL, WILL USE DEFAULT FOLDER
            isBroadcast="True",
            start=SR_STARTTIME,
            end=SR_ENDTIME,
            recorderSettings=options)
        print(Test_ScheduleRecording)
        return get_room_state(get_room_name(RoomID)) # Return POST success
    else:
        print("Recording in progress")
        return get_room_state(get_room_name(RoomID)) # Return POST fail

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
        return get_room_state(get_room_name(RoomID)) # Return POST success
    else:
        return get_room_state(get_room_name(RoomID)) # Return POST fail

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
        return get_room_state(get_room_name(RoomID)) # Return POST success
    else:
        return get_room_state(get_room_name(RoomID)) # Return POST fail


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
    request_dict = eval(data_request.decode("utf-8"))
    print(request_dict)
    print(type(request_dict))
    match request_dict:
        case {"requested_state": "recording"}:
            print("Recording has Started")
            print(room_name)
            print(type(room_name))
            # print(Start_Recording_By_RoomID(get_room_id(room_name)))
            data = await Start_Recording_By_RoomID(get_room_id(room_name))
            # await Start_Recording_By_RoomID(get_room_id(room_name))
            return str(data).encode()
        case {"requested_state": "stop"}:
            print("Recording has Stopped")
            data = await Stop_Recording_By_RoomID(get_room_id(room_name))
            # print(Stop_Recording_By_RoomID(get_room_id(room_name)))
            return str(data).encode()
        case {"requested_state": "extend"}:
            print("Recording has been Extended")
            data = await Extend_5_Recording_By_RoomID(get_room_id(room_name))
            # print(Extend_5_Recording_By_RoomID(get_room_id(room_name)))
            return str(data).encode()
        case _:
            return {"error": "room not found"}
    #data = await post_recording_state(room_name,data_request)
    return data_request

# Post Examples:
# "POST","recording_state",{"requested_state": "recording"}
# "POST","recording_state",{"requested_state": "stop"}
# "POST","recording_state",{"requested_state": "extend"}