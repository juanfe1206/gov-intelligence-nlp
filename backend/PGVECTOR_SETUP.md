# pgvector Extension Setup Guide

The `gov-intelligence-nlp` project uses [pgvector](https://github.com/pgvector/pgvector) for efficient vector storage and similarity search in PostgreSQL.

## Installation Steps

### 1. Install pgvector on PostgreSQL

pgvector is a C extension that must be installed on the PostgreSQL server itself, not just in Python.

#### On Linux (Ubuntu/Debian):
```bash
# Install build dependencies
sudo apt-get install postgresql-server-dev-15  # or your PostgreSQL version

# Clone pgvector repository
cd /tmp
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

#### On macOS (with Homebrew):
```bash
# Install pgvector
brew install pgvector

# Or with PostgreSQL installation
brew install postgresql@15
brew install pgvector  # Install after PostgreSQL
```

#### On Windows:
Download pre-built binaries from [pgvector releases](https://github.com/pgvector/pgvector/releases) and follow the installation instructions, or use a PostgreSQL distribution that includes pgvector (e.g., from EnterpriseDB).

### 2. Enable the Extension in Your Database

After pgvector is installed on PostgreSQL:

```sql
-- Connect to your database
psql postgresql://postgres:postgres@localhost:5432/gov_intelligence_nlp

-- Create the extension
CREATE EXTENSION vector;

-- Verify installation
SELECT * FROM pg_extension WHERE extname = 'vector';
```

### 3. Run Database Migrations

Once pgvector is enabled:

```bash
cd backend
export DATABASE_SYNC_URL="postgresql://postgres:postgres@localhost:5432/gov_intelligence_nlp"
alembic upgrade head
```

## Troubleshooting

### "extension "vector" is not available"

This error means pgvector is not installed on your PostgreSQL server.

**Solution:** Complete step 1 above for your operating system.

### "Could not open extension control file"

The pgvector files were installed to the wrong location.

**Solution:**
1. Verify pgvector is in PostgreSQL's extension directory:
   ```bash
   # Linux/macOS
   find /usr/share/postgresql -name "vector.control"
   
   # macOS with Homebrew
   find /usr/local/Cellar/postgresql -name "vector.control"
   ```

2. If not found, reinstall pgvector following the appropriate instructions above.

### "make: No such file or directory"

Your system is missing build tools.

**Solution:**
- **Linux:** `sudo apt-get install build-essential postgresql-server-dev-15`
- **macOS:** `xcode-select --install`
- **Windows:** Use pre-built binaries instead

## Verification

Test that pgvector is working:

```python
# backend/test_pgvector.py
from app.db.session import async_session_maker
from sqlalchemy import text
import asyncio

async def test_pgvector():
    async with async_session_maker() as session:
        result = await session.execute(
            text("SELECT * FROM pg_extension WHERE extname = 'vector'")
        )
        extension = result.fetchone()
        if extension:
            print("pgvector is properly installed!")
        else:
            print("pgvector extension not found")

asyncio.run(test_pgvector())
```

## Version Requirements

- PostgreSQL: 15+
- pgvector: 0.5+
- Python pgvector package: 0.2.0+

## References

- [pgvector GitHub Repository](https://github.com/pgvector/pgvector)
- [pgvector Installation Guide](https://github.com/pgvector/pgvector#installation)
- [pgvector Documentation](https://github.com/pgvector/pgvector#usage)
