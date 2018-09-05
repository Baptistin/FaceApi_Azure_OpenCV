import httplib, urllib, json, time
import cv2
import subprocess
from VideoCapture import Device
from datetime import datetime
cam = Device()
import ssl

# This restores the same behavior as before.
context = ssl._create_unverified_context()
name = 'detect'
last_apicall_face_count = 0
last_face_count = 0
first_run = True
filter_count = 0
last_date = 0

faceapi_headers = {
    # Request headers
	'Content-type': 'application/octet-stream',
        'Ocp-Apim-Subscription-Key': '<key>',
}
faceapi_params = urllib.urlencode({
    'returnFaceId': 'true',
    'returnFaceLandmarks': 'false',
    'returnFaceAttributes': 'age,gender,glasses',
})
# Request headers Emotion API
headers = {
    'Content-Type': 'application/octet-stream',
    'Ocp-Apim-Subscription-Key': '<key>',
    
}

faceapi_body = ""
filename = 'imagecr.jpg'

face_cascade = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')

### Connexion webservice FaceApi ###
conn = httplib.HTTPSConnection('westeurope.api.cognitive.microsoft.com')
connexion = httplib.HTTPSConnection('westus.api.cognitive.microsoft.com')

emotion = 0

anger = 0
suprise = 0
happiness = 0
neutral = 0
sadness = 0

def launch_process():
    global filter_count
    global face_cascade
    global last_face_count
    global first_run
    global headers_vitrine
    global last_apicall_face_count
    global emotion_str
    global glasses

    headers_vitrine = {'content-type': 'application/json'}


    while (True):
        print("filter_count = " + str(filter_count))
        records = []
        last_date = datetime.now()
        last_date_str = last_date.strftime('%Y-%m-%d %H:%M:%S')

        print("Tentative : " + last_date_str)
        print("Capture de l'image en cours.")
        cam.saveSnapshot(filename, timestamp=3, boldfont=1)
        img = cv2.imread(filename)
        faces = face_cascade.detectMultiScale(img, 1.1,10)

        json_object = {}
        json_object["persons"] = []
        json_object["nb_personne"] = 0

        print("Nombre de visages photo : " + str(len(faces)))

        ### PARTIE FILTRE ###
        if (len(faces) != last_face_count):
            print("Resultat different")
            if (filter_count > 0 and first_run == False):
                filter_count -= 1
                print("filter_count -1 = " + str(filter_count))


        else:
            print("Meme resultat")
            if (filter_count < 2 and first_run == False):
                filter_count += 1
                print("filter_count +1 = " + str(filter_count))
                time.sleep(1)

        last_face_count = len(faces)

        ### PARTIE APPEL API ####
        if (filter_count == 2 and (first_run == True or len(faces) != last_apicall_face_count)):
            if (len(faces) == 0):
                print("filter_count = 2, nombre de visages : 0")
                print("Envoie FaceAPI")
                json_object["nb_personne"] = 0
                json_person = {}
                json_object['persons'].append(json_person)
                records.append(json_object)
                jsonString = json.dumps(records)
                ### Connexion webservice Vitrine ###
                connection_vitrine = httplib.HTTPSConnection('localhost:8080',context=context)
                connection_vitrine.request("POST", "/faceapi", jsonString, headers=headers_vitrine)
                connection_vitrine.close()
                filter_count = 0
                last_apicall_face_count = len(faces)
            else:
                print("filter_count = 2, nombre de visages : " + str(len(faces)))
                print("Envoie FaceAPI")
                f = open(filename, "rb")
                faceapi_body = f.read()
                f.close()
                conn.request("POST", "/face/v1.0/detect?%s" % faceapi_params, faceapi_body, faceapi_headers)
                
                ### Résultat de la requete FaceAPI ###
                response = conn.getresponse()
                data = response.read()                
                decoded = json.loads(data)
                print(decoded)
                connexion.request("POST", "/emotion/v1.0/recognize", faceapi_body , headers)
                responsemotion = connexion.getresponse()
                datamotion = responsemotion.read()
                decodedmotion = json.loads(datamotion)
                print(datamotion)
                emotion_str = "neutral"
                emotion = decodedmotion[0]['scores']['neutral']
                if (emotion < decodedmotion[0]['scores']['anger']):
                    emotion = decodedmotion[0]['scores']['anger']
                    emotion_str = "anger"

                if (emotion < decodedmotion[0]['scores']['surprise']):
                    emotion = decodedmotion[0]['scores']['surprise']
                    emotion_str = "surprise"

                if (emotion < decodedmotion[0]['scores']['happiness']):
                    emotion = decodedmotion[0]['scores']['happiness']
                    emotion_str = "happiness"

                if (emotion < decodedmotion[0]['scores']['sadness']):
                    emotion = decodedmotion[0]['scores']['sadness']
                    emotion_str = "sadness"
                    
                emotion = 0
                ## TRAITER LE NOUVEAU JSON
                nombrepersonne = len(decoded)
                # print(nombrepersonne)
                json_object["nb_personne"] = str(nombrepersonne)
                for i in range(len(decoded)):
                    sexe = decoded[i]["faceAttributes"]["gender"]
                    age = int(decoded[i]["faceAttributes"]["age"])
                    glasses = decoded[i]["faceAttributes"]["glasses"]
                    json_person = {}
                    json_person["sexe"] = sexe
                    json_person["age"] = age
                    json_person["emotion"] = emotion_str
                    json_person["glasses"] = glasses                    
                    json_object['persons'].append(json_person)
                    print (sexe)
                    print(age)
                    print(emotion_str)
                    print(glasses)
                records.append(json_object)
                jsonString = json.dumps(records)
                ### Connexion webservice Vitrine ###
                filter_count = 0
                last_apicall_face_count = len(faces)
                time.sleep(1)
        else:
            print("Pas d'envoie FaceAPI")
            time.sleep(0.5)
        print("")
        first_run = False


def error_manager(err):
    print(err)
    print(".....................")
    print("Redemarrage du script")
    print(".....................")
    time.sleep(3)
    argument = ""
    proc = subprocess.Popen(['python', 'checkvisage.py', argument], shell=False)


def app_launcher():
    try:
        launch_process()
    except Exception as err:  # catch *all* Exceptions
        print("erreur catchee")
        error_manager(err)


app_launcher()
