#Twisted Test

##To run the test task:

1) Set proper user/pass for MySQL -> test.py, mysql_pool definition

   also, these steps are assumed:

   create database twisted_test;

   grant all on twisted_test.* to 'user'@'localhost';

2) Run redis-server

3) Run python2 test.py

4) Go to localhost:8880/test, press "Send JSON"

5) Examine ./twisted_test.log