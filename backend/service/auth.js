// const sessionIdToUserMap = new Map(); //ststefull

const jwt = require('jsonwebtoken');
const secret= "rohank10";

function setUser(user){
    // sessionIdToUserMap.set(id,user);
    return jwt.sign({
        id : user.id,
        email : user.email,
        username : user.username,
        role : user.role
    },secret);
}

function getUser(token){
    // return sessionIdToUserMap.get(id);
    if(!token) return null;
    try{
        return jwt.verify(token,secret);
    }catch(e){
        return null;
    }
}

function getUserFromRequest(req) {
    const userUid = req.cookies?.uid;
    if (!userUid) {
      throw new Error('You are not logged in');
    }
  
    const user = getUser(userUid);
    if (!user) {
      throw new Error('Invalid user');
    }
  
    return user;
  }
  

module.exports = {setUser,getUser,getUserFromRequest};