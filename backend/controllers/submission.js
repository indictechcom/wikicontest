const { body, validationResult } = require('express-validator');
const {getUserFromRequest} = require('../service/auth');

async function handlePOSTsubmission(req, res) {
  const { article_title, article_link } = req.body;
  console.log(article_link,article_title);
  const status = req.body.status || 'pending'; // Default to 'pending' if not provided
  
  let user;
  try {
    user = getUserFromRequest(req);
  } catch (err) {
    return res.status(401).json({ error: err.message });
  }
  
  const user_id = user.id;
  const contest_id = req.params.id;

  const db = req.app.locals.db;

  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }

  const checkContestQuery = `SELECT * FROM contests WHERE id = ?`;

  db.get(checkContestQuery, [contest_id], (err, contest) => {
    if (err) {
      console.error('Error checking contest:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }

    if (!contest) {
      return res.status(404).json({ error: 'Contest not found' });
    }

    const now = new Date();
    const startDate = new Date(contest.start_date);
    const endDate = new Date(contest.end_date);

    if (now < startDate) {
      return res.status(400).json({ error: 'Contest has not started yet' });
    }

    if (now > endDate) {
      return res.status(400).json({ error: 'Contest has ended' });
    }

    const checkExistingQuery = `SELECT id FROM submissions WHERE user_id = ? AND contest_id = ?`;

    db.get(checkExistingQuery, [user_id, contest_id], (err, existing) => {
      if (err) {
        console.error('Error checking existing submission:', err);
        return res.status(500).json({ error: 'Internal server error' });
      }

      if (existing) {
        return res.status(400).json({ error: 'You have already submitted to this contest' });
      }

      const insertSubmissionQuery = `
        INSERT INTO submissions (user_id, contest_id, article_title, article_link, status)
        VALUES (?, ?, ?, ?, ?)
      `;

      db.run(insertSubmissionQuery, [
        user_id,
        contest_id,
        article_title,
        article_link,
        status || 'pending'
      ], function (err) {
        if (err) {
          console.error('Error inserting submission:', err);
          res.status(500).json({ error: 'Internal server error' });
        } else {
          res.status(201).json({
            message: 'Submission created successfully',
            submissionId: this.lastID,
            contest_id: contest_id,
            article_title: article_title
          });
        }
      });
    });
  });
}

const validateSubmissionInput = [
  body('article_title').notEmpty().withMessage('Article title is required'),
  body('article_link').isURL().withMessage('Article link must be a valid URL'),
];

async function getSubmissionsByContest(req, res) {
  const { id } = req.params;
  const db = req.app.locals.db;
  
  let user;
  try {
    user = getUserFromRequest(req);
  } catch (err) {
    return res.status(401).json({ error: err.message });
  }

  const checkPermissionQuery = `
    SELECT c.created_by, c.jury_members 
    FROM contests c 
    WHERE c.id = ?
  `;

  db.get(checkPermissionQuery, [id], (err, contest) => {
    if (err) {
      console.error('Error checking permissions:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }

    if (!contest) {
      return res.status(404).json({ error: 'Contest not found' });
    }

    const selectSubmissionsQuery = `
      SELECT 
        s.*,
        u.username,
        u.email,
        c.name as contest_name
      FROM submissions s
      LEFT JOIN users u ON s.user_id = u.id
      LEFT JOIN contests c ON s.contest_id = c.id
      WHERE s.contest_id = ?
      ORDER BY s.submitted_at DESC
    `;
    
    db.all(selectSubmissionsQuery, [id], (err, submissions) => {
      if (err) {
        console.error('Error fetching submissions:', err);
        res.status(500).json({ error: 'Internal server error' });
      } else {
        res.status(200).json(submissions);
      }
    });
  });
}

async function updateSubmissionStatusandScore(req, res) {
  const { id } = req.params;
  const { status } = req.body;
  const db = req.app.locals.db;

  let user;
  try {
    user = getUserFromRequest(req);
  } catch (err) {
    return res.status(401).json({ error: err.message });
  }

  const getSubmissionQuery = `
    SELECT s.*, c.created_by, c.jury_members, c.marks_setting_accepted, c.marks_setting_rejected
    FROM submissions s
    JOIN contests c ON s.contest_id = c.id
    WHERE s.id = ?
  `;

  db.get(getSubmissionQuery, [id], (err, submission) => {
    if (err) {
      console.error('Error fetching submission:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }

    if (!submission) {
      return res.status(404).json({ error: 'Submission not found' });
    }

    if (submission.status === 'accepted' && status === 'accepted') {
      return res.status(200).json({ message: 'Submission is already accepted. No changes made.' });
    }
    if (submission.status === 'rejected' && status === 'rejected') {
      return res.status(200).json({ message: 'Submission is already rejected. No changes made.' });
    }
    let finalScore ;
    if (finalScore === undefined) {
      if (status === 'accepted') {
        finalScore = submission.marks_setting_accepted;
      } else if (status === 'rejected') {
        finalScore = submission.marks_setting_rejected;
      } else {
        finalScore = 0;
      }
    }

    const updateSubmissionQuery = `
      UPDATE submissions 
      SET status = ?, score = ?
      WHERE id = ?
    `;

    db.run(updateSubmissionQuery, [status, finalScore, id], function (err) {
      if (err) {
        console.error('Error updating submission:', err);
        return res.status(500).json({ error: 'Internal server error' });
      }

      const scoreDifference = finalScore - (submission.score || 0);

      const updateUserScoreQuery = `
        UPDATE users 
        SET score = score + ?
        WHERE id = ?
      `;

      db.run(updateUserScoreQuery, [scoreDifference, submission.user_id], (err) => {
        if (err) {
          console.error('Error updating user score:', err);
          return res.status(500).json({ error: 'Error updating user score' });
        }

        res.status(200).json({ 
          message: 'Submission updated successfully',
          status: status,
          score: finalScore
        });
      });
    });
  });
}

async function getSubmissionById(req, res) {
  const { id } = req.params;
  const db = req.app.locals.db;
  
  let user;
  try {
    user = getUserFromRequest(req);
  } catch (err) {
    return res.status(401).json({ error: err.message });
  }

  const query = `SELECT * FROM submissions WHERE id = ?`;

  db.get(query, [id], (err, submission) => {
    if (err) {
      console.error('Error fetching submission:', err);
      return res.status(500).json({ error: 'Internal server error' });
    }

    if (!submission) {
      return res.status(404).json({ error: 'Submission not found' });
    }
    return res.status(200).json(submission);
   });
}

async function getAllSubmissions(req, res) {
  const db = req.app.locals.db;

  const selectAllSubmissionsQuery = `SELECT * FROM submissions`;

  db.all(selectAllSubmissionsQuery, [], (err, submissions) => {
    if (err) {
      console.error('Error fetching submissions:', err);
      res.status(500).json({ error: 'Internal server error' });
    } else {
      res.status(200).json(submissions);
    }
  });
}
  
module.exports = {
  handlePOSTsubmission,
  updateSubmissionStatusandScore,
  getSubmissionById,
  validateSubmissionInput,
  getAllSubmissions,
  getSubmissionsByContest,
};