import os
import psycopg2
import pandas as pd

from dotenv import load_dotenv
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from pymongo import MongoClient
from pymongo.errors import OperationFailure
from sqlalchemy import create_engine

# Load environment variables from the .env file (if present)
load_dotenv()

pg_database = os.getenv("pg_database")
pg_user = os.getenv("pg_user")
pg_password =  os.getenv("pg_password")

db_name = os.getenv("db_name")
db_user =  os.getenv("db_user")
db_password = os.getenv("db_password")
db_ip = os.getenv("psql_ip")

schema_file_path = os.getenv("schema_file_path")


print('Creating new database :--> ',db_name)

con = psycopg2.connect(dbname=pg_database,
      user=pg_user, host=db_ip,
      password=pg_password)

con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

cur = con.cursor()

# Use the psycopg2.sql module instead of string concatenation 
# in order to avoid sql injection attacks.

#create a new user with password
query = sql.SQL("CREATE USER {} WITH PASSWORD {}").format(
        sql.Identifier(db_user),  # Safe username insertion
        sql.Placeholder()         # Placeholder for the password
    )
    
# Execute the query with the actual password as a parameter
try:
    cur.execute(query, [db_password])
except Exception as e:
    print(e)


# drop existing database
cur.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(
        sql.Identifier(db_name))
    )

# create new database
cur.execute(sql.SQL("CREATE DATABASE {}").format(
        sql.Identifier(db_name))
    )

cur.execute(sql.SQL("ALTER DATABASE {} OWNER TO {}").format(
        sql.Identifier(db_name),      # Safe database name insertion
        sql.Identifier(db_user)       # Safe new owner insertion
    ))

#grant database privileges
cur.execute(sql.SQL("GRANT ALL PRIVILEGES ON DATABASE {0} TO {1}").format(
        sql.Identifier(db_name), sql.Identifier(db_user))
    )


print(f"Successfully created database {db_name}")

# New connection for new user and database
newdbcon = psycopg2.connect(dbname=db_name,
      user=db_user, host=db_ip,
      password=db_password)

newdbcon.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

newdbcur = newdbcon.cursor()

engine = create_engine(
    f'postgresql+psycopg2://{db_user}:{db_password}@{db_ip}/{db_name}'
)

newdbcur.execute(
    f"""CREATE TABLE IF NOT EXISTS 
            usertype (
                id SERIAL           NOT NULL PRIMARY KEY, 
                "userType"          TEXT NOT NULL,
                "createdAt"         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, 
                "updatedAt"         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
    """
)

result = pd.read_sql("select * from usertype", engine)
if result.empty:
    df = pd.read_csv(
        f"""{schema_file_path}/usertype.csv"""
    )
    df.to_sql("usertype", engine, if_exists="append", index=False)

newdbcur.execute(
    f"""CREATE TABLE IF NOT EXISTS
            users 
            ( 
                id SERIAL           NOT NULL PRIMARY KEY, 
                "firstName"         TEXT NOT NULL, 
                "lastName"          TEXT NOT NULL, 
                password            TEXT NOT NULL, 
                "phoneNumber"       CHARACTER VARYING(15) NOT NULL, 
                email               TEXT NOT NULL, 
                permissions         TEXT NOT NULL, 
                address             TEXT, 
                gender              TEXT, 
                "employeeId"        CHARACTER VARYING(255) DEFAULT '0', 
                "isVerified"        BOOLEAN DEFAULT false, 
                "usertypeId"        INTEGER NOT NULL, 
                "isDeleted"         BOOLEAN DEFAULT false,
                "createdAt"         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, 
                "updatedAt"         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, 
                CONSTRAINT users_fk1 FOREIGN KEY ("usertypeId") REFERENCES "usertype" ("id"), 
                UNIQUE (email),
                UNIQUE ("phoneNumber")
            );
    """
)

query = f"""INSERT INTO users (id,"firstName","lastName","password","phoneNumber", "email", "permissions", "usertypeId") values (1,'Tproject','Superadmin','$2b$10$cGa5yOKs7v1.qJdYwP.fJudFuZIIT.ctDC66MtwbzTqTvcXRyis5O','8547077529','tprojectsuperadmin@tproject.com', 'superadmin', 1 )"""
newdbcur.execute(query)

newdbcur.execute(
    f"""CREATE TABLE IF NOT EXISTS 
            country (
                id SERIAL           NOT NULL PRIMARY KEY, 
                "name"          TEXT NOT NULL,
                "createdAt"         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, 
                "updatedAt"         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (name)
            );
    """
)

query = f"""INSERT INTO country (id,"name") values (1,'INDIA')"""
newdbcur.execute(query)

newdbcur.execute(
    f"""CREATE TABLE IF NOT EXISTS 
            profiles (
                id SERIAL            NOT NULL PRIMARY KEY, 
                "userId"             INTEGER NOT NULL,
                "dob"                DATE,
                "profileImage"       CHARACTER VARYING(1024),
                "gender"             CHARACTER VARYING(255),
                "countryId"          INTEGER NOT NULL,
                "createdAt"          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP, 
                "updatedAt"          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT profiles_fk1 FOREIGN KEY ("userId") REFERENCES "users" ("id"),
                CONSTRAINT profiles_fk2 FOREIGN KEY ("countryId") REFERENCES "country" ("id")
            );
    """
)

# create mongodb database and user
CONNECTION_STRING = "mongodb://localhost:27017"
 
# Create a connection using MongoClient.
client = MongoClient(CONNECTION_STRING)
 
mongodb = client.admin

monogo_db_user = os.getenv("monogo_db_user")
monogo_db_name = os.getenv("monogo_db_name")
monogo_db_password = os.getenv("monogo_db_password")
roles = [
    {"role": "readWrite", "db": monogo_db_name},
    { "role": "read", "db": monogo_db_name}
]

try:
# Create the user with the specified credentials and roles
    mongodb.command("createUser", monogo_db_user, pwd=monogo_db_password, roles=roles)
    print(f"User {monogo_db_user} created successfully.")
except OperationFailure as e:
    print(f"Error creating user: {e}")

try:
    db = client[monogo_db_name]
    collection = db["tproject_collection"]
    collection.insert_one({"name": "tproject", "remarks": 'Successfully created'})
except OperationFailure as e:
    print("Error",e)

  
