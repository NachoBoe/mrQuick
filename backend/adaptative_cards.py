from typing import List, Dict, Any, Optional, Callable, Union
import yaml


class FillIn:
    def __init__(self, id: str, input_type: str, label: str, required: bool = False):
        self.id = id
        self.input_type = input_type
        self.label = label
        self.required = required

class Choice:
    def __init__(self, id: str, choices: List[str], label: str, required: bool = False):
        self.id = id
        self.choices = choices
        self.label = label
        self.required = required

class ButtonAd:
    def __init__(self, id: str, actions: List[str], label: str):
        self.id = id
        self.actions = actions
        self.label = label

class TextAd:
    def __init__(self, id: str, text: str):
        self.id = id
        self.text = text

AdaptiveCardElement = Union[FillIn, Choice, ButtonAd, TextAd]

def parse_adaptive_card(yaml_content: str) -> List[AdaptiveCardElement]:
    parsed = yaml.safe_load(yaml_content)
    elements = []
    for item in parsed:
        if 'FillIn' in item:
            elements.append(FillIn(**item['FillIn']))
        elif 'Choice' in item:
            elements.append(Choice(**item['Choice']))
        elif 'ButtonAd' in item:
            elements.append(ButtonAd(**item['ButtonAd']))
        elif 'TextAd' in item:
            elements.append(TextAd(**item['TextAd']))
    return elements
