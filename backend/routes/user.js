const express = require('express');
const router = express.Router();


const { restrictTo, restrictToLoggedinUserOnly } = require('../middlewares/auth');


const {     
    handlePOSTuser,
    handleUserLogin,
    handleUserLogout,
    getAllUsers,
    getDashboard,
} = require('../controllers/user');

router.post('/register', handlePOSTuser);
router.post('/login', handleUserLogin);
router.post('/logout', restrictToLoggedinUserOnly, handleUserLogout);
router.get('/dashboard', restrictToLoggedinUserOnly, getDashboard);
router.get('/all', restrictTo(['admin']), getAllUsers); 

module.exports = router;