#!/usr/bin/env python3
"""
Relation Manager - CRUD operations for market correlations.

Usage:
    python relation_manager.py add --primary gold --primary-dir up --secondary silver ...
    python relation_manager.py get --id rel-001
    python relation_manager.py list --entity gold
    python relation_manager.py update --id rel-001 --strength strong
    python relation_manager.py delete --id rel-001
"""

import sqlite3
import json
import argparse
from datetime import datetime
from pathlib import Path
from init_db import DB_PATH


def generate_relation_id(primary_id: str, secondary_id: str) -> str:
    """Generate a unique relation ID."""
    import hashlib
    hash_input = f"{primary_id}-{secondary_id}-{datetime.now().isoformat()}"
    hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:6]
    return f"rel-{primary_id}-{secondary_id}-{hash_suffix}"


def add_relation(
    primary_id: str,
    secondary_id: str,
    direction: str,
    logic: str,
    strength: str = None,
    lag: str = None,
    confidence: str = None,
    source: str = None,
    tags: list = None,
    notes: str = None,
    id: str = None,
) -> dict:
    """Add a new relation to the database.
    
    Args:
        primary_id: Primary entity ID (assumes upward direction)
        secondary_id: Secondary entity ID
        direction: 'up' (positive correlation) or 'down' (negative correlation)
        logic: Description of the correlation logic
        strength: 'strong', 'medium', or 'weak'
        lag: 'immediate', 'short-term', or 'long-term'
    """
    
    # Validate direction
    valid_directions = ["up", "down"]
    if direction not in valid_directions:
        return {"status": "error", "message": f"Invalid direction. Must be one of: {valid_directions} ('up' = 正相关, 'down' = 负相关)"}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if entities exist
    cursor.execute("SELECT id, name FROM entities WHERE id = ?", (primary_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"status": "error", "message": f"Primary entity '{primary_id}' not found"}
    primary_name = result[1]
    
    cursor.execute("SELECT id, name FROM entities WHERE id = ?", (secondary_id,))
    result = cursor.fetchone()
    if not result:
        conn.close()
        return {"status": "error", "message": f"Secondary entity '{secondary_id}' not found"}
    secondary_name = result[1]
    
    # Generate ID if not provided
    if not id:
        import hashlib
        from datetime import datetime
        hash_input = f"{primary_id}-{secondary_id}-{datetime.now().isoformat()}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:6]
        id = f"rel-{primary_id}-{secondary_id}-{hash_suffix}"
    
    try:
        cursor.execute("""
            INSERT INTO relations (
                id, primary_id, secondary_id, direction, strength, logic, lag, confidence, source, tags, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id, primary_id, secondary_id, direction, strength, logic, lag, confidence, source,
            json.dumps(tags) if tags else None, notes
        ))
        conn.commit()
        conn.close()
        
        dir_desc = "正相关" if direction == "up" else "负相关"
        result = {
            "status": "success",
            "message": f"Relation added: {primary_name}↑ → {secondary_name}{'↑' if direction == 'up' else '↓'} ({dir_desc})",
            "relation": {
                "id": id,
                "primary": {"id": primary_id, "name": primary_name},
                "secondary": {"id": secondary_id, "name": secondary_name},
                "direction": direction,
                "logic": logic
            }
        }
    except sqlite3.IntegrityError as e:
        conn.close()
        result = {"status": "error", "message": f"Relation '{id}' already exists"}
    except sqlite3.Error as e:
        conn.close()
        result = {"status": "error", "message": str(e)}
    
    return result


def get_relation(id: str) -> dict:
    """Get a relation by ID."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT r.*, e1.name as primary_name, e2.name as secondary_name
        FROM relations r
        JOIN entities e1 ON r.primary_id = e1.id
        JOIN entities e2 ON r.secondary_id = e2.id
        WHERE r.id = ?
    """, (id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        columns = ["id", "primary_id", "secondary_id", "direction", "strength", 
                   "logic", "lag", "confidence", "source", "tags", "notes", 
                   "created_at", "updated_at", "primary_name", "secondary_name"]
        relation = dict(zip(columns, row))
        if relation["tags"]:
            relation["tags"] = json.loads(relation["tags"])
        
        # Reorganize for clarity
        relation["primary"] = {"id": relation["primary_id"], "name": relation["primary_name"]}
        relation["secondary"] = {"id": relation["secondary_id"], "name": relation["secondary_name"]}
        relation["direction_desc"] = "正相关" if relation["direction"] == "up" else "负相关"
        del relation["primary_id"], relation["primary_name"]
        del relation["secondary_id"], relation["secondary_name"]
        
        return {"status": "success", "relation": relation}
    else:
        return {"status": "error", "message": f"Relation '{id}' not found"}


def list_relations(
    entity_id: str = None,
    direction: str = None,
    category: str = None,
    limit: int = 100
) -> dict:
    """List relations with optional filters."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    query = """
        SELECT r.id, r.primary_id, r.secondary_id, r.direction, r.strength, r.logic, r.lag,
               e1.name as primary_name, e1.category as primary_category,
               e2.name as secondary_name, e2.category as secondary_category
        FROM relations r
        JOIN entities e1 ON r.primary_id = e1.id
        JOIN entities e2 ON r.secondary_id = e2.id
    """
    
    params = []
    conditions = []
    
    if entity_id:
        conditions.append("(r.primary_id = ? OR r.secondary_id = ?)")
        params.extend([entity_id, entity_id])
    
    if direction:
        conditions.append("r.direction = ?")
        params.append(direction)
    
    if category:
        conditions.append("(e1.category = ? OR e2.category = ?)")
        params.extend([category, category])
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += f" LIMIT {limit}"
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    columns = ["id", "primary_id", "secondary_id", "direction", "strength", "logic", "lag",
               "primary_name", "primary_category", "secondary_name", "secondary_category"]
    
    relations = []
    for row in rows:
        rel = dict(zip(columns, row))
        rel["direction_desc"] = "正相关" if rel["direction"] == "up" else "负相关"
        rel["primary"] = {"id": rel["primary_id"], "name": rel["primary_name"], "category": rel["primary_category"]}
        rel["secondary"] = {"id": rel["secondary_id"], "name": rel["secondary_name"], "category": rel["secondary_category"]}
        for key in ["primary_id", "primary_name", "primary_category", "secondary_id", "secondary_name", "secondary_category"]:
            del rel[key]
        relations.append(rel)
    
    return {"status": "success", "count": len(relations), "relations": relations}


def update_relation(id: str, **kwargs) -> dict:
    """Update a relation. Only provided fields will be updated."""
    
    valid_fields = ["primary_direction", "secondary_direction", "relation_type", 
                    "strength", "logic", "mechanism", "lag", "confidence", 
                    "source", "tags", "notes"]
    updates = {k: v for k, v in kwargs.items() if k in valid_fields and v is not None}
    
    if not updates:
        return {"status": "error", "message": "No valid fields to update"}
    
    # Validate directions if provided
    valid_directions = ["up", "down", "stable"]
    if "primary_direction" in updates and updates["primary_direction"] not in valid_directions:
        return {"status": "error", "message": f"Invalid primary_direction. Must be one of: {valid_directions}"}
    if "secondary_direction" in updates and updates["secondary_direction"] not in valid_directions:
        return {"status": "error", "message": f"Invalid secondary_direction. Must be one of: {valid_directions}"}
    
    # Validate relation_type if provided
    valid_types = ["positive", "negative", "mixed", "conditional"]
    if "relation_type" in updates and updates["relation_type"] not in valid_types:
        return {"status": "error", "message": f"Invalid relation_type. Must be one of: {valid_types}"}
    
    # Handle JSON field
    if "tags" in updates and isinstance(updates["tags"], list):
        updates["tags"] = json.dumps(updates["tags"])
    
    updates["updated_at"] = datetime.now().isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    fields = ", ".join(f"{k} = ?" for k in updates.keys())
    values = list(updates.values()) + [id]
    
    cursor.execute(f"UPDATE relations SET {fields} WHERE id = ?", values)
    
    if cursor.rowcount > 0:
        conn.commit()
        conn.close()
        return {"status": "success", "message": f"Relation '{id}' updated", "fields_updated": list(updates.keys())}
    else:
        conn.close()
        return {"status": "error", "message": f"Relation '{id}' not found"}


def delete_relation(id: str) -> dict:
    """Delete a relation."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get relation info before delete
    cursor.execute("""
        SELECT r.primary_id, r.secondary_id, e1.name, e2.name
        FROM relations r
        JOIN entities e1 ON r.primary_id = e1.id
        JOIN entities e2 ON r.secondary_id = e2.id
        WHERE r.id = ?
    """, (id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return {"status": "error", "message": f"Relation '{id}' not found"}
    
    primary_id, secondary_id, primary_name, secondary_name = row
    
    cursor.execute("DELETE FROM relations WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    
    return {"status": "success", "message": f"Relation deleted: {primary_name} ↔ {secondary_name}"}


def find_relations_chain(entity_id: str, max_depth: int = 3) -> dict:
    """Find multi-hop relations starting from an entity."""
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # BFS to find chains
    chains = []
    visited = set()
    queue = [(entity_id, [])]
    
    while queue and len(chains) < 50:
        current_id, path = queue.pop(0)
        
        if len(path) >= max_depth:
            continue
        
        if current_id in visited:
            continue
        
        visited.add(current_id)
        
        # Find relations involving this entity
        cursor.execute("""
            SELECT r.id, r.primary_id, r.secondary_id, r.primary_direction, r.secondary_direction,
                   r.relation_type, r.logic, e1.name, e2.name
            FROM relations r
            JOIN entities e1 ON r.primary_id = e1.id
            JOIN entities e2 ON r.secondary_id = e2.id
            WHERE r.primary_id = ? OR r.secondary_id = ?
        """, (current_id, current_id))
        
        for row in cursor.fetchall():
            rel_id, p_id, s_id, p_dir, s_dir, rel_type, logic, p_name, s_name = row
            
            # Determine next entity in chain
            if p_id == current_id:
                next_id = s_id
                next_name = s_name
                step = {"from": p_name, "direction": p_dir, "relation": rel_type, 
                        "to": next_name, "to_direction": s_dir, "logic": logic}
            else:
                next_id = p_id
                next_name = p_name
                step = {"from": s_name, "direction": s_dir, "relation": rel_type,
                        "to": next_name, "to_direction": p_dir, "logic": logic}
            
            new_path = path + [step]
            chains.append(new_path)
            
            if next_id not in visited:
                queue.append((next_id, new_path))
    
    conn.close()
    
    # Filter chains to show unique ones
    unique_chains = []
    seen = set()
    for chain in chains:
        key = tuple((s["from"], s["to"]) for s in chain)
        if key not in seen:
            seen.add(key)
            unique_chains.append(chain)
    
    return {"status": "success", "entity_id": entity_id, "chains": unique_chains[:20]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Manage market correlations")
    subparsers = parser.add_subparsers(dest="command", help="Command")
    
    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new relation")
    add_parser.add_argument("--id", help="Relation ID (auto-generated if not provided)")
    add_parser.add_argument("--primary", required=True, help="Primary entity ID")
    add_parser.add_argument("--primary-dir", required=True, choices=["up", "down", "stable"], help="Primary direction")
    add_parser.add_argument("--secondary", required=True, help="Secondary entity ID")
    add_parser.add_argument("--secondary-dir", required=True, choices=["up", "down", "stable"], help="Secondary direction")
    add_parser.add_argument("--type", required=True, choices=["positive", "negative", "mixed", "conditional"], help="Relation type")
    add_parser.add_argument("--logic", required=True, help="Logic description")
    add_parser.add_argument("--strength", choices=["strong", "medium", "weak"], help="Relation strength")
    add_parser.add_argument("--mechanism", help="Detailed mechanism")
    add_parser.add_argument("--lag", choices=["immediate", "short-term", "long-term"], help="Time lag")
    add_parser.add_argument("--confidence", choices=["high", "medium", "low"], help="Confidence level")
    add_parser.add_argument("--source", help="Source reference")
    add_parser.add_argument("--tags", help="Tags (comma-separated)")
    add_parser.add_argument("--notes", help="Additional notes")
    
    # Get command
    get_parser = subparsers.add_parser("get", help="Get a relation")
    get_parser.add_argument("--id", required=True, help="Relation ID")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List relations")
    list_parser.add_argument("--entity", help="Filter by entity ID")
    list_parser.add_argument("--type", choices=["positive", "negative", "mixed", "conditional"], help="Filter by relation type")
    list_parser.add_argument("--category", help="Filter by entity category")
    list_parser.add_argument("--limit", type=int, default=100, help="Limit results")
    
    # Update command
    update_parser = subparsers.add_parser("update", help="Update a relation")
    update_parser.add_argument("--id", required=True, help="Relation ID")
    update_parser.add_argument("--primary-dir", choices=["up", "down", "stable"], help="New primary direction")
    update_parser.add_argument("--secondary-dir", choices=["up", "down", "stable"], help="New secondary direction")
    update_parser.add_argument("--type", choices=["positive", "negative", "mixed", "conditional"], help="New relation type")
    update_parser.add_argument("--strength", choices=["strong", "medium", "weak"], help="New strength")
    update_parser.add_argument("--logic", help="New logic")
    update_parser.add_argument("--mechanism", help="New mechanism")
    update_parser.add_argument("--lag", choices=["immediate", "short-term", "long-term"], help="New time lag")
    update_parser.add_argument("--confidence", choices=["high", "medium", "low"], help="New confidence")
    update_parser.add_argument("--source", help="New source")
    update_parser.add_argument("--notes", help="New notes")
    
    # Delete command
    delete_parser = subparsers.add_parser("delete", help="Delete a relation")
    delete_parser.add_argument("--id", required=True, help="Relation ID")
    
    # Chain command
    chain_parser = subparsers.add_parser("chain", help="Find relation chains")
    chain_parser.add_argument("--entity", required=True, help="Starting entity ID")
    chain_parser.add_argument("--depth", type=int, default=3, help="Maximum chain depth")
    
    args = parser.parse_args()
    
    if args.command == "add":
        tags = args.tags.split(",") if args.tags else None
        result = add_relation(
            args.primary, args.primary_dir, args.secondary, args.secondary_dir,
            args.type, args.logic, args.strength, args.mechanism, args.lag,
            args.confidence, args.source, tags, args.notes, args.id
        )
    elif args.command == "get":
        result = get_relation(args.id)
    elif args.command == "list":
        result = list_relations(args.entity, args.type, args.category, args.limit)
    elif args.command == "update":
        update_kwargs = {}
        if args.primary_dir: update_kwargs["primary_direction"] = args.primary_dir
        if args.secondary_dir: update_kwargs["secondary_direction"] = args.secondary_dir
        if args.type: update_kwargs["relation_type"] = args.type
        if args.strength: update_kwargs["strength"] = args.strength
        if args.logic: update_kwargs["logic"] = args.logic
        if args.mechanism: update_kwargs["mechanism"] = args.mechanism
        if args.lag: update_kwargs["lag"] = args.lag
        if args.confidence: update_kwargs["confidence"] = args.confidence
        if args.source: update_kwargs["source"] = args.source
        if args.notes: update_kwargs["notes"] = args.notes
        result = update_relation(args.id, **update_kwargs)
    elif args.command == "delete":
        result = delete_relation(args.id)
    elif args.command == "chain":
        result = find_relations_chain(args.entity, args.depth)
    else:
        result = {"status": "error", "message": "No command specified"}
    
    print(json.dumps(result, ensure_ascii=False, indent=2))