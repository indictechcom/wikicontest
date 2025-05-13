const { getUser } = require('../service/auth');

function checkforAuth(req, res, next) {
    const tokenCookie = req.cookies?.uid;
    req.user = null;
    if (!tokenCookie) {
        return next();
    }

    const user = getUser(tokenCookie);
    req.user = user;
    next();
}

function restrictTo(roles = []) {
    return (req, res, next) => {
        if (!req.user) {
            return res.status(401).json({ error: 'You are not logged in' });
        }

        const db = req.app.locals.db;

        const checks = roles.map(role => {
            return new Promise((resolve, reject) => {
                if (role === 'owner' && req.params.id) {
                    const submissionId = req.params.id;
                    const checkOwnerQuery = `SELECT user_id FROM submissions WHERE id = ?`;
                    
                    db.get(checkOwnerQuery, [submissionId], (err, submission) => {
                        if (err) return reject({ status: 500, error: 'Internal server error' });
                        if (!submission) return reject({ status: 404, error: 'Submission not found' });
                        if (submission.user_id === req.user.id || req.user.role === 'admin') return resolve(true);
                        return resolve(false);
                    });
                } 
                else if (role === 'creator_contest' && req.params.id) {
                    const contestId = req.params.id;
                    const checkContestQuery = `SELECT created_by FROM contests WHERE id = ?`;

                    db.get(checkContestQuery, [contestId], (err, contest) => {
                        if (err) return reject({ status: 500, error: 'Internal server error' });
                        if (!contest) return reject({ status: 404, error: 'Contest not found' });

                        if (contest.created_by === req.user.username || req.user.role === 'admin') {
                            return resolve(true);
                        }

                        return resolve(false);
                    });
                }
                // Jury of Submission
                else if (role === 'jury_submission' && req.params.id) {
                    const submissionId = req.params.id;

                    const checkSubmissionQuery = `SELECT contest_id FROM submissions WHERE id = ?`;
                    db.get(checkSubmissionQuery, [submissionId], (err, submission) => {
                        if (err) return reject({ status: 500, error: 'Internal server error' });
                        if (!submission) return reject({ status: 404, error: 'Submission not found' });

                        const contestId = submission.contest_id;

                        const checkContestQuery = `SELECT jury_members FROM contests WHERE id = ?`;
                        db.get(checkContestQuery, [contestId], (err, contest) => {
                            if (err) return reject({ status: 500, error: 'Internal server error' });
                            if (!contest) return reject({ status: 404, error: 'Contest not found' });

                            const submissionJuryUsernames = contest.jury_members
                                ? contest.jury_members.split(',').map(u => u.trim())
                                : [];
                            console.log('Submission Jury Usernames:', submissionJuryUsernames);
                            if (submissionJuryUsernames.includes(req.user.username) || req.user.role === 'admin') {
                                return resolve(true);
                            }

                            return resolve(false);
                        });
                    });
                }

                // Jury of Contest
                else if (role === 'jury_contest' && req.params.id) {
                    const contestId = req.params.id;
                    const checkContestQuery = `SELECT jury_members FROM contests WHERE id = ?`;

                    db.get(checkContestQuery, [contestId], (err, contest) => {
                        if (err) return reject({ status: 500, error: 'Internal server error' });
                        if (!contest) return reject({ status: 404, error: 'Contest not found' });

                        const contestJuryUsernames = contest.jury_members
                            ? contest.jury_members.split(',').map(u => u.trim())
                            : [];

                        console.log('Contest Jury Usernames:', contestJuryUsernames);

                        if (contestJuryUsernames.includes(req.user.username) || req.user.role === 'admin') {
                            return resolve(true);
                        }

                        return resolve(false);
                    });
                }
            else {
                    // Normal role check
                    if (req.user.role === role || req.user.role === 'admin') return resolve(true);
                    return resolve(false);
                }
            });
        });

        Promise.allSettled(checks).then(results => {
            // First check if any rejected (error responses)
            for (let r of results) {
                if (r.status === 'rejected') {
                    const { status, error } = r.reason;
                    return res.status(status).json({ error });
                }
            }

            // Then see if any role passed
            const anyAllowed = results.some(r => r.status === 'fulfilled' && r.value === true);

            if (anyAllowed) return next();
            console.log(anyAllowed);
            return res.status(403).json({ error: 'You are not allowed to access this route' });
        });
    };
}


async function restrictToLoggedinUserOnly(req, res, next) {
    const userUid = req.cookies?.uid;
    if (!userUid) {
        return res.status(401).json({ error: 'You are not logged in' });
    }
    const user = getUser(userUid);
    if (!user) {
        return res.status(401).json({ error: 'Invalid user' });
    }
    req.user = user;
    next();
}

module.exports = {
    checkforAuth,
    restrictTo,
    restrictToLoggedinUserOnly,
};