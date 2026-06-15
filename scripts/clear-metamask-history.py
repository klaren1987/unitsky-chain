import sqlite3
import shutil
import os
import sys

db = sys.argv[1]
bak = db + ".bak_metamask_clear"
if not os.path.exists(bak):
    shutil.copy2(db, bak)
conn = sqlite3.connect(db)
patterns = (
    "%metamask%",
    "%127.0.0.1:8765%",
    "%nkbihfbeogaeaoehlefnkodbefgpgknn%",
    "%ust%",
)
for p in patterns:
    conn.execute(
        "DELETE FROM visits WHERE url IN (SELECT id FROM urls WHERE url LIKE ?)",
        (p,),
    )
    conn.execute("DELETE FROM urls WHERE url LIKE ?", (p,))
conn.commit()
conn.close()
print("History cleaned for MetaMask-related URLs")
