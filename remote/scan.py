import os
import sys
import gzip
import sqlite3
import tempfile


def usage():
    print("usage:")
    print("    " + os.path.basename(__file__) + " [dir]")
    sys.exit(1)


commandline_args_count = len(sys.argv)
rootdir = "."
if commandline_args_count == 2:
    rootdir = sys.argv[1]
else:
    if commandline_args_count > 2:
        usage()

temp = tempfile.NamedTemporaryFile()

try:
    con = sqlite3.connect(temp.name)

    with con:
        cur = con.cursor()
        cur.execute("DROP TABLE IF EXISTS tree")
        cur.execute('''CREATE TABLE tree(id       INTEGER PRIMARY KEY     AUTOINCREMENT,
                                         type     TEXT                    NOT NULL,
                                         size     INTEGER                 NOT NULL,
                                         name     TEXT                    NOT NULL,
                                         parentid INTEGER,
                                         CONSTRAINT parent_fk FOREIGN KEY (parentid) REFERENCES fs(id)
                                         UNIQUE (name, parentid)
                                        );'''
                    )
        cur.execute("DROP INDEX IF EXISTS parentid_index")
        cur.execute("CREATE INDEX parentid_index ON tree (parentid)")

        con.commit()

        othermounts = []

        rootdir = unicode(rootdir)

        for root, dirs, files in os.walk(rootdir):

            omfound = False
            for om in othermounts:
                if root.startswith(om):
                    omfound = True
            if omfound:
                continue

            # build root in db
            dsize = os.path.getsize(root)
            path = root
            if path.startswith(rootdir):
                path = path[len(rootdir):]
            if path.startswith(os.path.sep):
                path = path[len(os.path.sep):]
            allparts = []
            while path != '':
                parts = os.path.split(path)
                if parts[0] == path:  # sentinel for absolute paths
                    allparts.insert(0, parts[0])
                    break
                elif parts[1] == path:  # sentinel for relative paths
                    allparts.insert(0, parts[1])
                    break
                else:
                    path = parts[0]
                    allparts.insert(0, parts[1])

            allparts.insert(0, rootdir)

            parent = None
            first, last = os.path.split(root)

            root = root.rstrip()
            rootdir = rootdir.rstrip()

            if root == rootdir:
                # first iteration / root dir (no parent)
                cur.execute("INSERT INTO tree (type, size, name, parentid) "
                            "VALUES('dir', ?, ?, NULL)", (dsize, root))
                parent = cur.lastrowid
            else:
                # not first iteration

                fid = None
                for part in allparts:
                    if not fid:
                        cur.execute("SELECT id FROM tree WHERE name=? AND parentid IS NULL", (part,))
                    else:
                        cur.execute("SELECT id FROM tree WHERE name=? AND parentid=?", (part, fid))
                    try:
                        fid = cur.fetchone()[0]
                    except TypeError:
                        print("root: " + str(root))
                        print("allparts: " + str(allparts))
                        print("part: " + str(part))
                        print("id: " + str(fid))
                        raise
                parent = fid

            totalsize = 0

            # add dirs to db
            for dir in dirs:
                d = os.path.join(root, dir)

                if os.path.islink(d):
                    continue

                # directory is a different mount point
                if os.path.ismount(d):
                    othermounts.append(d)
                    continue

                # directory is a subdirectory of a different mount point
                omfound = False
                for om in othermounts:
                    if d.startswith(om):
                        omfound = True
                if omfound:
                    continue

                dsize = os.path.getsize(d)
                totalsize += dsize
                if os.path.isdir(d):
                    cur.execute("INSERT INTO tree (type, size, name, parentid) "
                                "VALUES('dir', ?, ?, ?)", (dsize, dir, parent))

            # add files to db
            for fname in files:
                f = os.path.join(root, fname)

                if os.path.islink(f):
                    continue

                try:
                    fsize = os.path.getsize(f)
                except OSError:
                    pass

                totalsize += fsize
                if os.path.isfile(f):
                    try:
                        cur.execute("INSERT INTO tree (type, size, name, parentid)"
                                    "VALUES('file', ?, ?, ?)", (fsize, fname, parent))
                    except sqlite3.ProgrammingError, e:
                        print("fsize: " + str(fsize))
                        print("fname: " + str(fname))
                        print("parent: " + str(parent))
                        raise

            # add total filesize to all parts of the path
            pathid = None

            for part in allparts:
                if not pathid:
                    cur.execute("SELECT id, size FROM tree WHERE name=? AND parentid IS NULL", (part,))
                else:
                    cur.execute("SELECT id, size FROM tree WHERE name=? AND parentid=?", (part, pathid))
                pathid, size = cur.fetchone()
                size += totalsize
                cur.execute("UPDATE tree SET size=? WHERE id=?", (size, pathid))

        with gzip.open('tree.sql.gz', 'w') as f:
            for line in con.iterdump():
                line = line.rstrip()
                if line != 'DELETE FROM "sqlite_sequence";':
                    if not line.startswith('INSERT INTO "sqlite_sequence" VALUES(\'tree\','):
                        try:
                            f.write('%s\n' % line)
                        except UnicodeEncodeError:
                            print("reg-line: " + line)
                            print("u-e-line: " + line.encode('unicode-escape'))
                            print
                            f.write('%s\n' % line.encode('unicode-escape'))

finally:
    temp.close()
