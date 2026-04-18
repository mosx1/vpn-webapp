from enum import Enum

class Protocols(Enum):
    xray: int = 2
    amneziawg: int = 3
    xui3: int = 4

class PanelXray(Enum):
    xray: int = 0
    xui: int = 1