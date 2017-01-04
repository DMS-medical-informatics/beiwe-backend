import secure_settings, constants
provided_settings = vars(secure_settings)
provided_settings.pop("__builtins__")

#check that all values provided actually contain something
for attr_name, attr_value in provided_settings.items():
    if not attr_value and attr_name[0] != '_':
        raise ImportError(attr_name + " was not provided with a value.")
    
MANDATORY_VARS = {'ASYMMETRIC_KEY_LENGTH',
                  'AWS_ACCESS_KEY_ID',
                  'AWS_SECRET_ACCESS_KEY',
                  'E500_EMAIL_ADDRESS',
                  'FLASK_SECRET_KEY',
                  'ITERATIONS',
                  'LOCAL_BACKUPS_DIRECTORY',
                  'MONGO_PASSWORD',
                  'MONGO_USERNAME',
                  'MONGO_PORT',
                  'OTHER_EMAIL_ADDRESS',
                  'S3_BACKUPS_AWS_KEY_ID',
                  'S3_BACKUPS_AWS_SECRET_ACCESS_KEY',
                  'S3_BACKUPS_BUCKET',
                  'S3_BUCKET',
                  'SYSADMIN_EMAILS' }

#Check that all the mandatory variables exist...
for mandatory_var in MANDATORY_VARS:
    if mandatory_var not in provided_settings:
        raise ImportError(mandatory_var + " was not provided in your settings.")

# Environment variables might be unpredictable, so we sanitize the numerical ones as ints.
secure_settings.MONGO_PORT = int(secure_settings.MONGO_PORT)
secure_settings.ASYMMETRIC_KEY_LENGTH = int(secure_settings.ASYMMETRIC_KEY_LENGTH)
secure_settings.ITERATIONS = int(secure_settings.ITERATIONS)

constants.DEFAULT_S3_RETRIES = int(constants.DEFAULT_S3_RETRIES)
constants.CONCURRENT_NETWORK_OPS = int(constants.CONCURRENT_NETWORK_OPS)
constants.FILE_PROCESS_PAGE_SIZE = int(constants.FILE_PROCESS_PAGE_SIZE)

# email addresses are parsed from a comma separated list
# whitespace before and after addresses are stripped
secure_settings.SYSADMIN_EMAILS = [_email_address.strip() for _email_address in secure_settings.SYSADMIN_EMAILS.split(",")]
