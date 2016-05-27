import os
import traceback, smtplib
from datetime import datetime
from config.security import E500_EMAIL_ADDRESS, SYSADMIN_EMAILS, OTHER_EMAIL_ADDRESS

def open_email_server():
        server = smtplib.SMTP(os.getenv("SPARKPOST_SMTP_HOST"), os.getenv("SPARKPOST_SMTP_PORT"))
        server.starttls()
        server.login(os.getenv("SPARKPOST_SMTP_USERNAME"), os.getenv("SPARKPOST_SMTP_PASSWORD"))
        return server

def log_and_email_error(e, log_message=None, emails=SYSADMIN_EMAILS ):
    """ Prints in the server logs (defaults to Apache if not specified),
        does NOT stop execution.
        Note the error.message value is actually the subject line of the email,
        the "log_message" variable is a passed in as the "message" variable
        into the log_error function and appears as part of the email and log statement. """
    try:
        subject = "Beiwe Error: %s" % e.message
        content = log_error(e, log_message, reraise=True)
        error_email = 'From: %s\nSubject: STAGE-%s\n\n%s' % (E500_EMAIL_ADDRESS, subject, content)
        email_server = open_email_server() 
        email_server.sendmail( E500_EMAIL_ADDRESS, emails, error_email )
        email_server.quit()
    except Exception:
        print("\n!!!! ERROR IN log_and_email_error !!!!")


def log_error(e, message=None, reraise=False):
    """ Prints an error to the apache log.
        "message" is a customizable that will be printed in the log.
        Reraise is dangerous, only set to true if you understand why it is."""
    try:
        error_message = "===================\n"
        error_message += datetime.utcnow().isoformat() + "\n"
        if message is not None: error_message += message + "\n"
        error_message += "ERROR:" + str(e.__repr__()) + "\n"
        error_message += traceback.format_exc() + "\n"
        error_message += "===================\n"
        print(error_message)
        return error_message
    except Exception:
        print("\n!!!! ERROR IN log_error !!!!")
        if reraise:
            raise


def email_system_administrators(message, subject, source_email=OTHER_EMAIL_ADDRESS):
    """ Sends an email to the system administrators. """
    error_email = 'From: %s\nSubject: STAGE-%s\n\n%s' % (source_email, subject, message)
    try:
        email_server = open_email_server() 
        email_server.sendmail( source_email, SYSADMIN_EMAILS, error_email )
        email_server.quit()
    except Exception as e:
        # todo: this reraise parameter may be incorrect.
        log_error(e, message="sysadmin email failed", reraise=False)
