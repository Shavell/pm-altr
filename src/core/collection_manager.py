"""Collection manager — SQLite-backed collections with requests."""
from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


DB_DIR = Path.home() / ".pm-altr"
DB_PATH = DB_DIR / "history.db"


@dataclass
class CollectionRequest:
    id: Optional[int] = None
    collection_id: Optional[int] = None
    name: str = ""
    method: str = "GET"
    url: str = ""
    headers: str = "{}"
    params: str = "{}"
    body: str = ""
    body_type: str = "none"
    auth_type: str = "none"
    auth_username: str = ""
    auth_password: str = ""
    auth_token: str = ""
    sort_order: int = 0


@dataclass
class Collection:
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: str = ""
    requests: List[CollectionRequest] = field(default_factory=list)


class CollectionManager:
    def __init__(self):
        DB_DIR.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS collections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS collection_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_id INTEGER NOT NULL,
                name TEXT DEFAULT '',
                method TEXT DEFAULT 'GET',
                url TEXT DEFAULT '',
                headers TEXT DEFAULT '{}',
                params TEXT DEFAULT '{}',
                body TEXT DEFAULT '',
                body_type TEXT DEFAULT 'none',
                auth_type TEXT DEFAULT 'none',
                auth_username TEXT DEFAULT '',
                auth_password TEXT DEFAULT '',
                auth_token TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
            )
        """)
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.commit()

    # --- Collections ---

    def create_collection(self, name: str, description: str = "") -> int:
        cur = self._conn.execute(
            "INSERT INTO collections (name, description, created_at) VALUES (?, ?, ?)",
            (name, description, datetime.utcnow().isoformat()),
        )
        self._conn.commit()
        return cur.lastrowid

    def get_collections(self) -> List[Collection]:
        rows = self._conn.execute(
            "SELECT * FROM collections ORDER BY name"
        ).fetchall()
        return [Collection(**{k: r[k] for k in ("id", "name", "description", "created_at")}) for r in rows]

    def rename_collection(self, cid: int, name: str):
        self._conn.execute("UPDATE collections SET name=? WHERE id=?", (name, cid))
        self._conn.commit()

    def delete_collection(self, cid: int):
        self._conn.execute("DELETE FROM collection_requests WHERE collection_id=?", (cid,))
        self._conn.execute("DELETE FROM collections WHERE id=?", (cid,))
        self._conn.commit()

    # --- Requests in a collection ---

    def add_request(self, cid: int, req: CollectionRequest) -> int:
        cur = self._conn.execute("""
            INSERT INTO collection_requests
                (collection_id, name, method, url, headers, params, body, body_type,
                 auth_type, auth_username, auth_password, auth_token, sort_order)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            cid, req.name, req.method, req.url, req.headers, req.params,
            req.body, req.body_type, req.auth_type, req.auth_username,
            req.auth_password, req.auth_token, req.sort_order,
        ))
        self._conn.commit()
        return cur.lastrowid

    def get_requests(self, cid: int) -> List[CollectionRequest]:
        rows = self._conn.execute(
            "SELECT * FROM collection_requests WHERE collection_id=? ORDER BY sort_order, id",
            (cid,),
        ).fetchall()
        cols = [
            "id", "collection_id", "name", "method", "url", "headers", "params",
            "body", "body_type", "auth_type", "auth_username", "auth_password",
            "auth_token", "sort_order",
        ]
        return [CollectionRequest(**{c: r[c] for c in cols}) for r in rows]

    def delete_request(self, req_id: int):
        self._conn.execute("DELETE FROM collection_requests WHERE id=?", (req_id,))
        self._conn.commit()

    # --- Export / Import as JSON ---

    def export_collection(self, cid: int) -> dict:
        rows = self._conn.execute("SELECT * FROM collections WHERE id=?", (cid,)).fetchall()
        if not rows:
            return {}
        c = rows[0]
        reqs = self.get_requests(cid)
        return {
            "name": c["name"],
            "description": c["description"],
            "requests": [
                {
                    "name": r.name, "method": r.method, "url": r.url,
                    "headers": json.loads(r.headers),
                    "params": json.loads(r.params),
                    "body": r.body, "body_type": r.body_type,
                    "auth_type": r.auth_type, "auth_username": r.auth_username,
                    "auth_token": r.auth_token,
                }
                for r in reqs
            ],
        }

    def import_collection(self, data: dict) -> int:
        cid = self.create_collection(data.get("name", "Imported"), data.get("description", ""))
        for i, r in enumerate(data.get("requests", [])):
            req = CollectionRequest(
                name=r.get("name", ""),
                method=r.get("method", "GET"),
                url=r.get("url", ""),
                headers=json.dumps(r.get("headers", {})),
                params=json.dumps(r.get("params", {})),
                body=r.get("body", ""),
                body_type=r.get("body_type", "none"),
                auth_type=r.get("auth_type", "none"),
                auth_username=r.get("auth_username", ""),
                auth_token=r.get("auth_token", ""),
                sort_order=i,
            )
            self.add_request(cid, req)
        return cid

    # --- OpenAPI Import ---

    def import_openapi(self, spec: dict) -> int:
        """Import an OpenAPI 3.x spec as a collection."""
        info = spec.get("info", {})
        title = info.get("title", "OpenAPI Import")
        desc = info.get("description", "")
        cid = self.create_collection(title, desc)

        servers = spec.get("servers", [])
        base_url = servers[0].get("url", "") if servers else ""

        idx = 0
        for path, methods in spec.get("paths", {}).items():
            for method, details in methods.items():
                if method.lower() in ("get", "post", "put", "patch", "delete", "head", "options"):
                    op_id = details.get("operationId", "")
                    summary = details.get("summary", "")
                    name = op_id or summary or f"{method.upper()} {path}"

                    # Build params from path parameters
                    params = {}
                    headers = {}
                    for param in details.get("parameters", []):
                        p_in = param.get("in", "")
                        p_name = param.get("name", "")
                        p_example = param.get("example", param.get("schema", {}).get("default", ""))
                        if p_in == "query":
                            params[p_name] = str(p_example) if p_example else ""
                        elif p_in == "header":
                            headers[p_name] = str(p_example) if p_example else ""

                    # Detect body
                    body = ""
                    body_type = "none"
                    req_body = details.get("requestBody", {})
                    content = req_body.get("content", {})
                    if "application/json" in content:
                        body_type = "json"
                        schema = content["application/json"].get("schema", {})
                        example = content["application/json"].get("example")
                        if example:
                            body = json.dumps(example, indent=2)
                        elif schema:
                            body = json.dumps(self._schema_example(schema), indent=2)
                    elif "application/x-www-form-urlencoded" in content:
                        body_type = "x-www-form-urlencoded"
                    elif "multipart/form-data" in content:
                        body_type = "form-data"

                    # Detect auth
                    auth_type = "none"
                    security = details.get("security", spec.get("security", []))
                    if security:
                        schemes = spec.get("components", {}).get("securitySchemes", {})
                        for sec_item in security:
                            for scheme_name in sec_item:
                                scheme = schemes.get(scheme_name, {})
                                if scheme.get("type") == "http":
                                    if scheme.get("scheme", "").lower() == "bearer":
                                        auth_type = "bearer"
                                    elif scheme.get("scheme", "").lower() == "basic":
                                        auth_type = "basic"

                    url = base_url.rstrip("/") + path
                    req = CollectionRequest(
                        name=name,
                        method=method.upper(),
                        url=url,
                        headers=json.dumps(headers),
                        params=json.dumps(params),
                        body=body,
                        body_type=body_type,
                        auth_type=auth_type,
                        sort_order=idx,
                    )
                    self.add_request(cid, req)
                    idx += 1
        return cid

    @staticmethod
    def _schema_example(schema: dict) -> dict | list | str:
        """Generate a minimal example from a JSON Schema."""
        if "example" in schema:
            return schema["example"]
        s_type = schema.get("type", "object")
        if s_type == "object":
            props = schema.get("properties", {})
            return {k: CollectionManager._schema_example(v) for k, v in props.items()}
        elif s_type == "array":
            items = schema.get("items", {})
            return [CollectionManager._schema_example(items)]
        elif s_type == "string":
            return schema.get("default", "string")
        elif s_type == "integer":
            return schema.get("default", 0)
        elif s_type == "number":
            return schema.get("default", 0.0)
        elif s_type == "boolean":
            return schema.get("default", False)
        return ""
