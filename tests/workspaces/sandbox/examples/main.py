
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

app = FastAPI()

class Item(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

db = []

@app.post("/items/", response_model=Item)
def create_item(item: Item):
    if any(x.id == item.id for x in db):
        raise HTTPException(status_code=400, detail="Item with this ID already exists")
    db.append(item)
    return item

@app.get("/items/", response_model=List[Item])
def read_items(skip: int = 0, limit: int = 10):
    return db[skip : skip + limit]

@app.get("/items/{item_id}", response_model=Item)
def read_item(item_id: int):
    item = next((x for x in db if x.id == item_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.put("/items/{item_id}", response_model=Item)
def update_item(item_id: int, item: Item):
    index = next((i for i, x in enumerate(db) if x.id == item_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Item not found")
    db[index] = item
    return item

@app.delete("/items/{item_id}", response_model=Item)
def delete_item(item_id: int):
    index = next((i for i, x in enumerate(db) if x.id == item_id), None)
    if index is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return db.pop(index)
