-- Schema untuk The Trust Protocol: Zero's Authority
-- Dijalankan oleh init_db.py untuk membuat zero_authority.db

DROP TABLE IF EXISTS users;
DROP TABLE IF EXISTS archives;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member'
);

CREATE TABLE archives (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    required_role TEXT NOT NULL DEFAULT 'member'
);

-- Seed data
-- Catatan: ini kredensial demo untuk skenario CTF, bukan contoh penggunaan nyata.
INSERT INTO users (username, password, role) VALUES
    ('kallen', 'imeleven', 'member');

INSERT INTO archives (title, content, required_role) VALUES
    (
        'Public Operation Report',
        'Laporan operasi rutin Black Knights. Tidak ada informasi sensitif di sini. Semua anggota jaringan dapat membaca arsip ini sebagai bagian dari transparansi internal.',
        'member'
    ),
    (
        'Zero''s Secret Archive',
        'Dokumen ini hanya dapat dibuka oleh identitas dengan otoritas Zero. Jika kamu membacanya, berarti sistem telah mempercayai klaim otoritasmu. Flag: TecFest26{z3r0_tru5t_n0_4uth0rity}',
        'zero'
    );
