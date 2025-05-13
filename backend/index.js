const express = require('express');
const app = express();
const port = 3000;
const path = require('path');
const cors = require('cors');
const cookieParser = require('cookie-parser');

const userRoutes = require('./routes/user');
const contestRoutes = require('./routes/contest');
const submissionRoutes = require('./routes/submission');
const { createTables } = require('./models/tables');
const { checkforAuth, restrictToLoggedinUserOnly } = require('./middlewares/auth');
const { logReqRes } = require('./middlewares');
const { connectDb, closeDb } = require('./db');  

const corsOptions = {
  origin: 'http://localhost:5173',
  credentials: true,
};
app.use(cors(corsOptions));

app.use(express.json());
app.use(express.urlencoded({ extended: false }));
app.use(cookieParser());
app.use(checkforAuth);

const file = 'log.txt';
app.use(logReqRes(file));

let db; 

async function init() {
  db = await connectDb();      
  await createTables(db);      
  app.locals.db = db;          
  console.log('Database initialized');
}

init().catch((err) => {
  console.error('Error initializing database:', err);
});

app.use('/api/user', userRoutes);
app.use('/api/contest', contestRoutes);
app.use('/api/submission', submissionRoutes);
app.use('/api/cookie', (req, res) => {
  const tokenCookie = req.cookies?.uid;

  if (!tokenCookie || !req.user) {
    return res.status(401).json({ error: 'You are not logged in' });
  }

  res.status(200).json({
    userId: req.user.id,
    username: req.user.username,
    email: req.user.email,
  });
});


app.listen(port, () => {
  console.log(`app listening on port ${port}`);
});

process.on('SIGINT', () => {
  console.log('\nShutting down...');
  if (db) {
    closeDb(db)
      .then(() => {
        console.log('Database connection closed');
        process.exit(0);
      })
      .catch((err) => {
        console.error('Error closing database:', err);
        process.exit(1);
      });
  } else {
    process.exit(0);
  }
});