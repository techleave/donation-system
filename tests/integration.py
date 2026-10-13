"""Real JVM + HTTP + SQLite tests; never connects to production or creates real donor data."""
import concurrent.futures
import hashlib
import http.cookiejar
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
import uuid

ROOT = Path(__file__).resolve().parents[1]
PASSWORD = "test-only-admin-password-123"


class SystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="donate-java-test-")
        # Seed the exact previous Node database format, including scrypt credentials.
        db = sqlite3.connect(Path(cls.temp.name) / "donate.sqlite")
        db.execute("CREATE TABLE runtime_migrations (name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)")
        for migration in sorted((ROOT / "drizzle").glob("*.sql")):
            db.executescript(migration.read_text())
            db.execute("INSERT INTO runtime_migrations VALUES (?,?)", (migration.name, "2026-10-12T00:00:00Z"))
        db.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY,email TEXT NOT NULL UNIQUE,password_hash TEXT NOT NULL,role TEXT NOT NULL,donor_id TEXT UNIQUE REFERENCES donors(id) ON DELETE CASCADE)")
        salt = "0123456789abcdef0123456789abcdef"
        digest = hashlib.scrypt(PASSWORD.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64, maxmem=64*1024*1024).hex()
        db.execute("INSERT INTO accounts VALUES (?,?,?,?,NULL)", (str(uuid.uuid4()), "admin@example.com", salt+":"+digest, "admin"))
        db.commit(); db.close()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0)); cls.port = s.getsockname()[1]
        cls.base = f"http://localhost:{cls.port}"
        cls.env = dict(os.environ, PORT=str(cls.port), PUBLIC_URL=cls.base, DATA_DIR=cls.temp.name, ADMIN_EMAIL="admin@example.com", INITIAL_ADMIN_PASSWORD="different-seed-must-not-reset-existing")
        cls.start()

    @classmethod
    def start(cls):
        cls.log = open(Path(cls.temp.name)/"server.log", "a")
        cls.process = subprocess.Popen(["java", "-jar", str(ROOT/"target/donation-system.jar")], env=cls.env, stdout=cls.log, stderr=cls.log)
        for _ in range(120):
            if cls.process.poll() is not None:
                raise RuntimeError(Path(cls.temp.name, "server.log").read_text())
            try:
                urllib.request.urlopen(cls.base+"/health", timeout=1).close(); return
            except (OSError, urllib.error.URLError):
                time.sleep(.1)
        raise RuntimeError("JVM did not become healthy")

    @classmethod
    def stop(cls):
        cls.process.terminate(); cls.process.wait(timeout=10); cls.log.close()

    @classmethod
    def tearDownClass(cls):
        cls.stop(); cls.temp.cleanup()

    def client(self):
        return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, client, path, method="GET", body=None, headers=None):
        h = {"Origin": self.base}
        if headers: h.update(headers)
        if isinstance(body, bytes): payload = body
        elif body is not None: payload = json.dumps(body).encode(); h["Content-Type"] = "application/json"
        else: payload = None
        try: r = client.open(urllib.request.Request(self.base+path, data=payload, method=method, headers=h), timeout=10)
        except urllib.error.HTTPError as err: r = err
        raw = r.read(); content_type = r.headers.get("Content-Type", "")
        return r.status, json.loads(raw) if "application/json" in content_type else raw

    def upload(self, client, path, fields, image, name="image.png"):
        boundary = "test"+uuid.uuid4().hex
        chunks = []
        for key, value in fields.items():
            chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
        chunks.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\nContent-Type: image/png\r\n\r\n'.encode()+image+b"\r\n")
        chunks.append(f'--{boundary}--\r\n'.encode())
        return self.call(client, path, "POST", b"".join(chunks), {"Content-Type": "multipart/form-data; boundary="+boundary})

    def test_01_workflows(self):
        admin = self.client(); alice = self.client(); bob = self.client(); anon = self.client()
        self.assertEqual(self.call(anon, "/health")[1]["backend"], "java")
        self.assertEqual(self.call(anon, "/api/donors", headers={"oai-authenticated-user-email": "admin@example.com", "oai-authenticated-user-id": "spoof"})[0], 403)
        self.assertEqual(self.call(admin, "/api/auth/login", "POST", {"email": "admin@example.com", "password": "wrong"})[0], 401)
        self.assertEqual(self.call(admin, "/api/auth/login", "POST", {"email": "admin@example.com", "password": PASSWORD})[0], 200)
        self.assertEqual(self.call(admin, "/admin")[0], 200)
        self.assertEqual(self.call(admin, "/api/auth/login", "POST", {"email": "admin@example.com", "password": PASSWORD}, {"Origin": "https://evil.example"})[0], 403)
        donor = {"prefix": "Ms.", "englishName": "Alice Example", "chineseName": "陳小明", "phone": "1234", "email": "alice@example.com"}
        status, data = self.call(admin, "/api/donors", "POST", donor); self.assertEqual(status, 201); d = data["donor"]
        self.assertEqual(self.call(admin, "/api/donors", "POST", donor)[0], 409)
        credentials = self.call(admin, "/api/accounts", "POST", {"donorId": d["id"]})[1]
        self.assertEqual(self.call(alice, "/api/auth/login", "POST", credentials)[0], 200)
        self.assertEqual(self.call(alice, "/admin")[0], 403)
        self.assertEqual(self.call(alice, "/api/donors")[0], 403)
        self.assertEqual(self.call(alice, "/api/profile")[1]["donor"]["englishName"], donor["englishName"])
        op = {"donorId": d["id"], "entryId": str(uuid.uuid4()), "amount": 3000}
        self.assertEqual(self.call(admin, "/api/donors/points", "POST", op)[1]["donor"]["demoPoints"], 3000)
        self.assertEqual(self.call(admin, "/api/donors/points", "POST", op)[1]["donor"]["demoPoints"], 3000)
        tree = {"requestId": str(uuid.uuid4()), "category": "tree", "fields": {"leaves": "2"}, "name": "spoof", "email": "spoof@example.com"}
        status, data = self.call(alice, "/api/requests", "POST", tree); self.assertEqual(status, 201); self.assertEqual(data["donor"]["demoPoints"], 1000)
        self.assertEqual(self.call(alice, "/api/requests", "POST", tree)[1]["donor"]["demoPoints"], 1000)
        self.assertEqual(self.call(alice, "/api/requests", "POST", dict(tree, requestId=str(uuid.uuid4())))[0], 400)
        self.assertEqual(self.call(alice, "/api/requests")[1]["requests"][0]["id"], tree["requestId"])
        request = self.call(admin, "/api/requests")[1]["requests"][0]
        self.assertEqual(request["email"], "alice@example.com")
        self.assertEqual(self.call(admin, "/api/requests", "PATCH", {"id": tree["requestId"], "status": "complete"})[0], 200)
        self.assertEqual(self.call(alice, "/api/requests")[1]["requests"][0]["status"], "complete")
        csv = 'Prefix,English Full Name,Chinese Full Name,Phone,Email\nMr.,"Bob, Example",,1234,bob@example.com\n'
        self.assertEqual(self.call(admin, "/api/donors/import", "POST", {"csv": csv, "action": "preview"})[1]["added"], 1)
        self.assertEqual(self.call(admin, "/api/donors/import", "POST", {"csv": csv, "action": "import"})[1]["added"], 1)
        bd = next(x for x in self.call(admin, "/api/donors")[1]["donors"] if x["email"] == "bob@example.com")
        bc = self.call(admin, "/api/accounts", "POST", {"donorId": bd["id"]})[1]
        self.call(bob, "/api/auth/login", "POST", bc)
        self.assertEqual(self.call(bob, "/api/requests")[1]["requests"], [])
        self.assertEqual(self.call(bob, "/api/donors/points?id="+d["id"])[0], 403)
        png = bytes([137, 80, 78, 71, 13, 10, 26, 10])+b"test image binary\x00\xff"
        d = self.call(admin, "/api/donors?id="+d["id"])[1]["donor"]
        status, data = self.upload(admin, "/api/donors/photo", {"id": d["id"], "revision": d["revision"]}, png)
        self.assertEqual(status, 200); d = data["donor"]
        self.assertEqual(self.call(alice, d["photoUrl"])[1], png)
        self.assertEqual(self.call(bob, d["photoUrl"])[0], 403)
        self.assertEqual(self.call(anon, d["photoUrl"])[0], 403)
        self.assertEqual(self.upload(admin, "/api/donors/photo", {"id": d["id"], "revision": d["revision"]-1}, png)[0], 409)
        status, cover = self.upload(admin, "/api/covers", {}, png); self.assertEqual(status, 201)
        self.assertEqual(self.call(anon, cover["url"])[1], png)
        cfg = self.call(admin, "/api/config?admin=1")[1]
        cfg["draft"]["copy"]["en"]["hello"] = "Welcome test"
        save = {"config": cfg["draft"], "revision": cfg["revision"], "action": "draft"}
        self.assertEqual(self.call(admin, "/api/config", "POST", save)[0], 200)
        self.assertNotEqual(self.call(anon, "/api/config")[1]["config"]["copy"]["en"]["hello"], "Welcome test")
        self.assertEqual(self.call(admin, "/api/config", "POST", save)[0], 409)
        save.update(revision=cfg["revision"]+1, action="publish")
        self.assertEqual(self.call(admin, "/api/config", "POST", save)[0], 200)
        self.assertEqual(self.call(anon, "/api/config")[1]["config"]["copy"]["en"]["hello"], "Welcome test")
        # Concurrent retries of one operation must debit exactly once.
        retry = {"requestId": str(uuid.uuid4()), "category": "tree", "fields": {"leaves": "1"}}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            responses = list(pool.map(lambda _: self.call(alice, "/api/requests", "POST", retry), range(4)))
        self.assertTrue(all(r[0] in (200, 201) for r in responses))
        self.assertEqual(self.call(alice, "/api/profile")[1]["donor"]["demoPoints"], 0)
        d = self.call(admin, "/api/donors?id="+d["id"])[1]["donor"]
        self.assertEqual(self.call(admin, "/api/donors", "PATCH", dict(d, email="alice-new@example.com"))[0], 200)
        fresh = self.client(); self.assertEqual(self.call(fresh, "/api/auth/login", "POST", dict(credentials, email="alice-new@example.com"))[0], 200)
        self.assertEqual(len(self.call(fresh, "/api/requests")[1]["requests"]), 2)
        self.assertEqual(self.call(admin, "/api/accounts", "POST", {"donorId": d["id"]})[0], 200)
        self.assertEqual(self.call(fresh, "/api/profile")[0], 401)
        self.assertEqual(self.call(anon, "/assets/donor-footer-banner-v2.png")[0], 200)
        # The website's history now retrieves records from the server.
        self.assertIn(b"fetch('/api/requests?offset='", self.call(anon, "/")[1])

    def test_02_restart_preserves_data(self):
        self.stop(); self.start()
        admin = self.client()
        self.assertEqual(self.call(admin, "/api/auth/login", "POST", {"email": "admin@example.com", "password": PASSWORD})[0], 200)
        self.assertEqual(len(self.call(admin, "/api/donors")[1]["donors"]), 2)
        self.assertEqual(len(self.call(admin, "/api/requests")[1]["requests"]), 2)
        self.assertEqual(self.call(admin, "/api/config")[1]["config"]["copy"]["en"]["hello"], "Welcome test")
        d = next(d for d in self.call(admin, "/api/donors")[1]["donors"] if d["email"] == "alice-new@example.com")
        self.assertEqual(d["demoPoints"], 0)
        self.assertEqual(self.call(admin, d["photoUrl"])[0], 200)
        entries = self.call(admin, "/api/donors/points?id="+d["id"])[1]["entries"]
        self.assertEqual(len(entries), 3)
        self.assertEqual(self.call(admin, "/api/donors", "DELETE", {"id": d["id"], "revision": d["revision"]})[0], 200)
        self.assertEqual(self.call(admin, "/api/donors?id="+d["id"])[0], 404)
        # Fulfilment records are retained after profile deletion, as in the original.
        self.assertEqual(len(self.call(admin, "/api/requests")[1]["requests"]), 2)

    def test_03_original_site_import(self):
        admin = self.client()
        self.call(admin, "/api/auth/login", "POST", {"email": "admin@example.com", "password": PASSWORD})
        donor_id, entry_id = str(uuid.uuid4()), str(uuid.uuid4())
        donor = dict(id=donor_id, prefix="Ms", english_name="Imported Donor", chinese_name="測試", phone="1234", email="imported@example.com", photo_key=None, user_id="old-chatgpt-user-id", revision=2, created_at="2026-10-11T12:00:00Z", updated_at="2026-10-11T13:00:00Z", points=2500)
        entry = dict(id=entry_id, donor_id=donor_id, amount=2500, kind="add", created_at="2026-10-11T13:00:00Z", applied=1)
        payload = dict(sourceProjectId="appgprj_6abb452ba1388191badab398f5fb3b58", tables=dict(donors=[donor], donor_point_entries=[entry], reward_requests=[]))
        path = "/api/admin/import-site-data"
        self.assertEqual(self.call(self.client(), path, "POST", payload)[0], 403)
        self.assertEqual(self.call(admin, path, "POST", payload, {"Origin": "https://evil.example"})[0], 403)
        status, result = self.call(admin, path, "POST", payload)
        self.assertEqual(status, 200); self.assertFalse(result["alreadyImported"])
        self.assertTrue(self.call(admin, path, "POST", payload)[1]["alreadyImported"])
        profile = self.call(admin, "/api/donors?id="+donor_id)[1]["donor"]
        self.assertEqual(profile["demoPoints"], 2500)
        self.assertEqual(profile["updatedAt"], donor["updated_at"])
        history = self.call(admin, "/api/donors/points?id="+donor_id)[1]["entries"]
        self.assertEqual(history[0]["id"], entry_id)
        self.assertEqual(history[0]["created_at"], entry["created_at"])
        payload["tables"]["donors"][0]["points"] = 9000
        self.assertEqual(self.call(admin, path, "POST", payload)[0], 409)
        self.assertEqual(self.call(admin, "/api/donors?id="+donor_id)[1]["donor"]["demoPoints"], 2500)
        db = sqlite3.connect(Path(self.temp.name)/"donate.sqlite")
        self.assertIsNone(db.execute("SELECT user_id FROM donors WHERE id=?", (donor_id,)).fetchone()[0])
        db.close()
        self.assertEqual(len(list(Path(self.temp.name).glob("before-sites-import-*.sqlite"))), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
