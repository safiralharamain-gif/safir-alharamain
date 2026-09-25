const express = require('express');
const cors = require('cors');
const multer = require('multer');
const crypto = require('crypto');
const { Pool } = require('pg');

const app = express();
const port = process.env.PORT || 3000;
const adminKey = process.env.ADMIN_KEY || '';
const allowedOrigins = (process.env.ALLOWED_ORIGINS || 'https://safiralharamain.com,https://safiralharamain-gif.github.io')
  .split(',').map(s => s.trim()).filter(Boolean);

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL ? { rejectUnauthorized: false } : false
});

app.use(cors({
  origin(origin, cb) {
    if (!origin || allowedOrigins.some(x => origin === x || origin.startsWith(x + '/'))) return cb(null, true);
    return cb(new Error('Origin not allowed'));
  }
}));
app.use(express.json({ limit: '3mb' }));

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 }
});

async function initDb() {
  await pool.query(`
    create table if not exists site_content (
      content_key text primary key,
      payload jsonb not null,
      updated_at timestamptz not null default now()
    );
  `);
  await pool.query(`
    create table if not exists media (
      id text primary key,
      mime_type text not null,
      data bytea not null,
      created_at timestamptz not null default now()
    );
  `);
}

function auth(req, res, next) {
  const key = req.get('x-admin-key') || '';
  if (!adminKey || key !== adminKey) return res.status(401).json({ ok: false, error: 'unauthorized' });
  next();
}

function cleanPayload(input) {
  const out = {};
  for (const key of ['brand', 'umrahGuide', 'hajjGuide', 'pastTrips']) {
    if (Object.prototype.hasOwnProperty.call(input || {}, key)) out[key] = input[key];
  }
  return out;
}

app.get('/health', (req, res) => res.json({ ok: true }));

app.get('/api/content', async (req, res) => {
  try {
    const q = await pool.query('select payload, updated_at from site_content where content_key=$1', ['portal']);
    if (!q.rowCount) return res.json({ ok: true, data: null });
    res.json({ ok: true, data: q.rows[0].payload, updatedAt: q.rows[0].updated_at });
  } catch (e) {
    res.status(500).json({ ok: false, error: 'content_read_failed' });
  }
});

app.post('/api/content', auth, async (req, res) => {
  try {
    const payload = cleanPayload(req.body);
    await pool.query(
      `insert into site_content(content_key,payload,updated_at)
       values($1,$2::jsonb,now())
       on conflict(content_key) do update set payload=excluded.payload,updated_at=now()`,
      ['portal', JSON.stringify(payload)]
    );
    res.json({ ok: true });
  } catch (e) {
    res.status(500).json({ ok: false, error: 'content_save_failed' });
  }
});

app.post('/api/media', auth, upload.single('file'), async (req, res) => {
  try {
    if (!req.file || !String(req.file.mimetype).startsWith('image/')) {
      return res.status(400).json({ ok: false, error: 'image_required' });
    }
    const id = crypto.randomUUID();
    await pool.query('insert into media(id,mime_type,data) values($1,$2,$3)', [id, req.file.mimetype, req.file.buffer]);
    const base = process.env.PUBLIC_BASE_URL || (req.protocol + '://' + req.get('host'));
    res.json({ ok: true, url: base + '/api/media/' + id });
  } catch (e) {
    res.status(500).json({ ok: false, error: 'media_upload_failed' });
  }
});

app.get('/api/media/:id', async (req, res) => {
  try {
    const q = await pool.query('select mime_type,data from media where id=$1', [req.params.id]);
    if (!q.rowCount) return res.status(404).end();
    res.set('Content-Type', q.rows[0].mime_type);
    res.set('Cache-Control', 'public, max-age=31536000, immutable');
    res.send(q.rows[0].data);
  } catch (e) {
    res.status(500).end();
  }
});

initDb()
  .then(() => app.listen(port, () => console.log('SAFIR CMS listening on ' + port)))
  .catch(err => {
    console.error('Database init failed', err);
    process.exit(1);
  });
