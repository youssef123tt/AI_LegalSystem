# Database Migrations Explained (From Scratch)

## What You Already Know: "Just Create Tables"

You've probably done something like this before — open a database tool, write SQL, hit run:

```sql
CREATE TABLE users (
    id   INTEGER PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(200)
);
```

The table appears. Done. ✅

**This works fine for learning and small projects.** But here's where it breaks down in real projects:

---

## The 3 Problems With "Just Create Tables"

### Problem 1: "What did I change last week?"

Imagine you add a `phone` column on your machine:

```sql
ALTER TABLE users ADD COLUMN phone VARCHAR(20);
```

Next week you forget you did it. Your teammate's database doesn't have that column. Your production database doesn't either. **Nobody can reproduce your database because there's no record of what changed.**

### Problem 2: "My teammate has a different schema"

You added `phone`. Your teammate added `address`. Now your databases look different. When you merge code, whose database is correct? There's no way to know.

### Problem 3: "How do I set up a fresh database?"

A new developer joins. They need a database that matches the current code. But the schema evolved over 6 months through dozens of manual `ALTER TABLE` statements that nobody wrote down. They have to ask you, and you have to remember (you won't).

---

## The Solution: Migration Files

A **migration** is a small Python file that says:

> "Here is a change to make to the database, and here is how to undo it."

```
migrations/
  0001_create_users.py          ← first migration
  0002_add_phone_to_users.py    ← second migration
  0003_create_documents.py      ← third migration
```

Each file has two functions:

```python
# 0002_add_phone_to_users.py

def upgrade():
    """Apply this change (go forward)"""
    op.add_column('users', sa.Column('phone', sa.String(20)))

def downgrade():
    """Undo this change (go backward)"""
    op.drop_column('users', 'phone')
```

### How it solves the 3 problems:

| Problem | Solution |
|---------|----------|
| What changed? | Each migration file _is_ the record. You can read them like a changelog. |
| Teammate has different schema? | Both of you run the same migrations. The schema is always in sync. |
| Fresh database setup? | Run all migrations from #1 forward. Done. |

---

## Where Alembic Fits In

**Alembic** is the tool that manages these migration files for SQLAlchemy (our ORM).

### What Alembic Does

```
┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│  Your Python │         │   Alembic    │         │   Postgres   │
│  ORM Models  │ ──────► │  (compares)  │ ──────► │   Database   │
│  (models.py) │         │              │         │   (tables)   │
└──────────────┘         └──────────────┘         └──────────────┘
```

1. You write Python classes in `models.py` (describing what tables _should_ look like)
2. Alembic **compares** your models to the actual database
3. Alembic **generates** a migration file with the differences
4. You **run** the migration, and the database updates

### Alembic's Key Commands

| Command | What it does |
|---------|-------------|
| `alembic revision --autogenerate -m "description"` | Looks at models.py vs database, generates a migration file with the differences |
| `alembic upgrade head` | Runs ALL pending migrations (brings database up to date) |
| `alembic downgrade -1` | Undoes the last migration (rolls back one step) |
| `alembic current` | Shows which migration the database is currently at |
| `alembic history` | Shows all migration files in order |

### How does Alembic know what's already applied?

Alembic creates a special table in your database called `alembic_version`. It has one row with the ID of the latest migration that was applied:

```
alembic_version
┌──────────────────────┐
│ version_num          │
├──────────────────────┤
│ 0002_add_phone       │  ← "I'm at migration #2"
└──────────────────────┘
```

When you run `alembic upgrade head`, it checks this table, sees it's at #2, and only runs #3 and onwards.

---

## Where SQLAlchemy ORM Fits In

**SQLAlchemy ORM** lets you define tables as Python classes instead of writing SQL:

### Without ORM (raw SQL):
```sql
CREATE TABLE documents (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title      VARCHAR(500) NOT NULL,
    year       INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### With SQLAlchemy ORM (Python):
```python
class Document(Base):
    __tablename__ = "documents"

    id         = Column(UUID, primary_key=True, default=uuid4)
    title      = Column(String(500), nullable=False)
    year       = Column(Integer)
    created_at = Column(DateTime, default=func.now())
```

**Both produce the exact same table.** The ORM version is just Python, so:
- Your IDE can autocomplete column names
- You can query with Python: `session.query(Document).filter(Document.year == 2024)`
- Alembic can read these classes to auto-generate migrations

---

## The Full Workflow for Milestone 2

Here's exactly what happens, step by step:

### Step 1: We write `models.py`

```python
# apps/shared/models.py

class Document(Base):
    __tablename__ = "documents"
    id           = Column(UUID, primary_key=True)
    title        = Column(String(500))
    jurisdiction = Column(String(100))
    year         = Column(Integer)
    law_type     = Column(String(50))
    file_path    = Column(String(1000))
    created_at   = Column(DateTime)

class IngestJob(Base):
    __tablename__ = "ingest_jobs"
    id           = Column(UUID, primary_key=True)
    document_id  = Column(UUID, ForeignKey("documents.id"))
    status       = Column(String(20))       # queued / processing / complete / failed
    error_message= Column(Text)
    created_at   = Column(DateTime)
    updated_at   = Column(DateTime)
```

At this point, these are just Python classes. **No tables exist yet.**

### Step 2: We generate a migration

```
alembic revision --autogenerate -m "create documents and ingest_jobs"
```

Alembic sees: "models.py says `documents` and `ingest_jobs` should exist, but the database has neither." It generates:

```python
# 0001_create_documents_and_ingest_jobs.py

def upgrade():
    op.create_table('documents', ...)
    op.create_table('ingest_jobs', ...)

def downgrade():
    op.drop_table('ingest_jobs')
    op.drop_table('documents')
```

### Step 3: We run the migration

```
alembic upgrade head
```

Now Postgres actually has the tables. ✅

### Step 4: In Docker, this runs automatically

In our [docker-compose.yml](file:///d:/AI_LegalSystem/infra/docker-compose.yml), we add a `migrate` service that runs `alembic upgrade head` before the API starts. So every time you run `docker compose up`, the database is automatically up to date.

```yaml
migrate:
  command: alembic upgrade head    # ← runs once, creates tables, exits
  depends_on:
    postgres: { condition: service_healthy }

api:
  depends_on:
    migrate: { condition: service_completed_successfully }  # ← waits for migration
```

**You never manually create tables.** Just define models in Python → Alembic handles the rest.

---

## Visual: The Complete Upload Flow

```
YOU run: docker compose up --build

  ┌─────────┐     ┌──────────┐     ┌──────────┐
  │ Postgres │────►│ migrate  │     │          │
  │ (starts) │     │ service  │     │          │
  └──────────┘     │          │     │          │
                   │ runs:    │     │          │
                   │ alembic  │     │          │
                   │ upgrade  │     │          │
                   │ head     │     │          │
                   │          │     │          │
                   │ creates: │     │          │
                   │ documents│     │          │
                   │ ingest_  │     │          │
                   │ jobs     │     │          │
                   └────┬─────┘     │          │
                        │ done ✅   │          │
                        ▼           │          │
                   ┌──────────┐     │  Worker  │
                   │   API    │     │ (Celery) │
                   │ (starts) │     │ (starts) │
                   └──────────┘     └──────────┘

THEN you upload a file:

  Browser/curl                API                    Postgres          Redis           Worker
       │                       │                        │                │                │
       │── POST /upload ──────►│                        │                │                │
       │   (file + metadata)   │── save file to disk    │                │                │
       │                       │── INSERT document ────►│                │                │
       │                       │── INSERT ingest_job ──►│ (status=queued)│                │
       │                       │── send task ──────────────────────────►│                │
       │◄── {doc_id, job_id} ──│                        │                │                │
       │                       │                        │                │── pick up task─►│
       │                       │                        │◄── UPDATE job ─────────────────│
       │                       │                        │  (status=processing)           │
       │                       │                        │     ... work ...               │
       │                       │                        │◄── UPDATE job ─────────────────│
       │                       │                        │  (status=complete)             │
       │                       │                        │                │                │
       │── GET /jobs/{id} ────►│── SELECT job ─────────►│                │                │
       │◄── {status:complete}──│◄──────────────────────│                │                │
```

---

## TL;DR Comparison

| Approach | How tables are created | How changes are tracked | How new devs set up |
|----------|----------------------|------------------------|-------------------|
| **Manual SQL** | You write `CREATE TABLE` by hand | Not tracked (you hope you remember) | "Ask the senior dev" |
| **ORM + Migrations** | You write Python classes, run `alembic upgrade` | Every change is a versioned file in Git | Run `alembic upgrade head` — done |
