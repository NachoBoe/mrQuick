import requests
from fuzzywuzzy import fuzz
from fuzzywuzzy import process

def find_closest_match(user_input, options):
    # Use process.extractOne to find the closest match
    closest_match, score = process.extractOne(user_input, options)
    # Get the index one the list
    index = options.index(closest_match)
    return index


def bt_api(method, endpoint, data):
    headers = {}
    headers["clientid"] = "26bfc822b0e67a564e4f22e0e8d6c5016c4664f7d46a96b3737a9ed8e35fa95d"
    headers["apikey"] = "1veN6i3DbnkCwCcJfsKLq7mYCmu6vejn"
    headers["accept"] = "application/json"
    headers["language"] = "ES"
    headers["Content-Type"] = "application/json"
    url = "http://btcanales.dlya.corp:3007/"
    url = url + endpoint
    if method == "post":
        response = requests.post(url, headers=headers, json=data)
    elif method == "get":
        response = requests.get(url, headers=headers, json=data)
    return response.json()

def print_flows(Flows):
    flow_str = ""
    for flow in Flows:
        flow_str += f"\n        Nombre: {flow.__class__.__name__}"
        flow_str += f"\n        Descripción: {flow.descripcion}"
        flow_str += "\n            Frases Disparadoras:"
        for trigger in flow.trigger_phrases:
            flow_str += f"\n                - {trigger}"
    return flow_str

def print_flow_inputs(Flow):
    inputs_str = ""
    inputs_str += "Flujo: " + Flow.__class__.__name__
    inputs_str += "\nDescripcion: " + Flow.__class__.__name__
    inputs_str += "\nEntradas:"
    for input in Flow.entradas:
        inputs_str += f"\n        Id: {input['id']}"
        inputs_str += f"\n        Tipo: {input['tipo']}"
        inputs_str += f"\n        Descripción: {input['descripcion']}"
    return inputs_str