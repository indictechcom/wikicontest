
async function createTables(db) {
  
  const createUsersTable = `
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username TEXT NOT NULL UNIQUE,
      email TEXT NOT NULL UNIQUE,
      role TEXT NOT NULL,  -- Can be 'admin', 'jury', 'user', etc.
      password TEXT NOT NULL,
      score INTEGER DEFAULT 0,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
  `;

  const createContestsTable = `
    CREATE TABLE IF NOT EXISTS contests (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      code_link TEXT,
      project_name TEXT NOT NULL, -- e.g., 'Wikimedia', 'Wikipedia'
      created_by TEXT NOT NULL,  -- Foreign key from users table
      description TEXT,
      start_date DATE,
      end_date DATE,
      rules TEXT,
      marks_setting_accepted INTEGER DEFAULT 0,
      marks_setting_rejected INTEGER DEFAULT 0,
      jury_members TEXT,  -- List of user ids separated by commas
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (created_by) REFERENCES users(username)
    );
  `;

  const createSubmissionsTable = `
    CREATE TABLE IF NOT EXISTS submissions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      user_id INTEGER NOT NULL,  -- Foreign key from users table
      contest_id INTEGER NOT NULL,  -- Foreign key from contests table
      article_title TEXT NOT NULL,
      article_link TEXT NOT NULL,
      status TEXT NOT NULL,  -- Can be 'accepted', 'rejected', etc.
      score INTEGER DEFAULT 0,
      submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (user_id) REFERENCES users(id),
      FOREIGN KEY (contest_id) REFERENCES contests(id)
    );
  `;

  try {
    await new Promise((resolve, reject) => {
      db.run(createUsersTable, (err) => {
        if (err) {
          console.error('Error creating users table:', err);
          reject(err);
        } else {
          resolve();
        }
      });
    });

    await new Promise((resolve, reject) => {
      db.run(createContestsTable, (err) => {
        if (err) {
          console.error('Error creating contests table:', err);
          reject(err);
        } else {
          resolve();
        }
      });
    });

    await new Promise((resolve, reject) => {
      db.run(createSubmissionsTable, (err) => {
        if (err) {
          console.error('Error creating submissions table:', err);
          reject(err);
        } else {
          resolve();
        }
      });
    });

    console.log('Tables created successfully');
  } catch (err) {
    console.error('Error creating tables:', err);
  }
}

module.exports = {
    createTables,
}
