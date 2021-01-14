import json

def intListToString(l):
    return ' '.join([str(i) for i in l])

def stringToIntList(string):
    return [int(i) for i in string.split()]

def stringToJSON(string):
    try:
        return json.loads(string)
    except:
        print('JSON parse error')
        return -1


def handleDesincronization(streamCount, solitaire, msgLen):
    if streamCount > solitaire.streamCount + msgLen:
        solitaire.__getKeysTream__(streamCount - solitaire.streamCount - msgLen)