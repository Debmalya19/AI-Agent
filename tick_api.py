"""
FastAPI REST API for the ticking system
"""

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime
import json
import asyncio

from ticking_service import TickingService, TicketContextRetriever, TicketStatus, TicketPriority, TicketCategory
from database import get_db_session

app = FastAPI(title="Ticking System API", version="1.0.0")

# Pydantic models
class TicketCreate(BaseModel):
    title: str
    description: str
    customer_id: Optional[int] = None
    priority: str = "medium"
    category: str = "general"
    tags: Optional[List[str]] = None

class TicketUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_agent_id: Optional[int] = None

class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    status: str
    priority: str
    category: str
    customer_id: Optional[int]
    assigned_agent_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    tags: Optional[str]

class CommentCreate(BaseModel):
    ticket_id: int
    comment: str
    author_id: Optional[int] = None
    is_internal: bool = False

# Dependency
def get_db():
    db = next(get_db_session())
    try:
        yield db
    finally:
        db.close()

@app.post("/tickets", response_model=TicketResponse)
def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    """Create a new ticket"""
    service = TickingService(db)
    
    try:
        priority = TicketPriority(ticket.priority)
        category = TicketCategory(ticket.category)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    created_ticket = service.create_ticket(
        title=ticket.title,
        description=ticket.description,
        customer_id=ticket.customer_id,
        priority=priority,
        category=category,
        tags=ticket.tags
    )
    
    return created_ticket

@app.get("/tickets/{ticket_id}", response_model=TicketResponse)
def get_ticket(ticket_id: int, db: Session = Depends(get_db)):
    """Get a specific ticket"""
    service = TickingService(db)
    ticket = service.get_ticket(ticket_id)
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return ticket

@app.get("/tickets", response_model=List[TicketResponse])
def list_tickets(
    status: Optional[str] = None,
    customer_id: Optional[int] = None,
    priority: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """List tickets with optional filters"""
    service = TickingService(db)
    
    try:
        status_enum = TicketStatus(status) if status else None
        priority_enum = TicketPriority(priority) if priority else None
        category_enum = TicketCategory(category) if category else None
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    tickets = service.get_tickets(
        status=status_enum,
        customer_id=customer_id,
        priority=priority_enum,
        category=category_enum,
        limit=limit,
        offset=offset
    )
    
    return tickets

@app.put("/tickets/{ticket_id}")
def update_ticket(ticket_id: int, update: TicketUpdate, db: Session = Depends(get_db)):
    """Update ticket status, priority, or assignment"""
    service = TickingService(db)
    
    success = True
    
    if update.status:
        try:
            status_enum = TicketStatus(update.status)
            success = service.update_ticket_status(ticket_id, status_enum)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    
    if update.assigned_agent_id is not None:
        success = service.assign_ticket(ticket_id, update.assigned_agent_id) and success
    
    if not success:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return {"message": "Ticket updated successfully"}

@app.post("/tickets/{ticket_id}/comments")
def add_comment(ticket_id: int, comment: CommentCreate, db: Session = Depends(get_db)):
    """Add a comment to a ticket"""
    service = TickingService(db)
    
    ticket_comment = service.add_comment(
        ticket_id=ticket_id,
        comment=comment.comment,
        author_id=comment.author_id,
        is_internal=comment.is_internal
    )
    
    if not ticket_comment:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return {"message": "Comment added successfully", "comment_id": ticket_comment.id}

@app.get("/tickets/{ticket_id}/context")
def get_ticket_context(ticket_id: int, db: Session = Depends(get_db)):
    """Get context for a ticket including customer info and similar tickets"""
    service = TickingService(db)
    context_retriever = TicketContextRetriever(db)
    
    ticket = service.get_ticket(ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    customer_context = {}
    if ticket.customer_id:
        customer_context = context_retriever.get_customer_context(ticket.customer_id)
    
    similar_tickets = context_retriever.get_similar_tickets(ticket.title)
    
    return {
        "ticket": ticket,
        "customer_context": customer_context,
        "similar_tickets": similar_tickets
    }

@app.get("/statistics")
def get_statistics(db: Session = Depends(get_db)):
    """Get ticket statistics"""
    service = TickingService(db)
    return service.get_ticket_statistics()

@app.get("/search")
def search_tickets(query: str, limit: int = 50, db: Session = Depends(get_db)):
    """Search tickets"""
    service = TickingService(db)
    tickets = service.search_tickets(query, limit)
    return tickets

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/chat/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket, client_id)
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process the message (you can add your chat logic here)
            response = {
                "type": "response",
                "message": f"Echo: {message_data.get('message', '')}",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send response back to the same client
            await manager.send_personal_message(json.dumps(response), client_id)
            
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        print(f"WebSocket error: {e}")
        manager.disconnect(client_id)

# Chat endpoint for HTTP fallback
@app.post("/chat")
async def chat_endpoint(request: dict):
    """HTTP fallback endpoint for chat when WebSocket is not available"""
    query = request.get("query", "")
    
    # Simple response logic - you can integrate with your RAG system here
    responses = {
        "how do i reset my password": "To reset your password, go to the login page and click 'Forgot Password'. Follow the instructions sent to your email.",
        "what are your support hours": "Our support team is available 24/7 via chat and email. Phone support is available from 9 AM to 6 PM EST, Monday to Friday.",
        "how can i check my data usage": "You can check your data usage by logging into your account dashboard and navigating to the 'Usage' section.",
        "how do i upgrade my plan": "To upgrade your plan, log into your account, go to 'Billing' > 'Change Plan', and select your desired plan.",
        "how to contact customer support": "You can contact customer support through this chat, email us at support@company.com, or call 1-800-SUPPORT."
    }
    
    # Find matching response
    query_lower = query.lower()
    for key, response in responses.items():
        if key in query_lower:
            return {"summary": response}
    
    return {"summary": "I'm here to help! Could you please provide more details about your question?"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
