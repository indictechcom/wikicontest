const { get } = require('mongoose');
const {getUserFromRequest}  = require('../service/auth');
async function handlePOSTcontest(req, res) {
    const {
      name,
      code_link,
      project_name,
      description,
      start_date,
      end_date,
      rules,
      marks_setting_accepted,
      marks_setting_rejected,
      jury_members
    } = req.body;
  
    const db = req.app.locals.db;

    let user;
    try {
      user = getUserFromRequest(req); 
    } catch (err) {
      return res.status(401).json({ error: err.message });
    }


    const created_by = user.username;

    console.log('Created by:', created_by);
    // Validate jury_members array
    if (!Array.isArray(jury_members) || jury_members.length === 0) {
      return res.status(400).json({ error: 'Jury members must be a non-empty array of usernames' });
    }
  
    // Validate that all usernames exist
    const placeholders = jury_members.map(() => '?').join(',');
    const checkUsersQuery = `SELECT username FROM users WHERE username IN (${placeholders})`;
  
    db.all(checkUsersQuery, jury_members, (err, rows) => {
      if (err) {
        console.error('Error checking jury members:', err);
        return res.status(500).json({ error: 'Internal server error' });
      }
  
      const existingUsernames = rows.map(row => row.username);
      const missing = jury_members.filter(j => !existingUsernames.includes(j));
  
      if (missing.length > 0) {
        return res.status(400).json({ error: `These jury members do not exist: ${missing.join(', ')}` });
      }
  
      // Convert rules object to JSON string
      const rulesString = JSON.stringify(rules);
  
      // Convert jury_members array to comma-separated string
      const juryMembersString = jury_members.join(',');
    console.log('Jury members:', juryMembersString);
      const insertContestQuery = `
        INSERT INTO contests (
          name, code_link, project_name, created_by, description, 
          start_date, end_date, rules, marks_setting_accepted, 
          marks_setting_rejected, jury_members
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `;
  
      db.run(insertContestQuery, [
        name,
        code_link,
        project_name,
        created_by,
        description,
        start_date,
        end_date,
        rulesString,
        marks_setting_accepted || 0,
        marks_setting_rejected || 0,
        juryMembersString
      ], function (err) {
        if (err) {
          console.error('Error inserting contest:', err);
          res.status(500).json({ error: 'Internal server error' });
        } else {
          res.status(201).json({ message: 'Contest created successfully', contestId: this.lastID });
        }
      });
  
    });
  }
  
  
async function getAllContests(req, res) {
  const db = req.app.locals.db;
  const selectAllContestsQuery = `
    SELECT 
      c.*,
      u.username AS creator_name
    FROM contests c
    LEFT JOIN users u ON c.created_by = u.username
    ORDER BY c.created_at DESC
  `;

  db.all(selectAllContestsQuery, [], (err, contests) => {
    if (err) {
      console.error('Error fetching contests:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }

    const now = new Date();

    // Separate contests into categories
    const current = [];
    const upcoming = [];
    const past = [];

    contests.forEach(contest => {
      // Parse jury_members and rules fields
      const parsedContest = {
        ...contest,
        jury_members: contest.jury_members 
          ? contest.jury_members.split(',').map(username => username.trim()).filter(Boolean)
          : [],
        rules: contest.rules 
          ? JSON.parse(contest.rules) 
          : {}
      };

      // Parse dates
      const startDate = new Date(contest.start_date);
      const endDate = new Date(contest.end_date);

      // Categorize
      if (now >= startDate && now <= endDate) {
        current.push(parsedContest);
      } else if (now < startDate) {
        upcoming.push(parsedContest);
      } else if (now > endDate) {
        past.push(parsedContest);
      }
    });

    res.status(200).json({
      current,
      upcoming,
      past
    });
  });
}

  
  
  async function getContestById(req, res) {
    const { id } = req.params;
    const db = req.app.locals.db;
  
    const selectContestQuery = `SELECT * FROM contests WHERE id = ?`;
  
    db.get(selectContestQuery, [id], (err, contest) => {
      if (err) {
        console.error('Error fetching contest:', err);
        return res.status(500).json({ error: 'Internal server error' });
      } else if (!contest) {
        return res.status(404).json({ error: 'Contest not found' });
      }
  
      // Convert jury_members and rules
      contest.jury_members = contest.jury_members 
        ? contest.jury_members.split(',').map(username => username.trim()).filter(Boolean)
        : [];
      contest.rules = contest.rules 
        ? JSON.parse(contest.rules) 
        : {};
  
      res.status(200).json(contest);
    });
  }
  
  

  async function deleteContest(req, res) {
    const { id } = req.params;
    const db = req.app.locals.db;
  
    // Check if user is the creator or an admin
    const checkPermissionQuery = `SELECT created_by FROM contests WHERE id = ?`;
  
    db.get(checkPermissionQuery, [id], (err, contest) => {
      if (err) {
        console.error('Error checking contest permissions:', err);
        return res.status(500).json({ error: 'Internal server error' });
      }
  
      if (!contest) {
        return res.status(404).json({ error: 'Contest not found' });
      }
  
      if (contest.created_by !== req.user.username && req.user.role !== 'admin') {
        return res.status(403).json({ error: 'You are not allowed to delete this contest' });
      }
  
      const deleteContestQuery = `DELETE FROM contests WHERE id = ?`;
  
      db.run(deleteContestQuery, [id], function (err) {
        if (err) {
          console.error('Error deleting contest:', err);
          res.status(500).json({ error: 'Internal server error' });
        } else {
          res.status(200).json({ message: 'Contest deleted successfully' });
        }
      });
    });
  }
  
async function getContestLeaderboard(req, res) {
    const { id } = req.params;
    const db = req.app.locals.db;
  
    const selectLeaderboardQuery = `
      SELECT 
        s.user_id,
        u.username,
        SUM(s.score) AS total_score
      FROM submissions s
      LEFT JOIN users u ON s.user_id = u.id
      WHERE s.contest_id = ?
      GROUP BY s.user_id, u.username
      ORDER BY total_score DESC
    `;
  
    db.all(selectLeaderboardQuery, [id], (err, leaderboard) => {
      if (err) {
        console.error('Error fetching leaderboard:', err);
        return res.status(500).json({ error: 'Internal server error' });
      }
  
      res.status(200).json(leaderboard);
    });
  }

  module.exports = {
    handlePOSTcontest,
    getAllContests,
    getContestById,
    deleteContest,
    getContestLeaderboard,
  };