from fastapi import HTTPException


class TicketNotFound(HTTPException):
    def __init__(self):
        super().__init__(status_code=404, detail="Ticket not found")


class Unauthorized(HTTPException):
    def __init__(self):
        super().__init__(status_code=401, detail="Unauthorized")
