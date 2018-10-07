import json

from flask import Blueprint, flash, Markup, redirect, render_template, request,\
    session

from libs import admin_authentication
from libs.admin_authentication import authenticate_admin_login,\
    authenticate_admin_study_access, get_admins_allowed_studies, get_admins_allowed_studies_as_query_set,\
    admin_is_system_admin
from libs.security import check_password_requirements

from database.study_models import Study
from database.user_models import Researcher
from database.data_access_models import ChunkRegistry
from datetime import datetime
from collections import OrderedDict

import sys 
import pytz

admin_pages = Blueprint('admin_pages', __name__)

# TODO: Document.


@admin_pages.route('/choose_study', methods=['GET'])
@authenticate_admin_login
def choose_study():
    allowed_studies = get_admins_allowed_studies_as_query_set()

    # If the admin is authorized to view exactly 1 study, redirect to that study
    if allowed_studies.count() == 1:
        return redirect('/view_study/{:d}'.format(allowed_studies.values_list('pk', flat=True).get()))

    # Otherwise, show the "Choose Study" page
    allowed_studies_json = Study.query_set_as_native_json(allowed_studies)
    return render_template(
        'choose_study.html',
        studies=allowed_studies_json,
        allowed_studies=allowed_studies_json,
        system_admin=admin_is_system_admin()
    )


@admin_pages.route('/view_study/<string:study_id>', methods=['GET'])
@authenticate_admin_study_access
def view_study(study_id=None):

    settings_strings = { 'accelerometer': 'Accelerometer', 'bluetooth': 'Bluetooth', 'calls': 'Calls', 'gps': 'GPS', 
        'identifiers': 'Identifiers', 'app_log': 'Android Log', 'ios_log': 'IOS Log', 'power_state': 'Power State', 
        'survey_answers': 'Survey Answers', 'survey_timings': 'Survey Timings', 'texts': 'Texts', 
        'audio_recordings': 'Audio Recordings', 'image_survey': 'Image Survey', 'wifi': 'Wifi', 'proximity': 'Proximity', 
        'gyro': 'Gyro', 'magnetometer': 'Magnetometer', 'devicemotion': 'Device Motion', 'reachability': 'Reachability' }
    study = Study.objects.get(pk=study_id)
    settings = study.get_study_device_settings().as_native_python()
    data_types_dict = {}
    for setting_key, setting_label in settings_strings.items():
        if setting_key in settings and settings[setting_key] is True:
            data_types_dict[setting_key] = setting_label
    tracking_survey_ids = study.get_survey_ids_and_object_ids_for_study('tracking_survey')
    if len(tracking_survey_ids) > 0:
        data_types_dict['survey_answers'] = settings_strings['survey_answers']
        data_types_dict['survey_timings'] = settings_strings['survey_timings']
    audio_survey_ids = study.get_survey_ids_and_object_ids_for_study('audio_survey')
    if len(audio_survey_ids) > 0:
        data_types_dict['audio_recordings'] = settings_strings['audio_recordings']
    image_survey_ids = study.get_survey_ids_and_object_ids_for_study('image_survey')
    participants = study.participants.all()

    data_types_dict = OrderedDict(sorted(data_types_dict.items(), key=lambda t: t[0]))

    print >> sys.stderr, data_types_dict

    participant_ids = [participant.patient_id for participant in participants]

    chunk_fields = ["pk", "participant_id", "data_type", "chunk_path", "time_bin", "chunk_hash",
                    "participant__patient_id", "study_id", "survey_id", "survey__object_id"]
    chunks = ChunkRegistry.get_chunks_time_range(study_id = study_id, user_ids = participant_ids).values(*chunk_fields)
    #print >> sys.stderr, chunks
    data_received_dates = {}
    datetime_now = datetime.now()
    for chunk in chunks:
        pt = chunk['participant__patient_id']
        dt = chunk['data_type']
        time_bin = chunk['time_bin']

        if not pt in data_received_dates:
            data_received_dates[pt] = {}

        if not dt in data_received_dates[pt] or time_bin > data_received_dates[pt][dt]:
            data_received_dates[pt][dt] = time_bin

    fmt = "%Y-%m-%d %H:%M:%S"
    received_data = {}
    for participant in data_received_dates.keys():
        if not participant in received_data:
            received_data[participant] = {}
        for dt in data_received_dates[participant].keys():
            if not dt in received_data[participant]:
                received_data[participant][dt] = {}

            date_diff = (datetime_now - data_received_dates[participant][dt]).total_seconds() / 3600.0
            date_string = data_received_dates[participant][dt].replace(tzinfo=pytz.utc).astimezone(pytz.timezone('America/Chicago')).strftime(fmt)

            if date_diff < 6.0:
                 date_color = 'btn-success'
            if date_diff >= 6.0:
                 date_color = 'btn-warning'
            if date_diff >= 12.0:
                 date_color = 'btn-danger'
           
            received_data[participant][dt]['date_color'] = date_color
            received_data[participant][dt]['date_string'] = date_string
            #print >> sys.stderr, "%s %f %s"%(date_string, date_diff, date_color)

    return render_template(
        'view_study.html',
        study=study,
        patients=participants,
        received_data=received_data,
        data_types=data_types_dict,
        audio_survey_ids=audio_survey_ids,
        image_survey_ids=image_survey_ids,
        tracking_survey_ids=tracking_survey_ids,
        allowed_studies=get_admins_allowed_studies(),
        system_admin=admin_is_system_admin()
    )


@admin_pages.route('/data-pipeline/<string:study_id>', methods=['GET'])
@authenticate_admin_study_access
def view_study_data_pipeline(study_id=None):
    study = Study.objects.get(pk=study_id)

    return render_template(
        'data-pipeline.html',
        study=study,
        allowed_studies=get_admins_allowed_studies(),
    )


"""########################## Login/Logoff ##################################"""


@admin_pages.route('/')
@admin_pages.route('/admin')
def render_login_page():
    if admin_authentication.is_logged_in():
        return redirect("/choose_study")
    return render_template('admin_login.html')


@admin_pages.route("/logout")
def logout():
    admin_authentication.logout_loggedin_admin()
    return redirect("/")


@admin_pages.route("/validate_login", methods=["GET", "POST"])
def login():
    """ Authenticates administrator login, redirects to login page if authentication fails. """
    if request.method == 'POST':
        username = request.values["username"]
        password = request.values["password"]
        if Researcher.check_password(username, password):
            admin_authentication.log_in_admin(username)
            return redirect("/choose_study")
        else:
            flash("Incorrect username & password combination; try again.", 'danger')

    return redirect("/")


@admin_pages.route('/manage_credentials')
@authenticate_admin_login
def manage_credentials():
    return render_template('manage_credentials.html',
                           allowed_studies=get_admins_allowed_studies(),
                           system_admin=admin_is_system_admin())


@admin_pages.route('/reset_admin_password', methods=['POST'])
@authenticate_admin_login
def reset_admin_password():
    username = session['admin_username']
    current_password = request.values['current_password']
    new_password = request.values['new_password']
    confirm_new_password = request.values['confirm_new_password']
    if not Researcher.check_password(username, current_password):
        flash("The Current Password you have entered is invalid", 'danger')
        return redirect('/manage_credentials')
    if not check_password_requirements(new_password, flash_message=True):
        return redirect("/manage_credentials")
    if new_password != confirm_new_password:
        flash("New Password does not match Confirm New Password", 'danger')
        return redirect('/manage_credentials')
    Researcher.objects.get(username=username).set_password(new_password)
    flash("Your password has been reset!", 'success')
    return redirect('/manage_credentials')


@admin_pages.route('/reset_download_api_credentials', methods=['POST'])
@authenticate_admin_login
def reset_download_api_credentials():
    researcher = Researcher.objects.get(username=session['admin_username'])
    access_key, secret_key = researcher.reset_access_credentials()
    msg = """<h3>Your Data-Download API access credentials have been reset!</h3>
        <p>Your new <b>Access Key</b> is:
          <div class="container-fluid">
            <textarea rows="1" cols="85" readonly="readonly" onclick="this.focus();this.select()">%s</textarea></p>
          </div>
        <p>Your new <b>Secret Key</b> is:
          <div class="container-fluid">
            <textarea rows="1" cols="85" readonly="readonly" onclick="this.focus();this.select()">%s</textarea></p>
          </div>
        <p>Please record these somewhere; they will not be shown again!</p>""" \
        % (access_key, secret_key)
    flash(Markup(msg), 'warning')
    return redirect("/manage_credentials")
