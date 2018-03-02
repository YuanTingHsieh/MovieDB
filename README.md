## MovieDB
It is a final project for CS564 at UW-Madison
It provides functionalities of load/add data, browsing data and searching data
The data type includes actors/directors/movies.

## Setting up and running the server
   0- After signing up to GCP, go to your GCP console and from there to Compute Engine view.

   1- Create a new VM (e.g. Ubuntu 17.04)

   2- Add a filter to open a port for Flask

     2.1. Go to VPC network > Firewall rules

     2.2. Create a new rule for all targets: source filters = 0.0.0.0/0, allow all protocols

     2.3. Add this filter as a network tag to your VM

  3- SSH to the instance using the SSH button from your VM overview

  4- In your VM, install **Anaconda** as follows:
     4.1. Run: `wget https://repo.continuum.io/archive/Anaconda2-5.0.0-Linux-x86_64.sh`
     4.2. Then Run: `bash Anaconda2-5.0.0-Linux-x86_64.sh`
  5- Create a sample Flask application:
     5.1. Create a directory templates: `mkdir templates`
     5.2. Now follow the directions in [here](https://www.tutorialspoint.com/flask/flask_sqlite.htm) paying attention to the following notes:
       5.2.1. Remember to put all the html files in the templates folder
       5.2.2. Put the following text in the home.html file (you may use an editor such as vim or emacs to create and edit files in the command line):
```html
<!doctype html>
<html>
  <body>
    <p><a href="/enternew">Add</a></p>
    <p><a href="list">List</a></p>
  </body>
</html>
```
       5.2.3. Save the web app python script in a file named flasksqliteapp.py (you may use vim or emacs to create and edit files).

  6- Run a Flask instance on the VM by running the following command:
       `FLASK_APP=flasksqliteapp.py flask run --host=0.0.0.0`
  7- Now you can access your sample web app by pointing to your VM IP using port 5000. For example if your VM is assigned IP X.Y.Z.T, then your app is being served on http://X.Y.Z.T:5000/. You can find the IP assigned to your VM from the VM information overview.

