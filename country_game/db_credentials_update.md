# Database Credentials Update

## Changes Made

1. Updated database credentials in `db_setup.py`:
   - Changed user from 'root' to 'spade605'
   - Changed password from 'password' to 'Beholder30'
   - Changed host from 'localhost' to 'spade605.mysql.pythonanywhere-services.com'
   - Added port 3306

2. Fixed database name in `app.py`:
   - Changed database name from '$county_game_server' to 'county_game_server' (removed the $ symbol)

3. Created a test script `test_db_connection.py` to verify the database connection and create the database and tables.

## Testing Results

The connection test failed when run locally with the error:
```
Error: 2003 (HY000): Can't connect to MySQL server on 'spade605.mysql.pythonanywhere-services.com:3306' (10060)
```

This is expected behavior because, as noted in the comments in `db_setup.py`, PythonAnywhere databases are only accessible from within the PythonAnywhere environment. The credentials are correctly updated, but the connection can only be tested when the code is deployed to PythonAnywhere.

## Next Steps

1. Deploy the updated code to PythonAnywhere.
2. Run the `db_setup.py` script on PythonAnywhere to create the database and tables.
3. Verify that the application can connect to the database and function correctly.