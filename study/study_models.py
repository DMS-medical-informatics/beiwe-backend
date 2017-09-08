# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import json

from django.db import models

from config.constants import IOS_API, ANDROID_API, NULL_OS, AUDIO_SURVEY, TRACKING_SURVEY
from config.study_constants import (
    ABOUT_PAGE_TEXT, CONSENT_FORM_TEXT, DEFAULT_CONSENT_SECTIONS_JSON,
    SURVEY_SUBMIT_SUCCESS_TOAST_TEXT, AUDIO_SURVEY_SETTINGS
)
from libs.security import (
    compare_password, device_hash, generate_easy_alphanumeric_string, generate_hash_and_salt,
    generate_random_string, generate_user_hash_and_salt
)
from study.validators import (
    id_validator, length_32_validator, standard_base_64_validator, url_safe_base_64_validator
)

from study.base_models import AbstractModel, JSONTextField


# AJK TODO create profiling models (see db/profiling.py)
# AJK TODO when all that is done, collapse migrations
# We're keeping Flask for the frontend stuff; Django is only for the database interactions (ORM).


# AJK TODO annotate, point out that a DeviceSettings is automatically created
class Study(AbstractModel):
    # AJK TODO make sure that the error generated by unique/max_length/validator is caught properly
    # in the view (cf. db.study_models.Study.create_default_study). This is a concern for all
    # models and fields that have restrictions on them.
    name = models.TextField(unique=True, help_text='Name of the study; can be of any length')
    encryption_key = models.CharField(max_length=32, validators=[length_32_validator],
                                      help_text='Key used for encrypting the study data')

    def add_researcher(self, researcher):
        # This takes either an actual Researcher object, or the primary key of such an object
        self.researchers.add(researcher)

    def remove_researcher(self, researcher):
        self.researchers.remove(researcher)

    def add_survey(self, survey):
        self.surveys.add(survey)

    def remove_survey(self, survey):
        # AJK TODO not sure if I want to raise this error
        if not self.surveys.filter(pk=survey.pk).exists():
            raise RuntimeError('Survey does not exist.')
        self.surveys.remove(survey)

    def get_surveys_for_study(self):
        return [json.loads(survey.as_native_json()) for survey in self.surveys.all()]

    def get_survey_ids_for_study(self, survey_type='tracking_survey'):
        return self.surveys.filter(survey_type=survey_type).values_list('id', flat=True)

    def get_study_device_settings(self):
        return self.device_settings


# AJK TODO idea: add SurveyArchive model that gets created on Survey.save() (or with a signal)
class Survey(AbstractModel):
    """
    Surveys contain all information the app needs to display the survey correctly to a participant,
    and when it should push the notifications to take the survey.

    Surveys must have a 'survey_type', which is a string declaring the type of survey it
    contains, which the app uses to display the correct interface.

    Surveys contain 'content', which is a JSON blob that is unpacked on the app and displayed
    to the participant in the form indicated by the survey_type.

    Timings schema: a survey must indicate the day of week and time of day on which to trigger;
    by default it contains no values. The timings schema mimics the Java.util.Calendar.DayOfWeek
    specification: it is zero-indexed with day 0 as Sunday. 'timings' is a list of 7 lists, each
    inner list containing any number of times of the day. Times of day are integer values
    indicating the number of seconds past midnight.
    """

    SURVEY_TYPE_CHOICES = (
        (AUDIO_SURVEY, AUDIO_SURVEY),
        (TRACKING_SURVEY, TRACKING_SURVEY),
    )

    content = JSONTextField(default='[]', help_text='JSON blob containing information about the survey questions.')
    survey_type = models.CharField(max_length=16, choices=SURVEY_TYPE_CHOICES,
                                   help_text='What type of survey this is.')
    settings = JSONTextField(default='{}', help_text='JSON blob containing settings for the survey.')
    timings = JSONTextField(default=json.dumps([[], [], [], [], [], [], []]),
                            help_text='JSON blob containing the times at which the survey is sent.')

    study = models.ForeignKey('Study', on_delete=models.PROTECT, related_name='surveys')

    @classmethod
    # AJK TODO this needs some testing
    def create_with_settings(cls, survey_type, study, **kwargs):
        """
        Create a new Survey with the provided survey type and attached to the given Study,
        as well as any other given keyword arguments. If the Survey is audio and no other
        settings are given, give it the default audio survey settings.
        """

        survey = cls(survey_type=survey_type, study=study, **kwargs)
        if survey_type == AUDIO_SURVEY and 'settings' not in kwargs:
            survey.settings = json.dumps(AUDIO_SURVEY_SETTINGS)

        survey.save()
        return survey


class AbstractPasswordUser(AbstractModel):
    """
    The AbstractPasswordUser (APU) model is used to enable basic password functionality for human
    users of the database, whatever variety of user they may be.

    APU descendants have passwords hashed once with sha256 and many times (as defined in
    secure_settings.py) with PBKDF2, and salted using a cryptographically secure random number
    generator. The sha256 check duplicates the storage of the password on the mobile device, so
    that the APU's password is never stored in a reversible manner.
    """

    # AJK TODO look into doing password stuff automatically through Django:
    # https://docs.djangoproject.com/en/1.11/topics/auth/passwords/
    password = models.CharField(max_length=44, validators=[url_safe_base_64_validator],
                                help_text='A hash of the user\'s password')
    salt = models.CharField(max_length=24, validators=[url_safe_base_64_validator])

    def generate_hash_and_salt(self, password):
        """
        Generate a password hash and random salt from a given password. This is different
        for different types of APUs, depending on whether they use mobile or web.
        """
        raise NotImplementedError

    def set_password(self, password):
        """
        Sets the instance's password hash to match the hash of the provided string.
        """
        password_hash, salt = self.generate_hash_and_salt(password)
        self.password = password_hash
        self.salt = salt
        self.save()

    def reset_password(self):
        """
        Resets the patient's password to match an sha256 hash of a randomly generated string.
        """
        password = generate_easy_alphanumeric_string()
        self.set_password(password)
        return password

    def validate_password(self, compare_me):
        """
        Checks if the input matches the instance's password hash.
        """
        return compare_password(compare_me, self.salt, self.password)

    class Meta:
        abstract = True


class Participant(AbstractPasswordUser):
    """
    The Participant database object contains the password hashes and unique usernames of any
    participants in the study, as well as information about the device the participant is using.
    A Participant uses mobile, so their passwords are hashed accordingly.
    """

    # AJK TODO possibly move their definitions *back* from constants.py to here
    # Same for survey types
    OS_TYPE_CHOICES = (
        (IOS_API, IOS_API),
        (ANDROID_API, ANDROID_API),
        (NULL_OS, NULL_OS),
    )

    patient_id = models.CharField(max_length=8, unique=True, validators=[id_validator],
                                  help_text='Eight-character unique ID with characters chosen from 1-9 and a-z')

    device_id = models.CharField(max_length=256, blank=True,
                                 help_text='The ID of the device that the participant is using for the study, if any.')
    os_type = models.CharField(max_length=16, choices=OS_TYPE_CHOICES, blank=True,
                               help_text='The type of device the participant is using, if any.')

    study = models.ForeignKey('Study', on_delete=models.PROTECT, related_name='participants', null=False)

    @classmethod
    def create_with_password(cls, study):
        """
        Creates a new patient with randomly generated patient_id and password.
        """

        # Ensure that a unique patient_id is generated. If it is not after
        # twenty tries, raise an error.
        patient_id = generate_easy_alphanumeric_string()
        for _ in xrange(20):
            if not cls.objects.filter(patient_id=patient_id).exists():
                # If patient_id does not exist in the database already
                break
            patient_id = generate_easy_alphanumeric_string()
        else:
            raise RuntimeError('Could not generate unique Patient ID for new Participant.')

        # Create a Participant, and generate for them a password
        participant = cls(patient_id=patient_id, study=study)
        password = participant.reset_password()

        return patient_id, password

    def generate_hash_and_salt(self, password):
        return generate_user_hash_and_salt(password)

    def debug_validate_password(self, compare_me):
        """
        Checks if the input matches the instance's password hash, but does
        the hashing for you for use on the command line. This is necessary
        for manually checking that setting and validating passwords work.
        """
        compare_me = device_hash(compare_me)
        return compare_password(compare_me, self.salt, self.password)

    def set_device(self, device_id):
        # AJK TODO once this works, get rid of it (and brethren)
        self.device_id = device_id
        self.save()

    def set_os_type(self, os_type):
        self.os_type = os_type
        self.save()

    def clear_device(self):
        self.device_id = None
        self.save()


class Researcher(AbstractPasswordUser):
    """
    The Researcher database object contains the password hashes and unique usernames of any
    researchers, as well as their data access credentials. A Researcher can be attached to
    multiple Studies, and a Researcher may also be an admin who has extra permissions.
    A Researcher uses web, so their passwords are hashed accordingly.
    """

    username = models.CharField(max_length=32, unique=True, help_text='User-chosen username, stored in plain text')
    admin = models.BooleanField(default=False, help_text='Whether the researcher is also an admin')

    access_key_id = models.CharField(max_length=64, validators=[standard_base_64_validator], blank=True)
    access_key_secret = models.CharField(max_length=44, validators=[url_safe_base_64_validator], blank=True)
    access_key_secret_salt = models.CharField(max_length=24, validators=[url_safe_base_64_validator], blank=True)

    studies = models.ManyToManyField('Study', related_name='researchers')

    @classmethod
    def create_with_password(cls, username, password):
        """
        Creates a new Researcher with provided username and password. They will initially
        not be associated with any Study.
        """

        researcher = cls(username=username)
        researcher.set_password(password)
        return researcher

    @classmethod
    def check_password(cls, username, compare_me):
        """
        Checks if the provided password matches the hash of the provided Researcher's password.
        """
        if not Researcher.objects.filter(username=username).exists():
            return False
        researcher = Researcher.objects.get(username=username)
        return researcher.validate_password(compare_me)

    def generate_hash_and_salt(self, password):
        return generate_hash_and_salt(password)

    def elevate_to_admin(self):
        self.admin = True
        self.save()

    def validate_access_credentials(self, proposed_secret_key):
        """ Returns True/False if the provided secret key is correct for this user."""
        return compare_password(
            proposed_secret_key,
            self.access_key_secret_salt,
            self.access_key_secret
        )

    def reset_access_credentials(self):
        access_key = generate_random_string()[:64]
        secret_key = generate_random_string()[:64]
        secret_hash, secret_salt = generate_hash_and_salt(secret_key)
        self.access_key_id = access_key
        self.access_key_secret = secret_hash
        self.access_key_secret_salt = secret_salt
        self.save()
        return access_key, secret_key


class DeviceSettings(AbstractModel):
    """
    The DeviceSettings database contains the structure that defines
    settings pushed to devices of users in of a study.
    """

    # Whether various device options are turned on
    accelerometer = models.BooleanField(default=True)
    gps = models.BooleanField(default=True)
    calls = models.BooleanField(default=True)
    texts = models.BooleanField(default=True)
    wifi = models.BooleanField(default=True)
    bluetooth = models.BooleanField(default=False)
    power_state = models.BooleanField(default=True)

    # Whether iOS-specific data streams are turned on
    proximity = models.BooleanField(default=False)
    gyro = models.BooleanField(default=False)
    magnetometer = models.BooleanField(default=False)
    devicemotion = models.BooleanField(default=False)
    reachability = models.BooleanField(default=True)

    # Upload over cellular data or only over WiFi (WiFi-only is default)
    allow_upload_over_cellular_data = models.BooleanField(default=False)

    # Timer variables
    accelerometer_off_duration_seconds = models.PositiveIntegerField(default=10)
    accelerometer_on_duration_seconds = models.PositiveIntegerField(default=10)
    bluetooth_on_duration_seconds = models.PositiveIntegerField(default=60)
    bluetooth_total_duration_seconds = models.PositiveIntegerField(default=300)
    bluetooth_global_offset_seconds = models.PositiveIntegerField(default=0)
    check_for_new_surveys_frequency_seconds = models.PositiveIntegerField(default=3600 * 6)
    create_new_data_files_frequency_seconds = models.PositiveIntegerField(default=15 * 60)
    gps_off_duration_seconds = models.PositiveIntegerField(default=600)
    gps_on_duration_seconds = models.PositiveIntegerField(default=60)
    seconds_before_auto_logout = models.PositiveIntegerField(default=600)
    upload_data_files_frequency_seconds = models.PositiveIntegerField(default=3600)
    voice_recording_max_time_length_seconds = models.PositiveIntegerField(default=240)
    wifi_log_frequency_seconds = models.PositiveIntegerField(default=300)

    # iOS-specific timer variables
    gyro_off_duration_seconds = models.PositiveIntegerField(default=600)
    gyro_on_duration_seconds = models.PositiveIntegerField(default=60)
    magnetometer_off_duration_seconds = models.PositiveIntegerField(default=600)
    magnetometer_on_duration_seconds = models.PositiveIntegerField(default=60)
    devicemotion_off_duration_seconds = models.PositiveIntegerField(default=600)
    devicemotion_on_duration_seconds = models.PositiveIntegerField(default=60)

    # Text strings
    about_page_text = models.TextField(default=ABOUT_PAGE_TEXT)
    call_clinician_button_text = models.TextField(default='Call My Clinician')
    consent_form_text = models.TextField(default=CONSENT_FORM_TEXT)
    survey_submit_success_toast_text = models.TextField(default=SURVEY_SUBMIT_SUCCESS_TOAST_TEXT)

    # Consent sections
    consent_sections = JSONTextField(default=DEFAULT_CONSENT_SECTIONS_JSON)

    study = models.OneToOneField('Study', on_delete=models.PROTECT, related_name='device_settings')
