const express = require('express');
const router = express.Router();

const { restrictTo, restrictToLoggedinUserOnly } = require('../middlewares/auth');

const {
  handlePOSTcontest,
  getAllContests,
  getContestById,
  deleteContest,
  getContestLeaderboard,
} = require('../controllers/contest');

const {
    handlePOSTsubmission,
    getSubmissionsByContest,
    validateSubmissionInput
} = require('../controllers/submission');

router.get('/', getAllContests);
router.post('/', restrictToLoggedinUserOnly, handlePOSTcontest);
router.get('/:id', getContestById);
router.get('/:id/leaderboard', getContestLeaderboard);
router.delete('/:id', restrictTo(['admin', 'creator_contest']), deleteContest);

router.post('/:id/submit', restrictToLoggedinUserOnly, validateSubmissionInput, handlePOSTsubmission);
router.get('/:id/submissions', restrictTo(['admin', 'jury_contest', 'creator_contest']), getSubmissionsByContest);



module.exports = router;