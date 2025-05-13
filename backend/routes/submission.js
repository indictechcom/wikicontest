const express = require('express');
const router = express.Router();

const { restrictTo, restrictToLoggedinUserOnly } = require('../middlewares/auth');

const {
  updateSubmissionStatusandScore,
  getSubmissionById,
  getAllSubmissions,
} = require('../controllers/submission');

router.get('/', restrictTo(['admin']), getAllSubmissions);
router.get('/:id', restrictTo(['owner', 'jury_submission','admin' ]), getSubmissionById);
router.put('/:id', restrictTo(['jury_submission', 'admin']), updateSubmissionStatusandScore);

module.exports = router;