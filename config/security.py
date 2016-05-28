import os

# In order to run the server or download daat  you must change the various
# passwords and credentials below, and then rename/copy this file to 
# a new file named global_passwords.py (keep it in the config folder)

# Store your passwords.  Do so somewhere that is secure, and in a way that will
# be accessible to you in the future.

# THESE ARE NOT THE DATA ENCRYPTION KEYS, THOSE ARE NOT STORED HERE.

# Do not use the example keys provided on any production environment.

# We STRONGLY recommend using a cryptographically secure random number generator
# to generate your passwords; your passwords should not be easy to remember.

# These are the credentials used to access the MongoDB that contains website
# usernames and passwords.  If you are configuring your server see the comment
# at the end of this document.
MONGO_USERNAME = "default"
MONGO_PASSWORD = "default"

# This is the secret key for the website, it is used in securing the website
# and config stored for each user.
# Do not use the example provided in this document
FLASK_SECRET_KEY = "abcdefghijklmnopqrstuvwxyz012345"

# These are your AWS (Amazon Web Services) access credentials.
# (Amazon provides you with these credentials, you do not generate them.)
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

S3_BACKUPS_AWS_KEY_ID = "aws_creds_for_backups"
S3_BACKUPS_AWS_SECRET_ACCESS_KEY = "aws_creds_for_backups"
LOCAL_BACKUPS_DIRECTORY = "edit me"

# the name of the s3 bucket that will be used to store user generated data, and
# backups of local database information.
S3_BUCKET = os.getenv("S3_BUCKET", "com.unwiredappeal.beiwe.2")
S3_BACKUPS_BUCKET = "edit_me"

# The length of the public/private keys used in encrypting user config on their device
ASYMMETRIC_KEY_LENGTH = 2048

# The number of iterations used in password hashing. You CANNOT change this
# value once people have created passwords, because then the hashes won't match!
ITERATIONS = 1000

# Email addresses used on the server.
E500_EMAIL_ADDRESS = "noreply@unwiredappeal.net" #500 error email source
OTHER_EMAIL_ADDRESS = "noreply@unwiredappeal.net" #500 error email source
SYSADMIN_EMAILS = ["keary@mindless.com", "eli@zagaran.com" ]


"""            Setting up MongoDB and mongolia

If you have set up a different default location for the conf, go edit that file,
otherwise cd to /etc, edit mongodb.conf using superuser privilages.
find the line #auth=true and remove the comment (the #)
run: sudo service mongod restart

in a python terminal, enter:
import mongolia
mongolia.add_user( "username_in_quotes", "password_in_quotes" )
mongolia.authenticate_connection( "username_in_quotes", "password_in_quotes" )
exit()
"""
