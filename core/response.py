from rest_framework.response import Response
from rest_framework import status

class CustomResponse(Response):
    def __init__(self, data=None, status=None, valid=True):
        super().__init__(data, valid, status)

        if valid:
            self.data = {
                "valid": True,
                "data": data,
                "status": status,
            }
        else:
            self.data = {
                "valid": False,
                "data": data,
                "status": status,
            }