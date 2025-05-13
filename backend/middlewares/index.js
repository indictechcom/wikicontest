const fs = require('fs');

function logReqRes(file) {
    return (req, res, next) => {
        fs.appendFile(
            file,
            `${req.method} ${req.url} ${new Date().toISOString()}\n`,
            (err) => {
                next();
            }
        );
    };
}

module.exports = {
    logReqRes,
}