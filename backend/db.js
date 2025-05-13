const sqlite3 = require('sqlite3').verbose();


function connectDb() {
  return new Promise((resolve, reject) => {
    const db = new sqlite3.Database('./wikicontest.db', (err) => {
      if (err) {
        console.error('Error opening database', err);
        reject(err);
      } else {
        console.log('Connected to the SQLite database!');
        resolve(db); 
      }
    });
  });
}


function closeDb(db) {
  return new Promise((resolve, reject) => {
    if (db) {
      db.close((err) => {
        if (err) {
          console.error('Error closing database', err);
          reject(err);
        } else {
          console.log('Database connection closed');
          resolve(); 
        }
      });
    } else {
      reject('No database connection found');
    }
  });
}

module.exports = {
  connectDb,
  closeDb,
};
