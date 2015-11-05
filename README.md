# web-du
##online disk utilization tool

###This will scan a filesystem and store the size and type of each file / dir in a sqlite db to be used in a web frontend.

There are 3 parts to this tool. The remote, the server and the frontend.

The remote runs on the machine you want see the disk utilization. It is currently a python script, but hopefully soon I will add something that doesn't require python.

The server is an http server that serves up json data about the filesystem that was run on the 'remote' machine. This is currently written in node.js but I might add a wsgi version also.

The frontend is just a small example of using the json data from the server to traverse the filesystem scanned on the remote machine.
