import requests
import json

from src import Flow, Step, Activity

from typing import List, Optional, Callable
from pydantic import BaseModel

from utils import bt_api

from src import BaseBot

from utils import find_closest_match

## FUNCIONES AUXILIARES





# FLUJO TRANSFERENCIA

class TransferenciaFlujo(Flow):
    def __init__(self):
        super().__init__(
            trigger_phrases=["transferencia", "quiero hacer una transferencia"],
            steps=[
                Step(self.step_1),
                Step(self.step_2),
                Step(self.step_3),
                Step(self.step_4)
            ],
            entradas=[
                {"id": "monto", "tipo": "float", "descripcion": "Monto a transferir"},
                {"id": "moneda", "tipo": "integer", "descripcion": "Moneda de la transferencia. Las opciones son pesos uruguayos (corresponde a 0) o dolares (corresponde a 22)"},
                {"id": "cuenta_origen", "tipo": "string", "descripcion": "Nombre de la cuenta de origen de la transferencia"},
                {"id": "tipo_destinatario", "tipo": "integer", "descripcion": "Tipo de destinatario de la transferencia. Las opciones son: 0 (en caso de querer transferir a una cuenta propia), 1 (en caso de querer transferir a un beneficiario precargado) o 2 (en caso de querer transferir a un nuevo beneficiario)"},
                {"id": "cuenta_destino", "tipo": "string", "descripcion": "Nombre de la cuenta de destino de la transferencia"}
                ],
            descripcion = "Este flujo permite realizar una transferencia."
        )
        self.default_inputs = dict()
        self.FLOW_MEMORY = dict()
        self.PARAMS_MEMORY = dict()

    async def step_1(self, bot: 'BaseBot', activity: Activity):
        
        if "tipo_destinatario" in self.default_inputs:
            self.PARAMS_MEMORY["tipo_destintatario"] = int(self.default_inputs["tipo_destinatario"])
            await self.go_to_step(bot, 1)
            return
    
        response = Activity(
                    type="text",
                    content="A que tipo de cuenta desea transferir? \n1. Mis Cuentas \n2. Mis Beneficiarios \n3. Nuevo Beneficiario",
                    timestamp="2024-07-25T12:34:56Z",
                    sender="bot",
                )
        await bot.websocket.send_json(response.dict())
        bot.state_memory.append(response)
        
        response_sug = Activity(
            type="suggestion",
            content="",
            timestamp="2024-07-25T12:34:56Z",
            sender="bot",
            suggestion_content = ["Mis Cuentas", "Mis Beneficiarios", "Nuevo Beneficiario"]
        )
        await bot.websocket.send_json(response_sug.dict())
        bot.state_memory.append(response_sug)

    async def step_2(self, bot: 'BaseBot', activity: Activity):
        
        if "tipo_destinatario" not in self.default_inputs:
            self.PARAMS_MEMORY["tipo_destintatario"] = ["Mis Cuentas", "Mis Beneficiarios", "Nuevo Beneficiario"].index(activity.content)
        
        endpoint = "get_accounts"
        data = {
        "Oper": 1,
        "Estado": "C",
        "Page": 1,
        "Moneda": [0]
        }
        cuentas = bt_api("post", endpoint, data)["data"]["Cuentas"]
        nombre_cuentas = [cuenta["Nombre"] for cuenta in cuentas]
        saldo_cuentas = [cuenta["Saldo"] for cuenta in cuentas]
        moneda_cuentas = [cuenta["Moneda"] for cuenta in cuentas]
        cuentas_yaml = ""
        self.PARAMS_MEMORY["cuentas"] = cuentas
            
        print(self.default_inputs)
        if "monto" in self.default_inputs:
            default_monto = "\n    default: " + str(self.default_inputs["monto"])
        else:
            default_monto = ""
        if "moneda" in self.default_inputs:
            default_moneda = "\n    default: " + '"' + str(self.default_inputs["moneda"]) + '"'
        else:
            default_moneda = ""
        if "cuenta_origen" in self.default_inputs:
            default_cuenta_origen = "\n    default: " + '"' + str(find_closest_match(self.default_inputs["cuenta_origen"],nombre_cuentas)) + '"'
        else:
            default_cuenta_origen = ""
        if "cuenta_destino" in self.default_inputs:
            default_cuenta_destino = "\n    default: " + '"' + str(find_closest_match(self.default_inputs["cuenta_destino"],nombre_cuentas)) + '"'
        else:
            default_cuenta_destino = ""
        for i in range(len(nombre_cuentas)):
            cuentas_yaml += f'\n      - title: "{nombre_cuentas[i]} ({saldo_cuentas[i]} {moneda_cuentas[i]})"\n        value: "{i}"'
        card_content = f"""
- Choice:{default_cuenta_origen}
    id: cuenta_origen
    options:{cuentas_yaml}
    label: "Cuenta de Origen"
    required: true
- Choice:{default_cuenta_destino}
    id: cuenta_destino
    options:{cuentas_yaml}
    label: "Cuenta Destino"
    required: true
- FillIn:{default_monto}
    id: Monto
    input_type: number
    label: "Monto"
    required: true
- Choice:{default_moneda}
    id: moneda
    options:
        - title: "UY"
          value: "0"
        - title: "USD"
          value: "22"
    label: "Moneda"
    required: true
- ButtonAd:
    id: transferir
    actions:
        - submit
    label: "Transferir"
        """
        response = Activity(
            type="adaptive_card",
            content="",
            timestamp="2024-07-25T12:34:56Z",
            sender="bot",
            card_content=card_content
        )
        await bot.websocket.send_json(response.dict())
        bot.state_memory.append(response)
        
    async def step_3(self, bot: 'BaseBot', activity: Activity):
        ans = json.loads(activity.content)
        monto= float(ans["Monto"])
        moneda =int(ans["moneda"])
        cuenta_origen = self.PARAMS_MEMORY["cuentas"][int(ans["cuenta_origen"])]['Producto']
        cuenta_destino = self.PARAMS_MEMORY["cuentas"][int(ans["cuenta_destino"])]['Producto']
        print(cuenta_origen)
        print(cuenta_destino)
        endpoint = "transfers_myaccounts_confirm"
        data = {
            "CuentaOrigen": cuenta_origen,
            "CuentaDestino":cuenta_destino,
            "Moneda": moneda,
            "Monto": monto,
            "Concepto": "Referencia"
        }
        transf_status = bt_api("post", endpoint, data)
        print(transf_status)
        transf_status = transf_status["data"]
        transfer_code = transf_status["Numerador"]
        self.PARAMS_MEMORY["transfer_code"] = transfer_code
        mondeda_str = "$" if moneda == 0 else "U$S"
        response = Activity(
            type="message",
            content="Se estan por transferir " + str(ans["Monto"]) + mondeda_str + " de la cuenta " + self.PARAMS_MEMORY["cuentas"][int(ans["cuenta_origen"])]['Nombre'] + " a la cuenta " + self.PARAMS_MEMORY["cuentas"][int(ans["cuenta_destino"])]['Nombre']+  ". Para confirmar la transferencia, envie el siguiente código de 4 dígitos " + str(transfer_code) ,
            timestamp="2024-07-25T12:34:56Z",
            sender="bot",
        )
        await bot.websocket.send_json(response.dict())
        bot.state_memory.append(response)  

    async def step_4(self, bot: 'BaseBot', activity: Activity):
        ans = int(activity.content)
        if ans == self.PARAMS_MEMORY["transfer_code"]:
            endpoint = "transfers_myaccounts_reconfirm"
            data = {
            "Numerador": self.PARAMS_MEMORY["transfer_code"],
            }
            confirmation_status = bt_api("post", endpoint, data)
            print(confirmation_status)
            if confirmation_status["success"] == True:
                response = Activity(
                    type="message",
                    content="Transferencia realizada con éxito. \nNúmero de Control:  " + confirmation_status["data"]["NroControl"],
                    timestamp="2024-07-25T12:34:56Z",
                    sender="bot",
                )
            else:
                response = Activity(
                    type="message",
                    content="Ocurrio un error. Por favor intente nuevamente.",
                    timestamp="2024-07-25T12:34:56Z",
                    sender="bot",
                )
            await bot.websocket.send_json(response.dict())
            bot.state_memory.append(response)
        else:
            response = Activity(
                type="message",
                content="Código incorrecto. La transferencia ha sido cancelada.",
                timestamp="2024-07-25T12:34:56Z",
                sender="bot",
            )
            await bot.websocket.send_json(response.dict())
            bot.state_memory.append(response)


class ConsultaCuentasFlujo(Flow):
    def __init__(self):
        super().__init__(
            trigger_phrases=["quiero ver mis cuentas", "consultar saldo", "saldo", "mis cuentas"],
            steps=[
                Step(self.step_1)
            ],
            entradas=[],
            descripcion = "Este flujo permite consultar las cuentas del usuario."
        )
        self.FLOW_MEMORY = dict()
        self.PARAMS_MEMORY = dict()

    async def step_1(self, bot: 'BaseBot', activity: Activity):
        endpoint = "get_accounts"
        data = {
        "Oper": 1,
        "Estado": "C",
        "Page": 1,
        "Moneda": [0]
        }
        cuentas = bt_api("post", endpoint, data)["data"]["Cuentas"]
        nombre_cuentas = [cuenta["Nombre"] for cuenta in cuentas]
        saldo_cuentas = [cuenta["Saldo"] for cuenta in cuentas]
        moneda_cuentas = [cuenta["Moneda"] for cuenta in cuentas]
        numero_cuentas = [cuenta["ProdShort"] for cuenta in cuentas]

        cuentas_str = ""
        for i in range(len(nombre_cuentas)):
            cuentas_str += f'{nombre_cuentas[i]} \n{numero_cuentas[i]} \n{moneda_cuentas[i]}{saldo_cuentas[i]} \n\n'
        cuentas_str = cuentas_str[:-2]
        response = Activity(
                type="message",
                content=cuentas_str,
                timestamp="2024-07-25T12:34:56Z",
                sender="bot",
            )
        await bot.websocket.send_json(response.dict())
        bot.state_memory.append(response)
    
        
        
        
        
all_flows = [TransferenciaFlujo(),ConsultaCuentasFlujo()]





