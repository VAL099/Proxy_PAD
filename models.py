from pydantic import BaseModel

class ProxyRequest(BaseModel):
    type:str
    content:str | dict