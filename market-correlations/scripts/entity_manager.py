#!/usr/bin/env python3
"""
Entity Manager - CRUD operations for market correlation entities.

Usage:
    python entity_manager.py add --id gold --name 黄金 --category commodity ...
    python entity_manager.py get --id gold
    python entity_manager.py list --category commodity
    python entity_manager.py update --id gold --description "..."
    python entity_manager.py delete --id gold
"""

import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path
from init_db import DB_PATH


def add_entity(
    id: str,
    name: str,
    category: str,
    name_en: str = None,
    subcategory: str = None,
    type: str = None,
    unit: str = None,
    description: str = None,
    aliases: list = None,
    metadata: dict = None,
) -> dict:
    """Add a new entity to the database."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            INSERT INTO entities (id, name, name_en, category, subcategory, type, unit, description, aliases, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id, name, name_en, category, subcategory, type, unit, description,
            json.dumps(aliases) if aliases else None,
            json.dumps(metadata) if metadata else None
        ))
        conn.commit()
        
        result = {
            "status": "success",
            "message": f"Entity '{id}' added successfully",
            "entity": {
                "id": id, "name": name, "category": category,
                "name_en": name_en, "subcategory": subcategory, "type": type,
                "unit": unit, "description": description
            }
        }
    except sqlite3.IntegrityError as e:
        result = {"status": "error", "message": f"Entity '{id}' already exists"}
    except sqlite3.Error as e:
        result = {"status": "error", "message": str(e)}
    finally:
        conn.close()
    
    return result


def get_entity(id: str) -> dict:
    """Get an entity by ID."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM entities WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        columns = ["id", "name", "name_en", "category", "subcategory", "type", 
                   "unit", "description", "aliases", "metadata", "created_at", "updated_at"]
        entity = dict(zip(columns, row))
        if entity["aliases"]:
            entity["aliases"] = json.loads(entity["aliases"])
        if entity["metadata"]:
            entity["metadata"] = json.loads(entity["metadata"])
        return {"status": "success", "entity": entity}
    else:
        return {"status": "error", "message": f"Entity '{id}' not found"}


def list_entities(category: str = None, type: str = None, limit: int = 100) -> dict:
    """List entities with optional filters."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = "SELECT id, name, name_en, category, subcategory, type, unit, description FROM entities"
    params = []
    
    if category:
        query += " WHERE category = ?"
        params.append(category)
        if type:
            query += " AND type = ?"
            params.append(type)
    elif type:
        query += " WHERE type = ?"
        params.append(type)
    
    query += f" LIMIT {limit}"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    columns = ["id", "name", "name_en", "category", "subcategory", "type", "unit", "description"]
    entities = [dict(zip(columns, row)) for row in rows]
    
    return {"status": "success", "count": len(entities), "entities": entities}


def update_entity(id: str, **kwargs) -> dict:
    """Update an entity. Only provided fields will be updated."""
    
    # Filter valid fields
    valid_fields = ["name", "name_en", "category", "subcategory", "type", 
                    "unit", "description", "aliases", "metadata"]
    updates = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
    
    if not updates:
        return {"status": "error", "message": "No valid fields to update"}
    
    # Handle JSON fields
    if "aliases" in updates and isinstance(updates["aliases"], list):
        updates["aliases"] = json.dumps(updates["aliases"])
    if "metadata" in updates and isinstance(updates["metadata"], dict):
        updates["metadata"] = json.dumps(updates["metadata"])
    
    updates["updated_at"] = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Build UPDATE query
    fields = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [id]
    
    cursor.execute(f"UPDATE entities SET {fields} WHERE id = ?", values)
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Entity '{id}' updated", "fields_updated": list(updates.keys())}
    else:
        conn.close()
        return {"status": "error", "message": f"Entity '{id}' not found"}


def delete_entity(id: str) -> dict:
    """Delete an entity. Will fail if entity has relations."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if entity has relations
    cursor.execute("SELECT COUNT(*) FROM relations WHERE primary_id = ? OR secondary_id = ?", (id, id))
    count = cursor.fetchone()[0]
    
    if count > 0:
        conn.close()
        return {"status": "error", "message": f"Entity '{id}' has {count} relations. Delete relations first."}
    
    cursor.execute("DELETE FROM entities WHERE id = ?", (id,))
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Entity '{id}' deleted"}
    else:
        conn.close()
        return {"status": "error", "message": f"Entity '{id}' not found"}


def search_entities(query: str, limit: int = 20) -> dict:
    """Search entities by name, name_en, description or aliases.
    
    Supports:
    - Exact match
    - Partial match
    - Alias match
    - Case-insensitive
    """
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Normalize query
    query_lower = query.lower().strip()
    
    # Search in multiple fields
    cursor.execute("""
        SELECT id, name, name_en, category, subcategory, type, unit, description, aliases
        FROM entities
        WHERE name LIKE ? 
           OR name_en LIKE ? 
           OR description LIKE ? 
           OR LOWER(aliases) LIKE ?
        ORDER BY 
            CASE 
                WHEN name = ? THEN 1
                WHEN name LIKE ? THEN 2
                WHEN aliases LIKE ? THEN 3
                ELSE 4
            END
        LIMIT ?
    """, (
        f"%{query}%", f"%{query}%", f"%{query}%", f"%{query_lower}%",
        query, f"{query}%", f"%{query}%",
        limit
    ))
    
    rows = cursor.fetchall()
    conn.close()
    
    entities = []
    for row in rows:
        entity = {
            "id": row[0],
            "name": row[1],
            "name_en": row[2],
            "category": row[3],
            "subcategory": row[4],
            "type": row[5],
            "unit": row[6],
            "description": row[7]
        }
        if row[8]:
            entity["aliases"] = json.loads(row[8])
        entities.append(entity)
    
    return {"status": "success", "count": len(entities), "query": query, "entities": entities}


def find_entity_by_name(name: str) -> dict:
    """Find entity by exact name or alias match.
    
    More precise than search_entities, returns best match.
    """
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    name_lower = name.lower().strip()
    
    # 1. Try exact match on id
    cursor.execute("SELECT * FROM entities WHERE id = ?", (name_lower,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return {"status": "success", "match_type": "id_exact", "entity": _row_to_entity(row)}
    
    # 2. Try exact match on name
    cursor.execute("SELECT * FROM entities WHERE name = ?", (name,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return {"status": "success", "match_type": "name_exact", "entity": _row_to_entity(row)}
    
    # 3. Try exact match on name_en
    cursor.execute("SELECT * FROM entities WHERE name_en = ?", (name,))
    row = cursor.fetchone()
    if row:
        conn.close()
        return {"status": "success", "match_type": "name_en_exact", "entity": _row_to_entity(row)}
    
    # 4. Try alias match (JSON contains)
    cursor.execute("SELECT * FROM entities WHERE aliases LIKE ?", (f'%"{name}"%',))
    row = cursor.fetchone()
    if row:
        conn.close()
        return {"status": "success", "match_type": "alias_exact", "entity": _row_to_entity(row)}
    
    # 5. Try partial match
    cursor.execute("""
        SELECT * FROM entities 
        WHERE name LIKE ? OR name_en LIKE ? OR aliases LIKE ?
        LIMIT 1
    """, (f"%{name}%", f"%{name}%", f'%{name}%'))
    row = cursor.fetchone()
    if row:
        conn.close()
        return {"status": "success", "match_type": "partial", "entity": _row_to_entity(row)}
    
    conn.close()
    return {"status": "error", "message": f"Entity '{name}' not found"}


def _row_to_entity(row) -> dict:
    """Convert database row to entity dict."""
    columns = ["id", "name", "name_en", "category", "subcategory", "type", 
               "unit", "description", "aliases", "metadata", "created_at", "updated_at"]
    entity = dict(zip(columns, row))
    if entity.get("aliases"):
        entity["aliases"] = json.loads(entity["aliases"])
    if entity.get("metadata"):
        entity["metadata"] = json.loads(entity["metadata"])
    return entity


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage market correlation entities")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new entity")
    add_parser.add_argument("--id", required=True, help="Entity ID")
    add_parser.add_argument("--name", required=True, help="Entity name")
    add_parser.add_argument("--category", required=True, help="Category")
    add_parser.add_argument("--name-en", help="English name")
    add_parser.add_argument("--subcategory", help="Subcategory")
    add_parser.add_argument("--type", help="Entity type")
    add_parser.add_argument("--unit", help="Unit")
    add_parser.add_argument("--description", help="Description")
    add_parser.add_argument("--aliases", help="Aliases (comma-separated)")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get an entity")
    get_parser.add_argument("--id", required=True, help="Entity ID")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List entities")
    list_parser.add_argument("--category", help="Filter by category")
    list_parser.add_argument("--type", help="Filter by type")
    list_parser.add_argument("--limit", type=int, default=100, help="Limit results")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update an entity")
    update_parser.add_argument("--id", required=True, help="Entity ID")
    update_parser.add_argument("--name", help="New name")
    update_parser.add_argument("--name-en", help="New English name")
    update_parser.add_argument("--category", help="New category")
    update_parser.add_argument("--subcategory", help="New subcategory")
    update_parser.add_argument("--type", help="New type")
    update_parser.add_argument("--unit", help="New unit")
    update_parser.add_argument("--description", help="New description")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete an entity")
    delete_parser.add_argument("--id", required=True, help="Entity ID")
    
    # Search command
    search_parser = subparsers.add_parser("search", help="Search entities")
    search_parser.add_argument("query", help="Search query")
    search_parser.add_argument("--limit", type=int, default=20, help="Limit results")
    
    args = parser.parse_args()
    
    if args.command == "add":
        aliases = args.aliases.split(",") if args.aliases else None
        result = add_entity(
            args.id, args.name, args.category, args.name_en,
            args.subcategory, args.type, args.unit, args.description, aliases
        )
    elif args.command == "get":
        result = get_entity(args.id)
    elif args.command == "list":
        result = list_entities(args.category, args.type, args.limit)
    elif args.command == "update":
        result = update_entity(args.id, **{k: v for k, v in vars(args).items() if v and k != "id"})
    elif args.command == "delete":
        result = delete_entity(args.id)
    elif args.command == "search":
        result = search_entities(args.query, args.limit)
    else:
        result = {"status": "error", "message": "No command specified"}
    
    print(json.dumps(result, ensure_ascii=False, indent=2))