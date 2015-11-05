var express = require('express');

var zlib = require('zlib');

var path = require('path');

var app = express();

app.use(function(req, res, next) {
	  res.header("Access-Control-Allow-Origin", "*");
	  res.header("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept");
	  res.header("Access-Control-Allow-Methods", "GET, OPTIONS");
	  next();
});

function getDB() {
	var gunzip = zlib.createGunzip();
	var fs = require('fs');
	var datadir = path.join('..', '..', 'data');
	try {
		var inp = fs.createReadStream(path.join(datadir, 'tree.db.gz'));
		var out = fs.createWriteStream(path.join(datadir, 'tree.db'));
		inp.pipe(gunzip).pipe(out);
	} catch (err) {
		console.log("Error:", err);
	}
	
	var dbfile = path.join(datadir, 'tree.db');
	return new sqlite3.Database(dbfile);
}

app.get('/id', function(req, res) {
	var db = getDB();
	db.serialize(function() {
		db.get("SELECT * FROM tree WHERE parentid IS NULL", function(err, row) {
			res.jsonp(row);
		});
	});
});
app.get('/id/:id', function(req, res) {
	var db = getDB();
	db.serialize(function() {
		db.get("SELECT * FROM tree WHERE id = ?", (req.params.id), function(err, row) {
			res.jsonp(row);
		});
	});
});

app.get('/list', function(req, res) {
	var db = getDB();
	db.serialize(function() {
		db.all("SELECT * FROM tree WHERE parentid = (SELECT id FROM tree WHERE parentid IS NULL) ORDER BY size DESC", function(err, rows) {
			res.jsonp(rows);
		});
	});
});
app.get('/list/:id', function(req, res) {
	var db = getDB();
	db.serialize(function() {
		db.all("SELECT * FROM tree WHERE parentid = ? ORDER BY size DESC", (req.params.id), function(err, rows) {
			res.jsonp(rows);
		});
	});
});

function getpath(res, id, path) {
	var db = getDB();
	if ( typeof path == 'undefined' ) {
		var path = [];
	}
	db.serialize(function() {
		db.get("SELECT * FROM tree WHERE id = ?", (id), function(err, row) {
			path.unshift(row);
			if ( row['parentid'] == null ) {
				res.jsonp(path);
			} else {
				getpath(res, row['parentid'], path);
			}
		});
	})
}
app.get('/path/:id', function(req, res) {
	getpath(res, req.params.id);
});

app.get('/path', function(req, res) {
	var db = getDB();
	db.serialize(function() {
		db.get("SELECT * FROM tree WHERE parentid IS NULL", function(err, row) {
			res.jsonp([row])
		});
	});
});


function get_path_and_list(res, id, orig_id, path) {
	var db = getDB();
	if ( typeof orig_id == 'undefined' ) {
		var path = [];
		var orig_id = id;
	}
	db.serialize(function() {
		db.get("SELECT * FROM tree WHERE id = ?", (id), function(err, row) {
			path.unshift(row);
			if ( row['parentid'] == null ) {
				var data = {};
				data['path'] = path;
				db.all("SELECT * FROM tree WHERE parentid = ? ORDER BY size DESC", (orig_id), function(err, rows) {
					data['list'] = rows;
					res.jsonp(data);
				});
			} else {
				get_path_and_list(res, row['parentid'], orig_id, path);
			}
		});
	});
}
app.get('/info', function(req, res) {
	if ( req.query.id ) {
		get_path_and_list(res, req.query.id);
	} else {
		var db = getDB();
		var data = {};
		db.serialize(function() {
			db.get("SELECT * FROM tree WHERE parentid is NULL", function(err, row) {
				data['path'] = [row];
				db.all("SELECT * FROM tree WHERE parentid = (SELECT id FROM tree WHERE parentid IS NULL) ORDER BY size DESC", function(err, rows) {
					data['list'] = rows;
					res.jsonp(data);
				});
			});
		});
	}
});

app.listen(3000);
console.log('Listening on port 3000...');
