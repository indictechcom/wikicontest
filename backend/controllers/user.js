const { setUser, getUser, getUserFromRequest } = require('../service/auth');
const bcrypt = require('bcrypt');

async function handlePOSTuser(req, res) {
  const { username, email, password } = req.body;
  const role = req.body.role || 'user'; 

  const db = req.app.locals.db; 
  const hashedPassword = await bcrypt.hash(password, 10);
  const insertUserQuery = `INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)`;

  db.run(insertUserQuery, [username, email, hashedPassword, role], function (err) {
    if (err) {
      console.error('Error inserting user:', err);
      res.status(500).json({ error: 'Internal server error' });
    } else {
      res.status(201).json({ message: 'User created successfully', userId: this.lastID , Username :  this.username});
    }
  });
}

async function handleUserLogin(req, res) {
  const { email, password } = req.body;
  const db = req.app.locals.db;  
  const selectUserQuery = `SELECT * FROM users WHERE email = ?`;

  db.get(selectUserQuery, [email], async (err, user) => {
    if (err) {
      console.error('Error fetching user:', err);
      res.status(500).json({ error: 'Internal server error' });
    } else if (!user) {
      res.status(401).json({ error: 'Invalid email or password' });
    } else {
      const isPasswordValid = await bcrypt.compare(password, user.password);
      if (!isPasswordValid) {
        res.status(401).json({ error: 'Invalid email or password' });
      } else {
        const token = setUser(user);
        res.cookie('uid', token, { httpOnly: true });
        res.status(200).json({ message: 'Login successful', userId: user.id, Username :  user.username });
      }
    }
  });
}

async function handleUserLogout(req, res) {
  res.clearCookie('uid');
  res.status(200).json({ message: 'Logout successful' });
}

async function getAllUsers(req, res) {
  const db = req.app.locals.db;  
  const selectAllUsersQuery = `SELECT id, username, email, role, score, created_at FROM users`;

  db.all(selectAllUsersQuery, [], (err, users) => {
    if (err) {
      console.error('Error fetching users:', err);
      res.status(500).json({ error: 'Internal server error' });
    } else {
      res.status(200).json(users);
    }
  });
}

async function getDashboard(req, res) {
  const db = req.app.locals.db;
  
  let user;
  try {
    user = getUserFromRequest(req);
  } catch (err) {
    return res.status(401).json({ error: err.message });
  }

  const userId = user.id;

  const getUserTotalScoreQuery = `SELECT score FROM users WHERE id = ?`;
  
  db.get(getUserTotalScoreQuery, [userId], (err, userScore) => {
    if (err) {
      console.error('Error fetching user score:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }

    const getContestWiseScoresQuery = `
      SELECT 
        c.id as contest_id,
        c.name as contest_name,
        SUM(s.score) as contest_score,
        COUNT(s.id) as submission_count
      FROM contests c
      INNER JOIN submissions s ON c.id = s.contest_id
      WHERE s.user_id = ?
      GROUP BY c.id, c.name
      ORDER BY c.name
    `;

    db.all(getContestWiseScoresQuery, [userId], (err, contestScores) => {
      if (err) {
        console.error('Error fetching contest wise scores:', err);
        return res.status(500).json({ error: 'Internal server error' });
      }

      const getAllSubmissionsQuery = `
        SELECT 
          s.*,
          c.name as contest_name
        FROM submissions s
        INNER JOIN contests c ON s.contest_id = c.id
        WHERE s.user_id = ?
        ORDER BY s.submitted_at DESC
      `;

      db.all(getAllSubmissionsQuery, [userId], (err, submissions) => {
        if (err) {
          console.error('Error fetching submissions:', err);
          return res.status(500).json({ error: 'Internal server error' });
        }

        const submissionsByContest = submissions.reduce((acc, submission) => {
          if (!acc[submission.contest_id]) {
            acc[submission.contest_id] = {
              contest_id: submission.contest_id,
              contest_name: submission.contest_name,
              submissions: []
            };
          }
          acc[submission.contest_id].submissions.push(submission);
          return acc;
        }, {});

        const getCreatedContestsQuery = `
          SELECT 
            c.*,
            COUNT(s.id) as submission_count
          FROM contests c
          LEFT JOIN submissions s ON c.id = s.contest_id
          WHERE c.created_by = ?
          GROUP BY c.id
          ORDER BY c.created_at DESC
        `;

        const username = user.username;
        db.all(getCreatedContestsQuery, [username], (err, createdContests) => {
          if (err) {
            console.error('Error fetching created contests:', err);
            return res.status(500).json({ error: 'Internal server error' });
          }

          const getJuryContestsQuery = `
            SELECT 
              c.*,
              COUNT(s.id) as submission_count
            FROM contests c
            LEFT JOIN submissions s ON c.id = s.contest_id
            WHERE c.jury_members LIKE '%,' || ? || ',%' 
               OR c.jury_members LIKE ? || ',%'
               OR c.jury_members LIKE '%,' || ?
               OR c.jury_members = ?
            GROUP BY c.id
            ORDER BY c.created_at DESC
          `;
          
          db.all(getJuryContestsQuery, [username, username, username, username], (err, juryContests) => {
            if (err) {
              console.error('Error fetching jury contests:', err);
              return res.status(500).json({ error: 'Internal server error' });
            }

            res.status(200).json({
              username : user.username,
              total_score: userScore ? userScore.score : 0,
              contest_wise_scores: contestScores,
              submissions_by_contest: Object.values(submissionsByContest),
              created_contests: createdContests,
              jury_contests: juryContests
            });
          });
        });
      });
    });
  });
}
  
module.exports = {
    handlePOSTuser,
    handleUserLogin,
    handleUserLogout,
    getAllUsers,
    getDashboard,
};